"""
indicators/normalize.py
=======================
指標正規化工具。
"""

import pandas as pd


def min_max_normalize(series: pd.Series) -> pd.Series:
    """
    Min-Max 正規化：把數值壓縮到 [0, 1] 區間。

    公式：(x - min) / (max - min)

    特殊情況：
    - 若 max == min（所有值一樣，分母為 0），回傳全部 0。
    - 若 series 為空，回傳空 series。
    """
    series = pd.to_numeric(series, errors="coerce").fillna(0)
    if series.empty:
        return series.astype(float)

    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series(0.0, index=series.index)
    return (series - min_val) / (max_val - min_val)
