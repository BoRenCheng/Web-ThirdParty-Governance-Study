"""
config/settings.py
==================
一般執行設定（非研究設計常數）。研究設計常數請見 config/constants.py。
"""

# 隨機種子：讓分層抽樣可以重現（reproducible）。
# 論文中報告抽樣方法時，必須包含這個種子。
RANDOM_SEED = 42

# Wayback Machine CDX API 端點
CDX_API_URL = "https://web.archive.org/cdx/search/cdx"

# 下載快照時使用的 User-Agent：
# 表明這是學術研究用途，並附上聯絡方式（禮貌爬蟲慣例）。
USER_AGENT = (
    "website-governance-longitudinal-study/0.1 "
    "(academic research; contact: raycheng940629@gmail.com)"
)

# 日誌等級
LOG_LEVEL = "INFO"
