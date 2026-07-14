"""
parser/html_parser.py
=====================
HTML 靜態解析器：從一份 HTML 快照中抽出所有外部資源引用。

解析的標籤與屬性：
    script[src]   -> resource_type = "script"   （TDI 第一版的核心）
    link[href]    -> resource_type = "link"     （CSS、字型、icon 等）
    iframe[src]   -> resource_type = "iframe"   （嵌入的第三方內容）
    img[src]      -> resource_type = "image"    （先保留，TDI 第一版不使用）
    source[src]   -> resource_type = "media"    （先保留，TDI 第一版不使用）

每個資源輸出一筆 record（dict），欄位見 RECORD_COLUMNS。
HTML 檔案不存在或解析失敗時，回傳空 list 並記錄錯誤，絕不中斷批次流程。
"""

from pathlib import Path

from bs4 import BeautifulSoup

from crawler.utils import get_logger
from parser.domain_extractor import (
    get_registrable_domain,
    get_host,
    is_third_party,
    normalize_url,
)

logger = get_logger("html_parser")

# static_resources.csv 的欄位順序
RECORD_COLUMNS = [
    "site_id", "domain", "year",
    "tag", "source_attr", "resource_type",
    "resource_url", "resource_domain", "registrable_domain",
    "is_third_party", "local_html_path",
]

# 要解析的 (標籤, 屬性, resource_type) 對應表
TAG_SPECS = [
    ("script", "src", "script"),
    ("link", "href", "link"),
    ("iframe", "src", "iframe"),
    ("img", "src", "image"),
    ("source", "src", "media"),
]

# Wayback 播放器自己注入的靜態資源（不是原網站的資源），要排除
_WAYBACK_ARTIFACTS = ("web.archive.org/_static/", "web-static.archive.org", "archive.org/includes/")


def _is_wayback_artifact(url: str) -> bool:
    """判斷該資源是不是 Wayback Machine 播放介面自己注入的檔案。"""
    return any(marker in url for marker in _WAYBACK_ARTIFACTS)


def parse_static_resources(html_path, site_id: str, domain: str, year: int) -> list:
    """
    解析單一 HTML 檔，回傳資源 record 的 list。

    參數：
        html_path -- HTML 檔案路徑
        site_id   -- 網站編號（S000001）
        domain    -- 網站主網域（用來判斷第三方，也用來解析相對路徑）
        year      -- 快照年份

    回傳：
        list[dict]，每個 dict 是一筆資源。失敗時回傳 []。
    """
    html_path = Path(html_path)
    if not html_path.exists():
        logger.error("HTML 檔案不存在：%s", html_path)
        return []

    try:
        html = html_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.error("HTML 讀取失敗 %s：%s", html_path, exc)
        return []

    try:
        # 優先使用 lxml（快），沒安裝時退回內建 html.parser
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        logger.error("HTML 解析失敗 %s：%s", html_path, exc)
        return []

    # 相對路徑以原網站首頁為基準（我們下載的是 id_ 未改寫 HTML，
    # 相對路徑本來就是相對於原網站）
    base_url = f"https://{domain}/"

    records = []
    for tag_name, attr, resource_type in TAG_SPECS:
        for element in soup.find_all(tag_name):
            raw_url = element.get(attr)
            if not raw_url:
                continue  # 例如 inline <script> 沒有 src，跳過

            resource_url = normalize_url(base_url, raw_url)
            if not resource_url:
                continue  # data:、javascript: 等非外部資源
            if _is_wayback_artifact(resource_url):
                continue  # Wayback 自己注入的檔案，不屬於原網站

            records.append({
                "site_id": site_id,
                "domain": domain,
                "year": year,
                "tag": tag_name,
                "source_attr": attr,
                "resource_type": resource_type,
                "resource_url": resource_url,
                "resource_domain": get_host(resource_url),           # 完整主機名
                "registrable_domain": get_registrable_domain(resource_url),  # eTLD+1
                "is_third_party": int(is_third_party(domain, resource_url)),
                "local_html_path": str(html_path),
            })

    return records
