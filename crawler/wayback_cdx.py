"""
crawler/wayback_cdx.py
======================
Wayback Machine CDX API 查詢模組。

CDX API 是 Internet Archive 提供的快照索引查詢介面，
給定網域與日期範圍，回傳該網域首頁在此期間的所有快照清單。

API 文件：https://github.com/internetarchive/wayback/tree/master/wayback-cdx-server
"""

from typing import Optional

import pandas as pd
import requests

from config.constants import MAX_RETRIES, REQUEST_TIMEOUT
from config.settings import CDX_API_URL, USER_AGENT
from crawler.utils import get_logger, parse_wayback_timestamp, polite_sleep

logger = get_logger("wayback_cdx")

# CDX 回傳的欄位（fl 參數指定）
CDX_FIELDS = ["timestamp", "original", "statuscode", "mimetype", "digest"]


def query_cdx(
    domain: str,
    from_date: str,
    to_date: str,
    session: Optional[requests.Session] = None,
) -> pd.DataFrame:
    """
    查詢某網域在 [from_date, to_date] 期間的 Wayback 快照。

    參數：
        domain     -- 網域，例如 "example.com"
        from_date  -- 起始日期 YYYYMMDD
        to_date    -- 結束日期 YYYYMMDD
        session    -- 可重複使用的 requests.Session（批次查詢時較有效率）

    回傳：
        DataFrame，欄位為 timestamp, original, statuscode, mimetype, digest。
        查無資料或多次重試仍失敗時，回傳「空的 DataFrame」（不丟例外），
        確保單一網站的錯誤不會中斷整個批次流程。
    """
    params = {
        "url": domain,
        "from": from_date,
        "to": to_date,
        "output": "json",
        "fl": ",".join(CDX_FIELDS),
        "filter": "statuscode:200",  # 只要成功的快照
        "collapse": "digest",        # 內容相同的快照只留一筆
    }
    http = session or requests
    empty = pd.DataFrame(columns=CDX_FIELDS)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = http.get(
                CDX_API_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json() if resp.text.strip() else []
            if len(data) <= 1:
                # CDX JSON 第一列是欄位名稱；只有一列（或全空）代表沒有快照
                return empty
            return pd.DataFrame(data[1:], columns=data[0])
        except (requests.RequestException, ValueError) as exc:
            # ValueError 涵蓋 JSON 解析失敗
            logger.warning(
                "CDX 查詢失敗（%s，第 %d/%d 次）：%s",
                domain, attempt, MAX_RETRIES, exc,
            )
            if attempt < MAX_RETRIES:
                polite_sleep(attempt * 2)  # 每次重試等久一點（2s, 4s）

    logger.error("CDX 查詢多次失敗，放棄：%s（%s~%s）", domain, from_date, to_date)
    return empty


def select_best_snapshot(df: pd.DataFrame, target_date: str) -> Optional[pd.Series]:
    """
    從快照清單中選出「timestamp 離 target_date 最近」的一筆。

    參數：
        df          -- query_cdx() 的回傳結果
        target_date -- 目標日期 YYYYMMDD，例如 "20220715"（該年 7 月 15 日）

    回傳：
        pd.Series（該筆快照的欄位），若 df 為空則回傳 None。
    """
    if df is None or df.empty:
        return None

    target = parse_wayback_timestamp(target_date + "120000")  # 對齊到中午
    diffs = df["timestamp"].map(
        lambda ts: abs((parse_wayback_timestamp(ts) - target).total_seconds())
    )
    return df.loc[diffs.idxmin()]
