"""
analysis/generate_phase1_figures.py
===================================
Phase 1 圖表產生器（只用 matplotlib，不用 seaborn；每張圖獨立輸出）。

輸出到 figures/：
    1. sample_tier_distribution.png          -- 樣本 Tier 分布
    2. third_party_script_count_by_year.png  -- 各年份第三方 script 數分布（箱型圖）
    3. third_party_domain_count_by_year.png  -- 各年份第三方網域數分布（箱型圖）
    4. tdi_distribution_by_year.png          -- 各年份 TDI 分布（箱型圖）
    5. tdi_mean_trend.png                    -- TDI 平均值跨年趨勢（折線圖）

設計原則：
    - 年份是「有序」變數，用同一藍色系由淺到深表示（2022 淺 -> 2026 深），
      不用彩虹色。
    - 格線、座標軸用低調灰色，讓資料本身最突出。
    - 資料為空時印出 warning，不報錯、不中斷。

執行方式：
    python -m analysis.generate_phase1_figures
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 不開視窗，直接存檔（在無螢幕環境也能跑）
import matplotlib.pyplot as plt
import pandas as pd

from config.paths import (
    FIGURE_DIR,
    PILOT_30_CSV,
    STATIC_RESOURCES_CSV,
    TDI_SCORES_CSV,
)
from crawler.utils import get_logger

logger = get_logger("generate_phase1_figures")

# ---- 視覺樣式（依 dataviz 設計規範）----
SURFACE = "#fcfcfb"       # 圖表底色
INK = "#0b0b0b"           # 主要文字
MUTED = "#898781"         # 軸標籤
GRID = "#e1e0d9"          # 格線（極淡）
BASELINE = "#c3c2b7"      # 座標軸線
# 年份為有序變數：同一藍色系由淺到深（2022 -> 2024 -> 2026）
YEAR_COLORS = {2022: "#86b6ef", 2024: "#3987e5", 2026: "#1c5cab"}
PRIMARY_BLUE = "#2a78d6"  # 單一系列用色


def _style_axes(ax):
    """套用統一的軸線樣式：去掉上/右邊框、淡格線、灰色刻度。"""
    ax.set_facecolor(SURFACE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(BASELINE)
    ax.spines["bottom"].set_color(BASELINE)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)  # 格線畫在資料下面


def _new_fig():
    """建立單張圖（不用 subplot 拼圖）。"""
    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    _style_axes(ax)
    return fig, ax


def _save(fig, filename: str):
    """存檔到 figures/ 並關閉圖表釋放記憶體。"""
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    out = FIGURE_DIR / filename
    fig.tight_layout()
    fig.savefig(out, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    logger.info("已輸出 %s", out)


def _boxplot_by_year(df: pd.DataFrame, value_col: str, title: str,
                     ylabel: str, filename: str):
    """通用函式：畫「各年份 value_col 分布」的箱型圖。"""
    if df is None or df.empty or value_col not in df.columns:
        logger.warning("資料為空，略過圖表：%s", filename)
        return

    years = sorted(df["year"].dropna().unique())
    if not years:
        logger.warning("沒有年份資料，略過圖表：%s", filename)
        return

    data = [df.loc[df["year"] == y, value_col].dropna() for y in years]
    fig, ax = _new_fig()
    boxes = ax.boxplot(
        data,
        tick_labels=[str(int(y)) for y in years],
        patch_artist=True,          # 允許填色
        widths=0.5,
        medianprops={"color": INK, "linewidth": 1.5},
        whiskerprops={"color": BASELINE},
        capprops={"color": BASELINE},
        flierprops={"marker": "o", "markersize": 4,
                    "markerfacecolor": MUTED, "markeredgecolor": "none"},
    )
    for patch, y in zip(boxes["boxes"], years):
        patch.set_facecolor(YEAR_COLORS.get(int(y), PRIMARY_BLUE))
        patch.set_edgecolor("none")
        patch.set_alpha(0.85)

    ax.set_title(title, color=INK, fontsize=13, pad=12)
    ax.set_xlabel("Year", color=MUTED, fontsize=11)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=11)
    _save(fig, filename)


def fig_sample_tier_distribution(sample: pd.DataFrame):
    """圖 1：樣本的 Tier 分布長條圖。"""
    if sample is None or sample.empty:
        logger.warning("樣本為空，略過 sample_tier_distribution.png")
        return

    counts = sample["tier"].value_counts().sort_index()
    fig, ax = _new_fig()
    bars = ax.bar(counts.index, counts.values, color=PRIMARY_BLUE, width=0.55)
    # 每根長條上方直接標數值（讓讀者不用對格線）
    for bar, v in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, v, str(int(v)),
                ha="center", va="bottom", color=INK, fontsize=11)

    ax.set_title("Sample Tier Distribution", color=INK, fontsize=13, pad=12)
    ax.set_xlabel("Tier", color=MUTED, fontsize=11)
    ax.set_ylabel("Number of Sites", color=MUTED, fontsize=11)
    _save(fig, "sample_tier_distribution.png")


def fig_tdi_mean_trend(tdi: pd.DataFrame):
    """圖 5：TDI 平均值跨年趨勢折線圖。"""
    if tdi is None or tdi.empty:
        logger.warning("TDI 為空，略過 tdi_mean_trend.png")
        return

    trend = tdi.groupby("year")["tdi"].mean().sort_index()
    fig, ax = _new_fig()
    ax.plot(trend.index, trend.values, color=PRIMARY_BLUE, linewidth=2,
            marker="o", markersize=8, markerfacecolor=PRIMARY_BLUE,
            markeredgecolor=SURFACE, markeredgewidth=2)
    # 直接標出每個點的數值
    for x, y in trend.items():
        ax.annotate(f"{y:.3f}", (x, y), textcoords="offset points",
                    xytext=(0, 10), ha="center", color=INK, fontsize=10)

    ax.set_title("Mean TDI Trend Across Years", color=INK, fontsize=13, pad=12)
    ax.set_xlabel("Year", color=MUTED, fontsize=11)
    ax.set_ylabel("Mean TDI", color=MUTED, fontsize=11)
    ax.set_xticks(list(trend.index))
    ax.set_ylim(bottom=0)
    _save(fig, "tdi_mean_trend.png")


def run(sample_path=None, resources_path=None, tdi_path=None):
    """主流程：讀三份資料，各自畫圖；缺哪份就略過對應圖表並警告。"""

    def safe_read(path, name):
        path = Path(path)
        if not path.exists():
            logger.warning("找不到 %s（%s），對應圖表將略過。", name, path)
            return None
        df = pd.read_csv(path)
        if df.empty:
            logger.warning("%s 是空的（%s）。", name, path)
        return df

    sample = safe_read(sample_path or PILOT_30_CSV, "樣本檔")
    resources = safe_read(resources_path or STATIC_RESOURCES_CSV, "static_resources.csv")
    tdi = safe_read(tdi_path or TDI_SCORES_CSV, "tdi_scores.csv")

    # 圖 1：樣本 Tier 分布
    fig_sample_tier_distribution(sample)

    # 圖 2、3：第三方 script 數 / 網域數 各年分布
    # （用 tdi_scores 的彙總欄位畫，因為它已補齊「零第三方」的網站）
    _boxplot_by_year(
        tdi, "third_party_script_count",
        "Third-party Script Count by Year", "Third-party Script Count",
        "third_party_script_count_by_year.png",
    )
    _boxplot_by_year(
        tdi, "third_party_domain_count",
        "Third-party Domain Count by Year", "Third-party Domain Count",
        "third_party_domain_count_by_year.png",
    )

    # 圖 4：TDI 各年分布
    _boxplot_by_year(
        tdi, "tdi",
        "TDI Distribution by Year", "TDI",
        "tdi_distribution_by_year.png",
    )

    # 圖 5：TDI 平均趨勢
    fig_tdi_mean_trend(tdi)

    logger.info("圖表輸出完成（目錄：%s）", FIGURE_DIR)


def main():
    parser = argparse.ArgumentParser(description="產生 Phase 1 圖表")
    parser.add_argument("--sample", default=None, help="樣本 CSV（預設 pilot_30.csv）")
    parser.add_argument("--resources", default=None, help="static_resources.csv 路徑")
    parser.add_argument("--tdi", default=None, help="tdi_scores.csv 路徑")
    args = parser.parse_args()
    run(sample_path=args.sample, resources_path=args.resources, tdi_path=args.tdi)


if __name__ == "__main__":
    main()
