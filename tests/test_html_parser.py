"""
tests/test_html_parser.py
=========================
測試 HTML 靜態解析器：能否正確抽出資源並判斷第三方。
"""

from parser.html_parser import parse_static_resources

# 測試用的小 HTML：包含第三方 script、第一方 script、第三方 CSS
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <script src="https://www.google-analytics.com/analytics.js"></script>
    <script src="/main.js"></script>
    <link href="https://fonts.googleapis.com/css?family=Noto" rel="stylesheet">
    <script>console.log("inline, no src, should be skipped");</script>
</head>
<body>
    <img src="//cdn.example.com/logo.png">
    <iframe src="https://www.youtube.com/embed/xyz"></iframe>
</body>
</html>
"""


def _write_html(tmp_path):
    """把測試 HTML 寫入暫存檔，回傳路徑。"""
    html_file = tmp_path / "S000001.html"
    html_file.write_text(SAMPLE_HTML, encoding="utf-8")
    return html_file


def test_extracts_all_resources(tmp_path):
    """應抓到 5 筆資源（2 script + 1 link + 1 img + 1 iframe），inline script 不算。"""
    records = parse_static_resources(_write_html(tmp_path), "S000001", "example.com", 2022)
    assert len(records) == 5
    types = sorted(r["resource_type"] for r in records)
    assert types == ["iframe", "image", "link", "script", "script"]


def test_third_party_detection(tmp_path):
    """第三方判斷：GA/fonts/youtube 是第三方；/main.js 與 cdn.example.com 是第一方。"""
    records = parse_static_resources(_write_html(tmp_path), "S000001", "example.com", 2022)
    by_url = {r["resource_url"]: r for r in records}

    # 第三方
    assert by_url["https://www.google-analytics.com/analytics.js"]["is_third_party"] == 1
    assert by_url["https://fonts.googleapis.com/css?family=Noto"]["is_third_party"] == 1
    assert by_url["https://www.youtube.com/embed/xyz"]["is_third_party"] == 1

    # 第一方：相對路徑補上網站網域
    assert by_url["https://example.com/main.js"]["is_third_party"] == 0
    # 第一方：cdn 子網域與主網域同一方（protocol-relative 補 https:）
    assert by_url["https://cdn.example.com/logo.png"]["is_third_party"] == 0


def test_registrable_domain_extracted(tmp_path):
    """registrable_domain 欄位應為 eTLD+1。"""
    records = parse_static_resources(_write_html(tmp_path), "S000001", "example.com", 2022)
    ga = next(r for r in records if "google-analytics" in r["resource_url"])
    assert ga["registrable_domain"] == "google-analytics.com"


def test_record_metadata_fields(tmp_path):
    """每筆 record 都要帶 site_id / domain / year。"""
    records = parse_static_resources(_write_html(tmp_path), "S000001", "example.com", 2022)
    for r in records:
        assert r["site_id"] == "S000001"
        assert r["domain"] == "example.com"
        assert r["year"] == 2022


def test_missing_file_returns_empty_list(tmp_path):
    """HTML 檔不存在時應回傳空 list，不能丟例外。"""
    records = parse_static_resources(tmp_path / "not_exist.html", "S000001", "example.com", 2022)
    assert records == []
