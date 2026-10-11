# 配置表：恰好 1 个键、空表导入、重启回读，以及配置与群名的原子保存。

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
from astrbot_plugin_keyword_reply.data.setting_store import SettingStore
from astrbot_plugin_keyword_reply.entity.constants import CFG_KEYWORD_GROUPS
from astrbot_plugin_keyword_reply.entity.group_name import GroupName


class SettingStoreTest(unittest.IsolatedAsyncioTestCase):
    # 配置键的读写与一次性事务保存

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "keyword_reply.db"
        self.store = SettingStore(self.db_path)
        # 保存接口会在同一个事务里写群名表，这里按真实接线先建好它
        self.group_names = GroupNameStore(self.db_path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_empty_table_reads_empty_list(self) -> None:
        # 空表按名单类型给空列表，页面显示空名单
        self.assertEqual(self.store.load_dict(), {CFG_KEYWORD_GROUPS: []})
        self.assertEqual(self.store.count(), 0)

    def test_import_if_empty_then_reopen(self) -> None:
        self.store.import_if_empty({CFG_KEYWORD_GROUPS: ["1", "2"]})
        self.assertEqual(self.store.load_dict(), {CFG_KEYWORD_GROUPS: ["1", "2"]})
        # 新建实例相当于插件重启，必须读回同一份名单
        reopened = SettingStore(self.db_path)
        self.assertEqual(reopened.load_dict(), {CFG_KEYWORD_GROUPS: ["1", "2"]})

    def test_import_does_not_overwrite_existing(self) -> None:
        self.store.import_if_empty({CFG_KEYWORD_GROUPS: ["1"]})
        # 表里已有配置，schema 不再参与，Pages 改过的值不能被冲掉
        self.store.import_if_empty({CFG_KEYWORD_GROUPS: ["9"]})
        self.assertEqual(self.store.load_dict(), {CFG_KEYWORD_GROUPS: ["1"]})

    async def test_set_value_writes_single_key(self) -> None:
        await self.store.set_value(CFG_KEYWORD_GROUPS, ["3"])
        self.assertEqual(self.store.load_dict(), {CFG_KEYWORD_GROUPS: ["3"]})
        # 只管理本插件的 1 个键，表里不该多出别的行
        self.assertEqual(self.store.count(), 1)

    async def test_save_writes_config_and_names(self) -> None:
        snapshot = await self.store.save_with_group_names(
            {CFG_KEYWORD_GROUPS: ["1", "2"]},
            [GroupName("1", "甲"), GroupName("2", "乙")],
        )
        # 返回的就是已提交的配置快照，形状与 load_dict 一致
        self.assertEqual(snapshot, {CFG_KEYWORD_GROUPS: ["1", "2"]})
        self.assertEqual(self.store.load_dict(), snapshot)
        self.assertEqual(self.group_names.as_map(), {"1": "甲", "2": "乙"})

    async def test_save_keeps_names_outside_this_request(self) -> None:
        await self.group_names.upsert("9", "老群")
        await self.store.save_with_group_names(
            {CFG_KEYWORD_GROUPS: ["1"]}, [GroupName("1", "甲")]
        )
        # 本次没出现的旧群名是历史数据，不能被删
        self.assertEqual(self.group_names.get_name("9"), "老群")

    async def test_save_skips_empty_id_and_empty_name(self) -> None:
        await self.store.save_with_group_names(
            {CFG_KEYWORD_GROUPS: ["1", "2"]},
            [GroupName("", "无群号"), GroupName("1", ""), GroupName("2", "乙")],
        )
        # 空群号没有主键可用、空群名是没拉到，两者都不该落库
        self.assertEqual(self.group_names.get_name("1"), "")
        self.assertEqual(self.group_names.get_name("2"), "乙")
        self.assertEqual(self.group_names.as_map(), {"2": "乙"})

    async def test_save_empty_name_does_not_overwrite_existing(self) -> None:
        await self.group_names.upsert("1", "旧名")
        await self.store.save_with_group_names(
            {CFG_KEYWORD_GROUPS: ["1"]}, [GroupName("1", "")]
        )
        # 协议没返回名字时保留已有名字，清空会让日志里的群号变回一串数字
        self.assertEqual(self.group_names.get_name("1"), "旧名")

    async def test_save_without_keyword_groups_fails_before_writing(self) -> None:
        # 配置缺本插件的键说明调用方没规范化，宁可直接失败也不写半份
        with self.assertRaises(ValueError):
            await self.store.save_with_group_names({}, [GroupName("1", "甲")])
        self.assertEqual(self.store.count(), 0)
        self.assertEqual(self.group_names.list_all(), [])

    async def test_save_reopen_reads_config_and_names(self) -> None:
        await self.store.save_with_group_names(
            {CFG_KEYWORD_GROUPS: ["1"]}, [GroupName("1", "甲")]
        )
        # 重启后配置和群名都还在
        self.assertEqual(
            SettingStore(self.db_path).load_dict(), {CFG_KEYWORD_GROUPS: ["1"]}
        )
        self.assertEqual(GroupNameStore(self.db_path).get_name("1"), "甲")

    async def test_save_rolls_back_when_group_name_write_fails(self) -> None:
        await self.store.save_with_group_names(
            {CFG_KEYWORD_GROUPS: ["1"]}, [GroupName("1", "甲")]
        )

        def boom(conn, group_names):
            # 事务中途抛错，配置和群名都必须回到调用前的值
            raise RuntimeError("注入的写入失败")

        self.store._write_group_names_sync = boom
        with self.assertRaises(RuntimeError):
            await self.store.save_with_group_names(
                {CFG_KEYWORD_GROUPS: ["1", "2"]}, [GroupName("1", "新名")]
            )
        self.assertEqual(self.store.load_dict(), {CFG_KEYWORD_GROUPS: ["1"]})
        self.assertEqual(self.group_names.get_name("1"), "甲")
        self.assertEqual(self.group_names.get_name("2"), "")
