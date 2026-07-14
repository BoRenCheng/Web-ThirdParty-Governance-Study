"""
crawler/tranco_sampler.py
=========================
Tranco List 分層抽樣程式。

功能：
1. 讀取 dataset/raw/tranco/tranco_top_1m.csv（格式：rank,domain）。
2. 依 rank 分成 Tier1（1~1000）、Tier2（1001~50000）、Tier3（50001~1000000）。
3. 每個 Tier 內隨機抽樣（固定隨機種子，可重現），產出：
   - dataset/processed/samples/sample_full.csv （100 + 400 + 500 = 1000 個）
   - dataset/processed/samples/pilot_100.csv    （10 + 40 + 50 = 100 個）
   - dataset/processed/samples/pilot_30.csv     （5 + 10 + 15 = 30 個）

抽樣設計說明：
- 先抽出 sample_full，pilot_100 是 sample_full 每個 Tier 的前段子集，
  pilot_30 又是 pilot_100 的子集。
- 這樣 pilot_30 ⊆ pilot_100 ⊆ sample_full，
  之後擴大樣本時，pilot 階段已下載的資料可以直接沿用，不會浪費。
- site_id 依 sample_full 的順序編成 S000001、S000002...，
  同一個網站在三個檔案中的 site_id 完全相同。

執行方式：
    python -m crawler.tranco_sampler --input dataset/raw/tranco/tranco_top_1m.csv
    python -m crawler.tranco_sampler --demo   # 測試用假資料，不能當研究結果！
"""

import argparse
import random
import sys

import pandas as pd

from config.constants import PILOT_30, PILOT_100, TIERS
from config.paths import (
    PILOT_30_CSV,
    PILOT_100_CSV,
    SAMPLE_DIR,
    SAMPLE_FULL_CSV,
    TRANCO_CSV,
    TRANCO_DIR,
)
from config.settings import RANDOM_SEED
from crawler.utils import get_logger

logger = get_logger("tranco_sampler")

# 輸出 CSV 的欄位順序
OUTPUT_COLUMNS = ["site_id", "domain", "rank", "tier", "category", "included", "note"]


