# 配置分片检查：本插件恰好 1 个配置键，constants、schema 与 load_dict 三处一致。

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT = str(ROOT.parent)
# 测试从仓库根的上一级导入包名 astrbot_plugin_keyword_reply
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

from astrbot_plugin_keyword_reply.data.setting_store import SettingStore
from astrbot_plugin_keyword_reply.entity.constants import (
    CFG_KEYWORD_GROUPS,
    DB_FILE_NAME,
    PLUGIN_NAME,
    SETTING_BOOL_KEYS,
    SETTING_INT_KEYS,
    SETTING_LIST_KEYS,
    SETTING_TEXT_KEYS,
)


class ConfigKeyTest(unittest.TestCase):
    # 配置键数量、库名和 schema 的一致性

    def test_only_one_setting_key(self) -> None:
        keys = (
            SETTING_LIST_KEYS
            + SETTING_TEXT_KEYS
            + SETTING_INT_KEYS
            + SETTING_BOOL_KEYS
        )
        # 关键词插件只留自己的名单键，多出任何一个都说明裁剪时漏了别的功能的键
        self.assertEqual(keys, (CFG_KEYWORD_GROUPS,))
        self.assertEqual(SETTING_TEXT_KEYS, ())
        self.assertEqual(SETTING_INT_KEYS, ())
        self.assertEqual(SETTING_BOOL_KEYS, ())

    def test_db_and_plugin_names_are_fixed(self) -> None:
        # 库名固定，迁移工具按这个文件名找本插件库
        self.assertEqual(DB_FILE_NAME, "keyword_reply.db")
        # 插件名必须和仓库目录名一致，Pages 路由前缀靠它
        self.assertEqual(PLUGIN_NAME, "astrbot_plugin_keyword_reply")

    def test_schema_has_same_single_key(self) -> None:
        schema = json.loads((ROOT / "_conf_schema.json").read_text(encoding="utf-8"))
        self.assertEqual(list(schema.keys()), [CFG_KEYWORD_GROUPS])
        item = schema[CFG_KEYWORD_GROUPS]
        # 沿用原仓的默认空名单和 invisible，宿主加载时才不会把名单显示成可编辑文本框
        self.assertEqual(item["type"], "list")
        self.assertEqual(item["default"], [])
        self.assertIs(item["invisible"], True)
        self.assertEqual(item["items"], {"type": "string"})

    def test_load_dict_has_same_single_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SettingStore(Path(tmp) / DB_FILE_NAME)
            self.assertEqual(list(store.load_dict().keys()), [CFG_KEYWORD_GROUPS])
