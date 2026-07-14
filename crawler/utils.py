"""
crawler/utils.py
================
爬蟲共用工具：日誌、日期處理、禮貌性等待。
"""

import logging
import sys
import time
from datetime import date, datetime

from config.constants import REQUEST_SLEEP_SECONDS
from config.paths import LOG_DIR
from config.settings import LOG_LEVEL


def get_logger(name: str) -> logging.Logger:
    """
    建立同時輸出到「終端機」與「logs/{name}.log」的 logger。

    每個模組用自己的名字呼叫一次即可；重複呼叫不會重複掛 handler。
    """
    logger = logging.getLogger(name)
    if logger.handlers:  # 已經設定過就直接回傳，避免重複輸出
        return logger

    logger.setLevel(LOG_LEVEL)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # 輸出到終端機
    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(fmt)
    logger.addHandler(stream)

    # 輸出到 logs/ 目錄（若目錄不存在則自動建立）
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(LOG_DIR / f"{name}.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


def today_yyyymmdd() -> str:
    """回傳今天日期的 YYYYMMDD 字串，例如 '20260713'。"""
    return date.today().strftime("%Y%m%d")


def clamp_to_today(date_str: str) -> str:
    """
    如果 date_str（YYYYMMDD）是未來日期，改成今天。

    用途：查詢 2026 年快照時，若 2026-08-31 還沒發生，
    不可以把未來日期丟給 Wayback API，要自動改成今天。
    """
    today = today_yyyymmdd()
    return min(date_str, today)  # YYYYMMDD 字串可直接按字典序比大小


def parse_wayback_timestamp(ts: str) -> datetime:
    """把 Wayback 的 14 碼 timestamp（YYYYMMDDhhmmss）轉成 datetime。"""
    return datetime.strptime(ts[:14], "%Y%m%d%H%M%S")


def polite_sleep(seconds: float = REQUEST_SLEEP_SECONDS) -> None:
    """每次網路請求之間等待一下，避免對 Wayback Machine 造成壓力。"""
    time.sleep(seconds)