def load_tranco(input_path) -> pd.DataFrame:
    """
    讀取 Tranco CSV。

    Tranco 官方下載檔通常「沒有標題列」（第一行直接是 1,google.com），
    但也支援有標題列（rank,domain）的檔案，兩種都能讀。
    """
    # 先看第一行判斷有沒有標題
    with open(input_path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()

    if first_line.lower().startswith("rank"):
        df = pd.read_csv(input_path)
        df.columns = [c.strip().lower() for c in df.columns]
    else:
        df = pd.read_csv(input_path, header=None, names=["rank", "domain"])

    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    df = df.dropna(subset=["rank", "domain"]).copy()
    df["rank"] = df["rank"].astype(int)
    return df[["rank", "domain"]]


def stratified_sample(tranco: pd.DataFrame) -> pd.DataFrame:
    """
    對 Tranco 名單做分層抽樣，回傳 sample_full（含 tier 欄位）。

    每個 Tier 依 rank 範圍切出母體，再用固定隨機種子抽出 n 個。
    若母體不足 n 個（例如 demo 假資料），就全取，並記錄警告。
    """
    rng = random.Random(RANDOM_SEED)
    sampled_parts = []

    for tier_name, spec in TIERS.items():
        pool = tranco[(tranco["rank"] >= spec["start"]) & (tranco["rank"] <= spec["end"])]
        n = spec["n"]
        if len(pool) < n:
            logger.warning(
                "%s 母體只有 %d 個（需要 %d 個），將全數納入。", tier_name, len(pool), n
            )
            n = len(pool)
        # rng.sample 保證不重複抽樣
        chosen_idx = rng.sample(list(pool.index), n)
        part = pool.loc[chosen_idx].copy()
        part["tier"] = tier_name
        part = part.sort_values("rank")  # Tier 內依 rank 排序，方便閱讀
        sampled_parts.append(part)

    full = pd.concat(sampled_parts, ignore_index=True)

    # 指定 site_id：S000001、S000002...（依 Tier1 -> Tier3、rank 由小到大的順序）
    full.insert(0, "site_id", [f"S{i + 1:06d}" for i in range(len(full))])

    # 補上其餘欄位的預設值
    full["category"] = "unknown"  # 網站類別，之後階段再人工/自動標註
    full["included"] = 1          # 1 = 納入分析；若之後要排除某網站，改 0 並在 note 說明
    full["note"] = ""
    return full[OUTPUT_COLUMNS]


def take_pilot(full: pd.DataFrame, quota: dict) -> pd.DataFrame:
    """
    從 sample_full 中取出 pilot 子集。

    quota 例如 {"Tier1": 5, "Tier2": 10, "Tier3": 15}。
    取每個 Tier 的前 n 個（sample_full 內 Tier 已依 rank 排序），
    因此 pilot_30 ⊆ pilot_100 ⊆ sample_full。
    """
    parts = [
        full[full["tier"] == tier_name].head(n)
        for tier_name, n in quota.items()
    ]
    return pd.concat(parts, ignore_index=True)


def make_demo_tranco() -> pd.DataFrame:
    """
    建立 demo 用的假 Tranco 名單（僅供測試程式流程）。

    注意：demo 資料是隨機產生的假網域，「絕對不能」當作正式研究資料！
    """
    rng = random.Random(RANDOM_SEED)
    rows = []
    # 產生足夠涵蓋三個 Tier 的稀疏假名單
    demo_ranks = (
        list(range(1, 1001))                                  # Tier1 全部
        + rng.sample(range(1001, 50001), 2000)                # Tier2 抽一部分
        + rng.sample(range(50001, 1000001), 3000)             # Tier3 抽一部分
    )
    for r in sorted(set(demo_ranks)):
        rows.append({"rank": r, "domain": f"demo-site-{r}.example"})
    return pd.DataFrame(rows)


def run(input_path=None, demo: bool = False) -> None:
    """主流程：讀取名單 -> 分層抽樣 -> 輸出三個 CSV。"""
    if demo:
        logger.warning("=== DEMO 模式：使用隨機假資料，不能當作研究結果！ ===")
        tranco = make_demo_tranco()
    else:
        input_path = input_path or TRANCO_CSV
        from pathlib import Path
        input_path = Path(input_path)
        if not input_path.exists():
            print()
            print("找不到 Tranco List 檔案！")
            print(f"請先將 Tranco List CSV 放到 {TRANCO_DIR / 'tranco_top_1m.csv'}")
            print("下載位置：https://tranco-list.eu/ （選 Full list，解壓縮後改名）")
            print("預期格式：rank,domain（或無標題列的 1,google.com）")
            print()
            print("若只是想測試程式流程，可執行：python -m crawler.tranco_sampler --demo")
            sys.exit(1)
        tranco = load_tranco(input_path)
        logger.info("已讀取 Tranco 名單：%d 筆", len(tranco))

    full = stratified_sample(tranco)
    pilot_100 = take_pilot(full, PILOT_100)
    pilot_30 = take_pilot(full, PILOT_30)

    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    full.to_csv(SAMPLE_FULL_CSV, index=False, encoding="utf-8")
    pilot_100.to_csv(PILOT_100_CSV, index=False, encoding="utf-8")
    pilot_30.to_csv(PILOT_30_CSV, index=False, encoding="utf-8")

    logger.info("已輸出 %s（%d 筆）", SAMPLE_FULL_CSV, len(full))
    logger.info("已輸出 %s（%d 筆）", PILOT_100_CSV, len(pilot_100))
    logger.info("已輸出 %s（%d 筆）", PILOT_30_CSV, len(pilot_30))
    if demo:
        logger.warning("提醒：以上為 DEMO 假資料，正式研究請放入真實 Tranco CSV 後重跑。")


def main():
    parser = argparse.ArgumentParser(description="Tranco List 分層抽樣")
    parser.add_argument(
        "--input",
        default=None,
        help="Tranco CSV 路徑（預設 dataset/raw/tranco/tranco_top_1m.csv）",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="使用假資料測試流程（不能當研究結果）",
    )
    args = parser.parse_args()
    run(input_path=args.input, demo=args.demo)


if __name__ == "__main__":
    main()
