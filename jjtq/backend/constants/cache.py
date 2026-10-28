"""新闻列表缓存键和过期时间，时间单位均为秒。"""

# 新闻列表缓存键模板
NEWS_LIST_KEY_TEMPLATE = "jjtq:news:list:v1:{category_id}:{page}:{page_size}"

# 新闻列表缓存过期时间
NEWS_LIST_TTL_SECONDS = 600

# 新闻列表缓存过期时间抖动范围
NEWS_LIST_TTL_JITTER_SECONDS = 60

# 新闻列表为空时缓存的过期时间
NEWS_LIST_EMPTY_TTL_SECONDS = 60

# 新闻列表为空时缓存的过期时间抖动范围
NEWS_LIST_EMPTY_TTL_JITTER_SECONDS = 10
