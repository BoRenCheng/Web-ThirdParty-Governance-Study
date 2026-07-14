"""
parser/domain_extractor.py
==========================
網域解析工具：判斷資源網址屬於第一方還是第三方。

核心概念：registrable domain（可註冊網域，即 eTLD+1）
- cdn.example.com 的 registrable domain 是 example.com
- www.google-analytics.com 的 registrable domain 是 google-analytics.com
- 比較兩個網址是否「同一方」，就是比較它們的 registrable domain 是否相同。
- 使用 tldextract 處理 Public Suffix List（能正確處理 .co.uk、.com.tw 等複合頂級域）。
"""

import re
from urllib.parse import urljoin, urlparse

import tldextract

# suffix_list_urls=() 表示「不要上網抓最新的 Public Suffix List」，
# 直接用 tldextract 內建快照，確保離線可用且結果可重現。
_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=())

# 這些 scheme 不是外部 HTTP 資源，直接忽略
_IGNORED_SCHEMES = ("data:", "javascript:", "mailto:", "about:", "blob:", "#")

# Wayback 改寫網址的樣式：/web/20220715123456js_/https://example.com/app.js
# 理論上我們下載的是 id_ 原始 HTML 不會被改寫，但保險起見仍支援還原。
_WAYBACK_RE = re.compile(
    r"^(?:https?:)?//web\.archive\.org/web/\d{4,14}(?:[a-z]{2}_)?/(?P<orig>.+)$",
    re.IGNORECASE,
)


def unwrap_wayback_url(url: str) -> str:
    """
    如果 url 是 Wayback 改寫過的網址，還原出原始網址；否則原樣回傳。

    例：https://web.archive.org/web/20220715js_/https://cdn.example.com/a.js
        -> https://cdn.example.com/a.js
    """
    if not url:
        return url
    m = _WAYBACK_RE.match(url.strip())
    if m:
        orig = m.group("orig")
        # 還原出來可能是 //cdn.example.com/... 或缺 scheme，補上 https:
        if orig.startswith("//"):
            return "https:" + orig
        if not orig.lower().startswith(("http://", "https://")):
            return "https://" + orig
        return orig
    return url


def get_registrable_domain(url_or_domain: str) -> str:
    """
    取出 registrable domain（eTLD+1）。

    例：
        https://cdn.example.com/app.js                  -> example.com
        https://www.google-analytics.com/analytics.js   -> google-analytics.com
        fonts.gstatic.com                               -> gstatic.com

    無法解析（空字串、相對路徑、IP...）時回傳空字串。
    """
    if not url_or_domain or not str(url_or_domain).strip():
        return ""
    text = unwrap_wayback_url(str(url_or_domain).strip())
    ext = _EXTRACTOR(text)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}"
    return ""


def normalize_url(base_url: str, resource_url: str) -> str:
    """
    把 HTML 中的資源網址正規化成完整 URL。

    規則：
    - 空值 / data: / javascript: 等非資源網址 -> 回傳空字串
    - //cdn.example.com/app.js（protocol-relative）-> 補上 https:
    - /main.js 或 img/logo.png（相對路徑）-> 用 base_url 補成完整網址
    - 已是完整網址 -> 原樣回傳（若被 Wayback 改寫則先還原）
    """
    if not resource_url or not str(resource_url).strip():
        return ""
    url = str(resource_url).strip()

    lower = url.lower()
    if any(lower.startswith(s) for s in _IGNORED_SCHEMES):
        return ""

    url = unwrap_wayback_url(url)

    if url.startswith("//"):
        return "https:" + url

    parsed = urlparse(url)
    if parsed.scheme in ("http", "https"):
        return url

    # 相對路徑：以 base_url 為基準組成完整網址
    if base_url:
        return urljoin(base_url, url)
    return url


def is_third_party(site_domain: str, resource_url: str) -> bool:
    """
    判斷 resource_url 對 site_domain 而言是否為「第三方」。

    規則：
    - 兩者的 registrable domain 不同 -> True（第三方）
    - 相同 -> False（第一方，例如 example.com 與 cdn.example.com）
    - resource_url 沒有有效網域（相對路徑等）-> False（視為第一方資源）
    """
    resource_domain = get_registrable_domain(resource_url)
    if not resource_domain:
        return False
    site_reg = get_registrable_domain(site_domain)
    if not site_reg:
        return False
    return resource_domain != site_reg


def get_host(url: str) -> str:
    """取出完整主機名（含子網域），例如 https://cdn.example.com/a.js -> cdn.example.com。"""
    if not url:
        return ""
    parsed = urlparse(unwrap_wayback_url(str(url).strip()))
    return parsed.netloc.lower()
