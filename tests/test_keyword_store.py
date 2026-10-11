# 关键词规则表：空库建表、写入读回、内存快照、重启回读。

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = str(ROOT.parent)
# 测试从仓库根的上一级导入包名 astrbot_plugin_keyword_reply
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

from astrbot_plugin_keyword_reply.data.group_name_store import GroupNameStore
from astrbot_plugin_keyword_reply.data.keyword_store import KeywordStore
from astrbot_plugin_keyword_reply.data.setting_store import SettingStore


class KeywordStoreTest(unittest.IsolatedAsyncioTestCase):
    # 关键词规则表的建表、读写和快照行为

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "keyword_reply.db"
        self.store = KeywordStore(self.db_path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _table_names(self) -> list[str]:
        """库里已有的普通表名，按名字排，方便对照集合。"""
        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
        finally:
            conn.close()
        return [str(row[0]) for row in rows]

    def _primary_key(self, table: str) -> list[str]:
        """表的主键列，按主键位次排回真实顺序。"""
        info = self._table_info(table)
        keyed = [(row[5], row[1]) for row in info if row[5]]
        return [name for _, name in sorted(keyed)]

    def _column_defs(self, table: str) -> list[tuple]:
        """列名、声明类型、是否 NOT NULL 三件套，逐列按定义顺序。"""
        return [
            (str(row[1]), str(row[2]), int(row[3])) for row in self._table_info(table)
        ]

    def _table_info(self, table: str) -> list[tuple]:
        """PRAGMA table_info：cid、列名、类型、notnull、默认值、主键位次。"""
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute(f"PRAGMA table_info({table})").fetchall()
        finally:
            conn.close()

    def test_empty_db_creates_three_tables(self) -> None:
        # 三个 store 各建自己的表，本插件一个库里应有三张表
        GroupNameStore(self.db_path)
        SettingStore(self.db_path)

        self.assertEqual(
            self._table_names(), ["group_name", "keyword_reply", "plugin_setting"]
        )
        # 主键必须和原库一致，否则迁移搬过来的行会撞成同一行
        self.assertEqual(self._primary_key("keyword_reply"), ["group_id", "keyword"])
        self.assertEqual(self._primary_key("group_name"), ["group_id"])
        self.assertEqual(self._primary_key("plugin_setting"), ["key"])

        self.assertEqual(
            self._column_defs("keyword_reply"),
            [("group_id", "TEXT", 1), ("keyword", "TEXT", 1), ("reply", "TEXT", 1)],
        )
        self.assertEqual(
            self._column_defs("group_name"),
            [("group_id", "TEXT", 1), ("group_name", "TEXT", 1)],
        )
        # plugin_setting 的 key 是非 INTEGER 主键，SQLite 不把 NOT NULL 记在列上
        self.assertEqual(
            self._column_defs("plugin_setting"),
            [("key", "TEXT", 0), ("value", "TEXT", 1)],
        )

    def test_empty_snapshot_has_no_rule(self) -> None:
        # 空库不应该凭空匹配出回复
        self.assertEqual(self.store.find_reply("1", "群规"), "")
        self.assertIsNone(self.store.rule_of("1", "群规"))
        self.assertEqual(self.store.list_rules("1"), [])

    async def test_upsert_then_find_reply(self) -> None:
        await self.store.upsert("1", "群规", "看置顶")
        # 命中要求整条消息完全相等，多一个字就不回
        self.assertEqual(self.store.find_reply("1", "群规"), "看置顶")
        self.assertEqual(self.store.find_reply("1", "看看群规"), "")
        # 同一个关键词在别的群是另一条规则，不能互相串
        self.assertEqual(self.store.find_reply("2", "群规"), "")
        rule = self.store.rule_of("1", "群规")
        self.assertEqual((rule.group_id, rule.keyword, rule.reply), ("1", "群规", "看置顶"))

    async def test_upsert_overwrites_same_keyword(self) -> None:
        await self.store.upsert("1", "群规", "旧回复")
        await self.store.upsert("1", "群规", "新回复")
        self.assertEqual(self.store.find_reply("1", "群规"), "新回复")
        self.assertEqual(len(self.store.list_rules("1")), 1)

    async def test_snapshot_updates_in_same_instance(self) -> None:
        # 写完立刻重建快照，同一个实例下一条消息就能命中新内容
        await self.store.upsert("1", "甲", "回甲")
        self.assertEqual(self.store.find_reply("1", "甲"), "回甲")
        await self.store.upsert_many("1", [("乙", "回乙"), ("丙", "回丙")])
        self.assertEqual(self.store.find_reply("1", "乙"), "回乙")
        self.assertEqual(self.store.find_reply("1", "丙"), "回丙")
        # 删掉后快照里也不该再有这条，否则热路径会回一条已经删掉的规则
        self.assertTrue(await self.store.delete("1", "甲"))
        self.assertEqual(self.store.find_reply("1", "甲"), "")

    async def test_upsert_many_empty_items_keeps_snapshot(self) -> None:
        await self.store.upsert("1", "甲", "回甲")
        # 空列表不写库也不重建快照，原有规则必须还在
        await self.store.upsert_many("1", [])
        self.assertEqual(self.store.find_reply("1", "甲"), "回甲")

    async def test_delete_missing_returns_false(self) -> None:
        # 本来就没有这条，返回 False，管理员路径靠它区分「删成功」和「没这条」
        self.assertFalse(await self.store.delete("1", "不存在"))

    async def test_list_page_filters_and_paginates(self) -> None:
        await self.store.upsert_many("1", [("甲", "回甲"), ("乙", "回乙")])
        await self.store.upsert("2", "丙", "回丙")
        # 填了群号只看这一群
        page, total = self.store.list_page("1", 0, 10)
        self.assertEqual(total, 2)
        self.assertEqual([rule.keyword for rule in page], ["乙", "甲"])
        # 空群号看全部，按 (群号, 关键词) 排
        page, total = self.store.list_page("", 0, 2)
        self.assertEqual(total, 3)
        self.assertEqual(
            [(rule.group_id, rule.keyword) for rule in page], [("1", "乙"), ("1", "甲")]
        )
        # 每页条数非法时不切片，只报总数
        self.assertEqual(self.store.list_page("", 0, 0), ([], 3))

    async def test_reopen_reads_committed_rules(self) -> None:
        await self.store.upsert("1", "群规", "看置顶")
        # 新建实例相当于插件重启，必须从库里读回同一条规则
        reopened = KeywordStore(self.db_path)
        self.assertEqual(reopened.find_reply("1", "群规"), "看置顶")
        self.assertEqual(len(reopened.list_rules("1")), 1)
