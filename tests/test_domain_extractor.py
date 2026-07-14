"""
tests/test_domain_extractor.py
==============================
測試網域解析與第三方判斷邏輯。
"""

from parser.domain_extractor import (
    get_registrable_domain,
    is_third_party,
    normalize_url,
    unwrap_wayback_url,
)


class TestGetRegistrableDomain:
    def test_subdomain_stripped(self):
        # cdn 子網域應被去掉，留下主網域
        assert get_registrable_domain("https://cdn.example.com/app.js") == "example.com"

    def test_www_stripped(self):
        assert (
            get_registrable_domain("https://www.google-analytics.com/analytics.js")
            == "google-analytics.com"
        )

    def test_bare_hostname(self):
        # 沒有 scheme 的裸主機名也要能解析
        assert get_registrable_domain("fonts.gstatic.com") == "gstatic.com"

    def test_compound_tld(self):
        # 複合頂級域（.co.uk）要正確切分
        assert get_registrable_domain("https://shop.amazon.co.uk/item") == "amazon.co.uk"

    def test_empty_returns_empty(self):
        assert get_registrable_domain("") == ""
        assert get_registrable_domain(None) == ""

    def test_relative_path_returns_empty(self):
        # 相對路徑沒有網域
        assert get_registrable_domain("/static/main.js") == ""


class TestNormalizeUrl:
    BASE = "https://example.com/"

    def test_absolute_url_unchanged(self):
        url = "https://cdn.other.com/lib.js"
        assert normalize_url(self.BASE, url) == url

    def test_protocol_relative_gets_https(self):
        assert (
            normalize_url(self.BASE, "//cdn.example.com/app.js")
            == "https://cdn.example.com/app.js"
        )

    def test_relative_path_joined_with_base(self):
        assert normalize_url(self.BASE, "/main.js") == "https://example.com/main.js"

    def test_empty_returns_empty(self):
        assert normalize_url(self.BASE, "") == ""
        assert normalize_url(self.BASE, None) == ""

    def test_data_uri_ignored(self):
        assert normalize_url(self.BASE, "data:image/png;base64,AAAA") == ""

    def test_javascript_ignored(self):
        assert normalize_url(self.BASE, "javascript:void(0)") == ""


class TestUnwrapWaybackUrl:
    def test_rewritten_url_unwrapped(self):
        wrapped = "https://web.archive.org/web/20220715120000js_/https://cdn.example.com/a.js"
        assert unwrap_wayback_url(wrapped) == "https://cdn.example.com/a.js"

    def test_normal_url_untouched(self):
        url = "https://cdn.example.com/a.js"
        assert unwrap_wayback_url(url) == url


class TestIsThirdParty:
    def test_same_registrable_domain_is_first_party(self):
        # cdn.example.com 與 example.com 是同一方
        assert is_third_party("example.com", "https://cdn.example.com/app.js") is False

    def test_different_domain_is_third_party(self):
        assert (
            is_third_party("example.com", "https://www.google-analytics.com/analytics.js")
            is True
        )

    def test_relative_path_is_first_party(self):
        # 沒有有效網域的資源（相對路徑）視為第一方
        assert is_third_party("example.com", "/static/main.js") is False

    def test_empty_url_is_first_party(self):
        assert is_third_party("example.com", "") is False
