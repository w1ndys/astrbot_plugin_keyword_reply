# 包骨架导入检查：确认根包与分层子包都来自本仓库，兄弟插件缺席时也能导入。

import sys
import unittest
from pathlib import Path

# ROOT 是本仓库根目录，用来核对导入到的包确实来自本仓
ROOT = Path(__file__).resolve().parents[1]
# PARENT 是仓库根的上一级目录，作为按包名导入本插件的搜索路径
PARENT = str(ROOT.parent)
# 测试从仓库根的上一级导入包名 astrbot_plugin_keyword_reply
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import astrbot_plugin_keyword_reply
from astrbot_plugin_keyword_reply import business, data, entity

# 本插件必须能单独加载，导入时不能顺带拉起另两个插件或旧原仓的包
SIBLING_PACKAGES = (
    "astrbot_plugin_group_manager",
    "astrbot_plugin_group_welcome",
    "astrbot_plugin_w1ndys_rules",
)


class PackageImportTest(unittest.TestCase):
    # 校验包骨架的来源和依赖边界

    def test_root_package_comes_from_this_repo(self) -> None:
        # 根包目录不是本仓库，说明吃到的是别的仓库的同名包，必须失败
        self.assertEqual(Path(astrbot_plugin_keyword_reply.__file__).resolve().parent, ROOT)

    def test_layer_packages_come_from_this_repo(self) -> None:
        # 三个分层子包必须分别落在本仓库已建好的目录里，缺哪个都说明骨架不完整
        self.assertEqual(Path(entity.__file__).resolve().parent, ROOT / "entity")
        self.assertEqual(Path(data.__file__).resolve().parent, ROOT / "data")
        self.assertEqual(Path(business.__file__).resolve().parent, ROOT / "business")

    def test_no_sibling_plugin_package_imported(self) -> None:
        # 内存里出现兄弟插件或旧原仓的包，等于单独安装时会导入失败
        for name in SIBLING_PACKAGES:
            self.assertNotIn(name, sys.modules)

    def test_requirements_is_empty(self) -> None:
        # requirements.txt 出现任何依赖行都会带进额外第三方包，本插件只允许空文件
        text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertEqual(text.strip(), "")
