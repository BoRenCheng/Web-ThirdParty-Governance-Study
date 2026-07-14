"""
crawler/wayback_downloader.py
=============================
Wayback Machine HTML 快照下載器。

流程（對 sample 中每個網站 × 每個目標年份 2022/2024/2026）：
1. 用 CDX API 查 6/1~8/31 的快照。
2. 找不到 -> 放寬到 5/1~9/30 再查一次。
3. 還是找不到 -> 在 metadata 標記 downloaded=0、error_message=missing_snapshot。
4. 找到 -> 選離 7/15 最近的快照，下載 HTML 存到 dataset/raw/wayback/{year}/{site_id}.html。

2026 特別規則：
- 若今天還沒到 2026-08-31，查詢的結束日期自動改成今天（不能查未來）。
- 若整個查詢起始日期都在未來（例如 2025 年就跑 2026 的查詢），直接標記 missing。

下載網址的小細節（重要，影響研究正確性）：
- metadata 中記錄的 snapshot_url 是標準格式：
      https://web.archive.org/web/{timestamp}/{original}
- 但實際下載時使用 "id_" 變體：
      https://web.archive.org/web/{timestamp}id_/{original}
  id_ 會回傳「未經 Wayback 改寫的原始 HTML」。
  若用標準網址，頁面中所有資源網址都會被改寫成 web.archive.org/web/...，
  會讓第三方偵測全部失真。使用 id_ 是 Web measurement 研究的標準做法。

執行方式：
    python -m crawler.wayback_downloader --sample dataset/processed/samples/pilot_30.csv
"""

import argparse
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm

from config.constants import (
    MAX_RETRIES,
    RELAXED_MONTHS,
    REQUEST_TIMEOUT,
    TARGET_DAY,
    TARGET_MONTHS,
    TARGET_YEARS,
)
from config.paths import PILOT_30_CSV, RESOURCE_DIR, SNAPSHOT_METADATA_CSV, WAYBACK_DIR
from config.settings import USER_AGENT
from crawler.utils import clamp_to_today, get_logger, polite_sleep, today_yyyymmdd
from crawler.wayback_cdx import query_cdx, select_best_snapshot

logger = get_logger("wayback_downloader")

# snapshot_metadata.csv 的欄位順序
METADATA_COLUMNS = [
    "site_id", "domain", "rank", "tier",
    "target_year", "target_from", "target_to",
    "timestamp", "original", "status_code", "mime_type",
    "snapshot_url", "downloaded", "local_path", "error_message",
]


def build_snapshot_url(timestamp: str, original: str) -> str:
    """組出人類可讀的 Wayback 快照網址（記錄在 metadata 中）。"""
    return f"https://web.archive.org/web/{timestamp}/{original}"


def build_download_url(timestamp: str, original: str) -> str:
    """組出 id_ 原始內容網址（實際下載用，取得未改寫的 HTML）。"""
    return f"https://web.archive.org/web/{timestamp}id_/{original}"


def looks_like_html(text: str) -> bool:
    """粗略檢查回應內容是否像 HTML（避免存到空檔或錯誤頁）。"""
    if not text or not text.strip():
        return False
    head = text[:2000].lower()
    return "<html" in head or "<!doctype" in head or "<head" in head or "<body" in head


