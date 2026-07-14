"""
indicators/compute_tdi.py
=========================
TDI（Third-party Dependency Index，第三方依賴度指標）第一版計算。

定義：
    TDI = 0.5 x normalized(third_party_script_count)
        + 0.5 x normalized(third_party_domain_count)

其中：
    third_party_script_count -- 第三方 <script src> 的數量（技術耦合強度）
    third_party_domain_count -- 第三方 registrable domain 的個數（依賴廣度）
    正規化採 min-max，對「整個資料集（所有網站所有年份合併）」計算，
    因此同一批資料內、跨年份的 TDI 可以直接比較。

重要設計：
    某網站某年若「完全沒有第三方資源」，仍會出現在結果中，數值為 0。
    做法是從 snapshot_metadata.csv 讀取所有「下載成功」的（網站, 年份）組合，
    再把沒有第三方資源的組合補 0。

執行方式：
    python -m indicators.compute_tdi \
        --resources dataset/processed/resources/static_resources.csv \
        --metadata dataset/processed/resources/snapshot_metadata.csv \
        --output dataset/processed/indicators/tdi_scores.csv
"""

import argparse
from pathlib import Path
from typing import Optional

import pandas as pd

from config.paths import INDICATOR_DIR, SNAPSHOT_METADATA_CSV, STATIC_RESOURCES_CSV, TDI_SCORES_CSV
from crawler.utils import get_logger
from indicators.normalize import min_max_normalize

logger = get_logger("compute_tdi")

# tdi_scores.csv 的欄位順序
TDI_COLUMNS = [
    "site_id", "domain", "year",
    "third_party_script_count", "third_party_domain_count", "third_party_resource_count",
    "script_norm", "domain_norm", "tdi",
]

# TDI 第一版的權重
WEIGHT_SCRIPT = 0.5
WEIGHT_DOMAIN = 0.5


def compute_tdi(resources: pd.DataFrame, metadata: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    計算 TDI。這是純函式（不讀寫檔案），方便單元測試。

    參數：
        resources -- static_resources.csv 的內容
        metadata  -- snapshot_metadata.csv 的內容（可為 None）。
                     提供時，用來補齊「有快照但沒有第三方資源」的組合（數值為 0）。

    回傳：
        DataFrame，欄位見 TDI_COLUMNS。
    """
    # ---- 步驟 1：只取第三方資源 ----
    if resources is None or resources.empty:
        third = pd.DataFrame(columns=["site_id", "domain", "year",
                                      "resource_type", "registrable_domain"])
    else:
        third = resources[resources["is_third_party"] == 1].copy()

    # ---- 步驟 2：以 (site_id, domain, year) 分組計數 ----
    if third.empty:
        counts = pd.DataFrame(columns=[
            "site_id", "domain", "year",
            "third_party_script_count", "third_party_domain_count", "third_party_resource_count",
        ])
    else:
        counts = (
            third.groupby(["site_id", "domain", "year"])
            .agg(
                # 第三方 script 數：resource_type == "script" 的筆數
                third_party_script_count=("resource_type", lambda s: int((s == "script").sum())),
                # 第三方網域數：不重複的 registrable domain 個數
                third_party_domain_count=("registrable_domain", "nunique"),
                # 第三方資源總數（所有標籤類型）
                third_party_resource_count=("resource_type", "size"),
            )
            .reset_index()
        )

    # ---- 步驟 3：補齊缺漏的 (site_id, domain, year) 組合，數值為 0 ----
    # 來源優先用 metadata 中「下載成功」的組合；沒有 metadata 時，
    # 退而用 resources 中出現過的所有組合（含只有第一方資源的網站）。
    if metadata is not None and not metadata.empty:
        base = metadata[metadata["downloaded"] == 1][["site_id", "domain", "target_year"]].rename(
            columns={"target_year": "year"}
        )
    elif resources is not None and not resources.empty:
        base = resources[["site_id", "domain", "year"]]
    else:
        base = counts[["site_id", "domain", "year"]]

    base = base.drop_duplicates().copy()
    base["year"] = base["year"].astype(int)
    if not counts.empty:
        counts["year"] = counts["year"].astype(int)

    result = base.merge(counts, on=["site_id", "domain", "year"], how="left")
    count_cols = ["third_party_script_count", "third_party_domain_count", "third_party_resource_count"]
    for col in count_cols:
        if col not in result.columns:
            result[col] = 0
        result[col] = result[col].fillna(0).astype(int)

    # ---- 步驟 4：min-max 正規化（對整個資料集，跨年份可比較）----
    result["script_norm"] = min_max_normalize(result["third_party_script_count"])
    result["domain_norm"] = min_max_normalize(result["third_party_domain_count"])

    # ---- 步驟 5：計算 TDI ----
    result["tdi"] = WEIGHT_SCRIPT * result["script_norm"] + WEIGHT_DOMAIN * result["domain_norm"]

    return result.sort_values(["site_id", "year"]).reset_index(drop=True)[TDI_COLUMNS]


def run(resources_path=None, metadata_path=None, output_path=None) -> None:
    """主流程：讀檔 -> compute_tdi() -> 輸出 tdi_scores.csv。"""
    resources_path = Path(resources_path or STATIC_RESOURCES_CSV)
    metadata_path = Path(metadata_path or SNAPSHOT_METADATA_CSV)
    output_path = Path(output_path or TDI_SCORES_CSV)

    if not resources_path.exists():
        print(f"找不到資源檔：{resources_path}")
        print("請先執行：python -m parser.run_static_parser")
        raise SystemExit(1)

    resources = pd.read_csv(resources_path)
    metadata = pd.read_csv(metadata_path) if metadata_path.exists() else None
    if metadata is None:
        logger.warning("找不到 %s，無法補齊零第三方資源的網站。", metadata_path)

    scores = compute_tdi(resources, metadata)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("已輸出 %s（%d 筆 site-year）", output_path, len(scores))
    if len(scores):
        logger.info("TDI 摘要：\n%s", scores.groupby("year")["tdi"].describe().to_string())


def main():
    parser = argparse.ArgumentParser(description="計算 TDI 第三方依賴度指標")
    parser.add_argument("--input", "--resources", dest="resources", default=None,
                        help="static_resources.csv 路徑")
    parser.add_argument("--metadata", default=None,
                        help="snapshot_metadata.csv 路徑（用於補齊零值組合）")
    parser.add_argument("--output", default=None,
                        help="輸出 tdi_scores.csv 路徑")
    args = parser.parse_args()
    run(resources_path=args.resources, metadata_path=args.metadata, output_path=args.output)


if __name__ == "__main__":
    main()
