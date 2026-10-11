# 实体层：本插件用到的固定值。不依赖 AstrBot，也不访问数据库。

# 关键词回复单独一个 SQLite 文件，只放本插件自己的表。
# 功能开没开改走 WebUI 群号名单，不看库里的开关行。
DB_FILE_NAME = "keyword_reply.db"

# WebUI：开启关键词回复的群号名单。空名单即关，不兼容旧的 SQLite 开关表。
CFG_KEYWORD_GROUPS = "keyword_groups"

# 关键词长度上限。命中要求整条消息与关键词完全相等，太长没人会真的发出来，
# 只会白占内存快照。
KEYWORD_MAX_LEN = 100

# 回复文本长度上限。够写一段通知，又不至于被管理员误塞进一整篇文章。
REPLY_MAX_LEN = 500

# 列关键词时一次最多回多少条。超出的只报数量，不刷屏。
KEYWORD_LIST_LIMIT = 30
# WebUI 关键词表默认每页条数。
KEYWORD_PAGE_SIZE = 20

# 读不到 AstrBot 真实配置时的兜底唤醒前缀。AstrBot 自己的默认值也是 /。
DEFAULT_WAKE_PREFIX = "/"

# 注册插件 Page API 时用的插件名，必须和仓库目录名一致。
PLUGIN_NAME = "astrbot_plugin_keyword_reply"

# 本插件只有 1 个配置键，按存储类型分组。schema 只在导入时读一次，之后 Pages 保存和
# 热路径都读 keyword_reply.db 的 plugin_setting，按这份分组决定怎么存。
SETTING_LIST_KEYS = (CFG_KEYWORD_GROUPS,)
# 本插件没有文本类配置键。
SETTING_TEXT_KEYS = ()
# 本插件没有整数类配置键。
SETTING_INT_KEYS = ()
# 本插件没有布尔类配置键。
SETTING_BOOL_KEYS = ()
# 布尔在 plugin_setting 里只有这两种写法。别的值读出来一律当 False。
SETTING_TRUE = "1"
SETTING_FALSE = "0"
