"""
parser/run_static_parser.py
===========================
靜態解析主程式：把所有下載成功的 HTML 快照解析成一張大表。

輸入：
    dataset/processed/resources/snapshot_metadata.csv（wayback_downloader 的輸出）
    dataset/raw/wayback/{year}/{site_id}.html

輸出：
    dataset/processed/resources/static_resources.csv

執行方式：
    python -m parser.run_static_parser --metadata dataset/processed/resources/snapshot_metadata.csv
"""

import argparse
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from config.paths import ROOT_DIR, SNAPSHOT_METADATA_CSV, STATIC_RESOURCES_CSV
from crawler.utils import get_logger
from parser.html_parser import RECORD_COLUMNS, parse_static_resources

logger = get_logger("run_static_parser")


def run(metadata_path=None, output_path=None) -> None:
    """主流程：讀 metadata -> 逐檔解析 -> 合併輸出 static_resources.csv。"""
    metadata_path = Path(metadata_path or SNAPSHOT_METADATA_CSV)
    output_path = Path(output_path or STATIC_RESOURCES_CSV)

    if not metadata_path.exists():
        print(f"找不到 metadata 檔：{metadata_path}")
        print("請先執行：python -m crawler.wayback_downloader --sample dataset/processed/samples/pilot_30.csv")
        raise SystemExit(1)

    metadata = pd.read_csv(metadata_path)
    # 只處理下載成功的快照
    to_parse = metadata[metadata["downloaded"] == 1]
    logger.info("metadata 共 %d 筆，其中下載成功 %d 筆", len(metadata), len(to_parse))

    all_records = []
    for _, row in tqdm(to_parse.iterrows(), total=len(to_parse), desc="解析 HTML", unit="file"):
        # local_path 存的是相對路徑，這裡以專案根目錄補成絕對路徑
        html_path = ROOT_DIR / str(row["local_path"])
        records = parse_static_resources(
            html_path=html_path,
            site_id=row["site_id"],
            domain=row["domain"],
            year=int(row["target_year"]),
        )
        all_records.extend(records)

    # 就算完全沒有資源，也輸出「有欄位名稱的空 CSV」，讓下游程式不會壞掉
    resources = pd.DataFrame(all_records, columns=RECORD_COLUMNS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    resources.to_csv(output_path, index=False, encoding="utf-8")

    logger.info("已輸出 %s（%d 筆資源）", output_path, len(resources))
    if len(resources):
        n_third = int(resources["is_third_party"].sum())
        logger.info("其中第三方資源 %d 筆（%.1f%%）", n_third, 100 * n_third / len(resources))


def main():
    parser = argparse.ArgumentParser(description="HTML 靜態資源解析")
    parser.add_argument(
        "--metadata",
        default=None,
        help="snapshot_metadata.csv 路徑（預設 dataset/processed/resources/snapshot_metadata.csv）",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="輸出 CSV 路徑（預設 dataset/processed/resources/static_resources.csv）",
    )
    args = parser.parse_args()
    run(metadata_path=args.metadata, output_path=args.output)


if __name__ == "__main__":
    main()
