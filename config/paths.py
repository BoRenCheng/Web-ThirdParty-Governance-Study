"""
config/paths.py
===============
集中管理專案所有路徑。

設計原則：
1. 全部使用 pathlib.Path，不使用硬編的 Windows 絕對路徑（例如 C:\\Users\\...）。
2. 所有路徑都以「本檔案所在位置」往上推得專案根目錄（ROOT_DIR），
   因此不管專案被移到哪台電腦、哪個資料夾，路徑都會自動正確。
3. 其他模組一律 `from config.paths import ...`，不要自己拼路徑字串。
"""

from pathlib import Path

# 專案根目錄：config/paths.py 往上兩層就是專案根目錄
# （paths.py -> config/ -> website-governance-longitudinal-study/）
ROOT_DIR = Path(__file__).resolve().parents[1]

# ---- 資料集目錄 ----
DATASET_DIR = ROOT_DIR / "dataset"

# 原始資料（不進版本控制，見 .gitignore）
RAW_DIR = DATASET_DIR / "raw"
TRANCO_DIR = RAW_DIR / "tranco"      # Tranco Top 1M 名單
WAYBACK_DIR = RAW_DIR / "wayback"    # Wayback Machine 下載的 HTML 快照

# 處理後資料（進版本控制，體積小）
PROCESSED_DIR = DATASET_DIR / "processed"
SAMPLE_DIR = PROCESSED_DIR / "samples"        # 抽樣結果（pilot_30.csv 等）
RESOURCE_DIR = PROCESSED_DIR / "resources"    # 快照 metadata 與第三方資源清單
INDICATOR_DIR = PROCESSED_DIR / "indicators"  # TDI 等指標

# 外部補充資料（例如未來的 tracker 分類清單）
EXTERNAL_DIR = DATASET_DIR / "external"

# ---- 產出目錄 ----
FIGURE_DIR = ROOT_DIR / "figures"  # 圖表輸出
LOG_DIR = ROOT_DIR / "logs"        # 執行紀錄
DOCS_DIR = ROOT_DIR / "docs"       # 研究文件

# ---- 常用檔案路徑（讓各模組共用同一個「事實來源」）----
TRANCO_CSV = TRANCO_DIR / "tranco_top_1m.csv"
PILOT_30_CSV = SAMPLE_DIR / "pilot_30.csv"
PILOT_100_CSV = SAMPLE_DIR / "pilot_100.csv"
SAMPLE_FULL_CSV = SAMPLE_DIR / "sample_full.csv"
SNAPSHOT_METADATA_CSV = RESOURCE_DIR / "snapshot_metadata.csv"
STATIC_RESOURCES_CSV = RESOURCE_DIR / "static_resources.csv"
TDI_SCORES_CSV = INDICATOR_DIR / "tdi_scores.csv"

# scripts/init_dirs.py 會依照這個清單自動建立所有資料夾
ALL_DIRS = [
    TRANCO_DIR,
    WAYBACK_DIR,
    SAMPLE_DIR,
    RESOURCE_DIR,
    INDICATOR_DIR,
    EXTERNAL_DIR,
    FIGURE_DIR,
    LOG_DIR,
]
