"""
tests/test_tdi.py
=================
測試 TDI 計算：輸出欄位齊全、數值在 [0, 1]、零第三方網站補 0。
"""

import pandas as pd

from indicators.compute_tdi import TDI_COLUMNS, compute_tdi
from indicators.normalize import min_max_normalize


def make_resources() -> pd.DataFrame:
    """建立小型測試資料：兩個網站、兩個年份。"""
    rows = [
        # S1 / 2022：2 個第三方 script（2 個不同網域）+ 1 個第一方 script
        dict(site_id="S1", domain="a.com", year=2022, resource_type="script",
             registrable_domain="ga.com", is_third_party=1),
        dict(site_id="S1", domain="a.com", year=2022, resource_type="script",
             registrable_domain="cdn.net", is_third_party=1),
        dict(site_id="S1", domain="a.com", year=2022, resource_type="script",
             registrable_domain="a.com", is_third_party=0),
        # S1 / 2024：1 個第三方 script + 1 個第三方 link（同一網域）
        dict(site_id="S1", domain="a.com", year=2024, resource_type="script",
             registrable_domain="ga.com", is_third_party=1),
        dict(site_id="S1", domain="a.com", year=2024, resource_type="link",
             registrable_domain="ga.com", is_third_party=1),
        # S2 / 2022：完全沒有第三方資源
        dict(site_id="S2", domain="b.com", year=2022, resource_type="script",
             registrable_domain="b.com", is_third_party=0),
    ]
    return pd.DataFrame(rows)


def test_output_columns():
    """輸出欄位必須完整。"""
    result = compute_tdi(make_resources())
    assert list(result.columns) == TDI_COLUMNS


def test_tdi_between_0_and_1():
    """TDI 與正規化欄位都必須落在 [0, 1]。"""
    result = compute_tdi(make_resources())
    for col in ["script_norm", "domain_norm", "tdi"]:
        assert (result[col] >= 0).all(), f"{col} 有負值"
        assert (result[col] <= 1).all(), f"{col} 超過 1"


def test_counts_correct():
    """第三方計數邏輯要正確。"""
    result = compute_tdi(make_resources()).set_index(["site_id", "year"])

    # S1/2022：2 個第三方 script、2 個第三方網域、共 2 筆第三方資源
    row = result.loc[("S1", 2022)]
    assert row["third_party_script_count"] == 2
    assert row["third_party_domain_count"] == 2
    assert row["third_party_resource_count"] == 2

    # S1/2024：1 個第三方 script、1 個網域、共 2 筆資源（script + link）
    row = result.loc[("S1", 2024)]
    assert row["third_party_script_count"] == 1
    assert row["third_party_domain_count"] == 1
    assert row["third_party_resource_count"] == 2


def test_zero_third_party_site_included():
    """完全沒有第三方資源的網站（S2）也要出現在結果中，且 TDI = 0。"""
    result = compute_tdi(make_resources()).set_index(["site_id", "year"])
    row = result.loc[("S2", 2022)]
    assert row["third_party_script_count"] == 0
    assert row["tdi"] == 0


def test_metadata_fills_missing_combinations():
    """metadata 中下載成功、但 resources 沒出現的組合，應補 0。"""
    metadata = pd.DataFrame([
        dict(site_id="S1", domain="a.com", target_year=2022, downloaded=1),
        dict(site_id="S1", domain="a.com", target_year=2024, downloaded=1),
        dict(site_id="S2", domain="b.com", target_year=2022, downloaded=1),
        dict(site_id="S3", domain="c.com", target_year=2022, downloaded=1),  # 不在 resources 裡
        dict(site_id="S3", domain="c.com", target_year=2024, downloaded=0),  # 失敗的不補
    ])
    result = compute_tdi(make_resources(), metadata)

    # S3/2022 下載成功但沒有任何資源 -> 應補 0
    s3 = result[(result["site_id"] == "S3") & (result["year"] == 2022)]
    assert len(s3) == 1
    assert s3.iloc[0]["tdi"] == 0

    # S3/2024 下載失敗 -> 不應出現
    assert len(result[(result["site_id"] == "S3") & (result["year"] == 2024)]) == 0


def test_empty_input_returns_empty_frame():
    """空輸入不能報錯，應回傳有欄位的空 DataFrame。"""
    result = compute_tdi(pd.DataFrame(columns=[
        "site_id", "domain", "year", "resource_type", "registrable_domain", "is_third_party",
    ]))
    assert list(result.columns) == TDI_COLUMNS
    assert len(result) == 0


def test_min_max_normalize_constant_series_is_zero():
    """所有值相同時（max == min），正規化結果應為全 0。"""
    s = pd.Series([5, 5, 5])
    assert (min_max_normalize(s) == 0).all()


def test_min_max_normalize_range():
    """一般情況：最小值變 0、最大值變 1。"""
    s = pd.Series([0, 5, 10])
    norm = min_max_normalize(s)
    assert norm.iloc[0] == 0.0
    assert norm.iloc[1] == 0.5
    assert norm.iloc[2] == 1.0