def download_html(url: str, session: requests.Session):
    """
    下載快照 HTML，回傳 (html_text, error_message)。
    成功時 error_message 為空字串；失敗時 html_text 為 None。
    含 timeout / retry / sleep。
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
                allow_redirects=True,
            )
            if resp.status_code != 200:
                error = f"http_error:{resp.status_code}"
                logger.warning("HTTP %s：%s（第 %d 次）", resp.status_code, url, attempt)
            elif not resp.text or not resp.text.strip():
                error = "empty_response"
            elif not looks_like_html(resp.text):
                error = "invalid_html"
            else:
                return resp.text, ""
        except requests.Timeout:
            error = "timeout"
            logger.warning("timeout：%s（第 %d 次）", url, attempt)
        except requests.RequestException as exc:
            error = f"http_error:{type(exc).__name__}"
            logger.warning("請求失敗：%s（第 %d 次）%s", url, attempt, exc)

        if attempt < MAX_RETRIES:
            polite_sleep(attempt * 2)  # 重試前多等一下

    return None, error


def process_site_year(row: pd.Series, year: int, session: requests.Session) -> dict:
    """
    處理「單一網站 × 單一年份」，回傳一筆 metadata dict。
    任何錯誤都轉成 error_message 記錄，絕不往外丟例外。
    """
    domain = row["domain"]
    from_date, to_date = TARGET_MONTHS[year]

    # ---- 2026 特別規則：結束日期不可以是未來 ----
    to_date = clamp_to_today(to_date)

    record = {
        "site_id": row["site_id"],
        "domain": domain,
        "rank": row["rank"],
        "tier": row["tier"],
        "target_year": year,
        "target_from": from_date,
        "target_to": to_date,
        "timestamp": "",
        "original": "",
        "status_code": "",
        "mime_type": "",
        "snapshot_url": "",
        "downloaded": 0,
        "local_path": "",
        "error_message": "",
    }

    # 整個查詢期間都還沒發生（例如提前跑未來年份）-> 直接標記 missing
    if from_date > today_yyyymmdd():
        record["error_message"] = "missing_snapshot"
        return record

    # ---- 步驟 1：查主要期間（6/1 ~ 8/31）----
    snapshots = query_cdx(domain, from_date, to_date, session=session)
    polite_sleep()

    # ---- 步驟 2：找不到就放寬期間（5/1 ~ 9/30）----
    if snapshots.empty:
        relaxed_from, relaxed_to = RELAXED_MONTHS[year]
        relaxed_to = clamp_to_today(relaxed_to)
        if relaxed_from <= today_yyyymmdd():
            record["target_from"] = relaxed_from
            record["target_to"] = relaxed_to
            snapshots = query_cdx(domain, relaxed_from, relaxed_to, session=session)
            polite_sleep()

    # ---- 步驟 3：仍然沒有快照 -> missing_snapshot ----
    if snapshots.empty:
        record["error_message"] = "missing_snapshot"
        return record

    # ---- 步驟 4：選離 7/15 最近的快照 ----
    best = select_best_snapshot(snapshots, f"{year}{TARGET_DAY}")
    record["timestamp"] = best["timestamp"]
    record["original"] = best["original"]
    record["status_code"] = best["statuscode"]
    record["mime_type"] = best["mimetype"]
    record["snapshot_url"] = build_snapshot_url(best["timestamp"], best["original"])

    # ---- 步驟 5：下載 HTML ----
    download_url = build_download_url(best["timestamp"], best["original"])
    html, error = download_html(download_url, session)
    polite_sleep()

    if html is None:
        record["error_message"] = error
        return record

    # ---- 步驟 6：存檔 dataset/raw/wayback/{year}/{site_id}.html ----
    year_dir = WAYBACK_DIR / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    local_path = year_dir / f"{row['site_id']}.html"
    local_path.write_text(html, encoding="utf-8", errors="replace")

    record["downloaded"] = 1
    # local_path 記錄「相對於專案根目錄」的路徑，換電腦也能用
    record["local_path"] = str(Path("dataset/raw/wayback") / str(year) / f"{row['site_id']}.html")
    return record


def run(sample_path=None) -> None:
    """主流程：讀取 sample -> 逐站逐年下載 -> 輸出 snapshot_metadata.csv。"""
    sample_path = Path(sample_path or PILOT_30_CSV)
    if not sample_path.exists():
        print(f"找不到樣本檔：{sample_path}")
        print("請先執行：python -m crawler.tranco_sampler --input dataset/raw/tranco/tranco_top_1m.csv")
        raise SystemExit(1)

    sample = pd.read_csv(sample_path)
    # 只處理 included=1 的網站
    if "included" in sample.columns:
        sample = sample[sample["included"] == 1]

    logger.info("樣本：%s（%d 個網站 × %d 個年份 = %d 個任務）",
                sample_path, len(sample), len(TARGET_YEARS), len(sample) * len(TARGET_YEARS))

    session = requests.Session()
    records = []

    # tqdm 進度條：總任務數 = 網站數 × 年份數
    tasks = [(row, year) for _, row in sample.iterrows() for year in TARGET_YEARS]
    for row, year in tqdm(tasks, desc="下載 Wayback 快照", unit="task"):
        try:
            record = process_site_year(row, year, session)
        except Exception as exc:  # 最後防線：任何漏網例外都不中斷批次
            logger.error("未預期錯誤 %s/%s：%s", row["domain"], year, exc)
            record = {c: "" for c in METADATA_COLUMNS}
            record.update({
                "site_id": row["site_id"], "domain": row["domain"],
                "rank": row["rank"], "tier": row["tier"],
                "target_year": year, "downloaded": 0,
                "error_message": f"unexpected:{type(exc).__name__}",
            })
        records.append(record)

    RESOURCE_DIR.mkdir(parents=True, exist_ok=True)
    metadata = pd.DataFrame(records, columns=METADATA_COLUMNS)
    metadata.to_csv(SNAPSHOT_METADATA_CSV, index=False, encoding="utf-8")

    ok = int((metadata["downloaded"] == 1).sum())
    fail = len(metadata) - ok
    logger.info("完成：成功 %d、失敗/缺漏 %d", ok, fail)
    if fail:
        logger.info("失敗原因統計：\n%s",
                    metadata.loc[metadata["downloaded"] != 1, "error_message"].value_counts().to_string())
    logger.info("metadata 已輸出：%s", SNAPSHOT_METADATA_CSV)


def main():
    parser = argparse.ArgumentParser(description="Wayback Machine HTML 快照下載器")
    parser.add_argument(
        "--sample",
        default=None,
        help="樣本 CSV 路徑（預設 dataset/processed/samples/pilot_30.csv）",
    )
    args = parser.parse_args()
    run(sample_path=args.sample)


if __name__ == "__main__":
    main()
