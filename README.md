# astrbot_plugin_keyword_reply

AstrBot 插件：群关键词回复。用中文交流。

三插件拆分（群管 / 入群流程 / 关键词回复）里的关键词插件，方案见原仓库
`astrbot_plugin_w1ndys_rules` 的 `specs/split-into-three-plugins/`。

## 当前状态

本仓库已有实体、存储与配置 schema，**仍不是可安装的 AstrBot 插件**：

- 已有：根包 `__init__.py`、`entity/`（常量与数据形状）、`data/`（SQLite 存储，库名固定 `keyword_reply.db`）、`_conf_schema.json`（只有 `keyword_groups` 一个键）、`business/` 与 `tests/` 包入口、`pyproject.toml`（ruff 配置）、空 `requirements.txt`。
- 未建：`main.py`、`metadata.yaml`、业务代码与控制台页面，所以宿主现在还装不上、也没有页面。这些按任务清单后续补齐。

## 依赖

无额外第三方包，`requirements.txt` 保持空文件；运行时只依赖 AstrBot 宿主，不需要群管插件的视觉相关依赖，也不依赖另外两个插件。

## 编码契约

本仓库开发默认启用 `.agents/skills/human-coding-contract/SKILL.md`（人话编码契约 / 土法编码 / 分层交付），规则见 `AGENTS.md`。

## 检查

```bash
# 两条都在仓库根执行；括号让 unittest 跑完回到根目录，保证 ruff 作用于全仓
(cd tests && ../.venv/bin/python -m unittest)
ruff check .
```

`.venv` 按需在本机自建，不入库。`ruff check .` 必须在仓库根跑，不要在 `tests/` 下跑，否则只检查测试目录。
