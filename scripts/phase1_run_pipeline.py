"""
scripts/phase1_run_pipeline.py
==============================
Phase 1 一鍵執行腳本：串起整條資料管線。

流程：
    1. 確認資料夾存在（init_dirs）
    2. 檢查 sample 檔是否存在
    3. Wayback 下載（crawler.wayback_downloader）
    4. HTML 靜態解析（parser.run_static_parser）
    5. TDI 計算（indicators.compute_tdi）
    6. 產生圖表（analysis.generate_phase1_figures）
    7. 自動更新 docs/phase1_pilot_report.md 的統計數字
    8. 列出所有產出檔案位置

執行方式：
    python -m scripts.phase1_run_pipeline --sample dataset/processed/samples/pilot_30.csv
"""

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from config.paths import (
    DOCS_DIR,
    FIGURE_DIR,
    ROOT_DIR,
    SNAPSHOT_METADATA_CSV,
    STATIC_RESOURCES_CSV,
    TDI_SCORES_CSV,
    PILOT_30_CSV,
)


def run_step(step_name: str, module: str, extra_args: list) -> bool:
    """
    用「python -m 模組」的方式執行一個步驟。

    回傳 True/False 表示成功與否；失敗時印出清楚的中文錯誤說明，
    不只丟 traceback。
    """
    print(f"\n{'=' * 60}")
    print(f"步驟：{step_name}")
    print(f"指令：python -m {module} {' '.join(extra_args)}")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, "-m", module, *extra_args],
        cwd=ROOT_DIR,  # 一律在專案根目錄執行，路徑才會正確
    )
    if result.returncode != 0:
        print(f"\n[失敗] 步驟「{step_name}」執行失敗（exit code {result.returncode}）。")
        print(f"請單獨重跑此步驟找原因：python -m {module} {' '.join(extra_args)}")
        return False
    return True


def update_pilot_report(sample_path: Path) -> None:
    """
    把目前的執行結果統計自動寫進 docs/phase1_pilot_report.md。
    任何錯誤都不影響管線成功與否（報告只是輔助文件）。
    """
    try:
        import pandas as pd

        lines = [
            "<!-- 本區塊由 scripts/phase1_run_pipeline.py 自動產生 -->",
            f"- 報告更新日期：{date.today().isoformat()}",
            f"- 使用樣本：`{sample_path}`",
        ]

        if SNAPSHOT_METADATA_CSV.exists():
            meta = pd.read_csv(SNAPSHOT_METADATA_CSV)
            ok = int((meta["downloaded"] == 1).sum())
            lines.append(f"- 快照任務：{len(meta)} 個，下載成功 {ok} 個，缺漏/失敗 {len(meta) - ok} 個")
            errors = meta.loc[meta["downloaded"] != 1, "error_message"].value_counts()
            for msg, n in errors.items():
                lines.append(f"    - {msg}: {n}")

        if STATIC_RESOURCES_CSV.exists():
            res = pd.read_csv(STATIC_RESOURCES_CSV)
            n_third = int(res["is_third_party"].sum()) if len(res) else 0
            lines.append(f"- 解析出資源：{len(res)} 筆，其中第三方 {n_third} 筆")

        if TDI_SCORES_CSV.exists():
            tdi = pd.read_csv(TDI_SCORES_CSV)
            lines.append(f"- TDI 分數：{len(tdi)} 筆 site-year")
            if len(tdi):
                by_year = tdi.groupby("year")["tdi"].mean()
                for y, v in by_year.items():
                    lines.append(f"    - {int(y)} 年平均 TDI：{v:.4f}")

        report_path = DOCS_DIR / "phase1_pilot_report.md"
        if report_path.exists():
            content = report_path.read_text(encoding="utf-8")
            marker_start = "<!-- AUTO_RESULTS_START -->"
            marker_end = "<!-- AUTO_RESULTS_END -->"
            if marker_start in content and marker_end in content:
                before = content.split(marker_start)[0]
                after = content.split(marker_end)[1]
                new_content = (
                    before + marker_start + "\n" + "\n".join(lines) + "\n" + marker_end + after
                )
                report_path.write_text(new_content, encoding="utf-8")
                print(f"已更新報告統計：{report_path}")
    except Exception as exc:
        print(f"[警告] 更新 pilot report 失敗（不影響管線結果）：{exc}")


def main():
    parser = argparse.ArgumentParser(description="Phase 1 一鍵執行")
    parser.add_argument(
        "--sample",
        default=str(PILOT_30_CSV),
        help="樣本 CSV 路徑（預設 dataset/processed/samples/pilot_30.csv）",
    )
    args = parser.parse_args()
    sample_path = Path(args.sample)

    # ---- 步驟 1：確認資料夾存在 ----
    from scripts.init_dirs import run as init_dirs_run
    init_dirs_run()

    # ---- 步驟 2：檢查 sample 是否存在 ----
    if not sample_path.exists():
        print(f"\n[失敗] 找不到樣本檔：{sample_path}")
        print("請先執行抽樣：")
        print("  python -m crawler.tranco_sampler --input dataset/raw/tranco/tranco_top_1m.csv")
        sys.exit(1)

    # ---- 步驟 3~6：依序執行管線 ----
    steps = [
        ("Wayback 快照下載", "crawler.wayback_downloader", ["--sample", str(sample_path)]),
        ("HTML 靜態解析", "parser.run_static_parser", []),
        ("TDI 計算", "indicators.compute_tdi", []),
        ("產生圖表", "analysis.generate_phase1_figures", ["--sample", str(sample_path)]),
    ]
    for step_name, module, extra in steps:
        if not run_step(step_name, module, extra):
            sys.exit(1)

    # ---- 步驟 7：更新 pilot report ----
    update_pilot_report(sample_path)

    # ---- 步驟 8：列出產出 ----
    print("\n" + "=" * 60)
    print("Phase 1 管線執行完成！產出檔案：")
    print("=" * 60)
    outputs = [
        SNAPSHOT_METADATA_CSV,
        STATIC_RESOURCES_CSV,
        TDI_SCORES_CSV,
        DOCS_DIR / "phase1_pilot_report.md",
    ]
    for p in outputs:
        status = "OK " if p.exists() else "缺 "
        print(f"  [{status}] {p.relative_to(ROOT_DIR)}")
    if FIGURE_DIR.exists():
        for fig in sorted(FIGURE_DIR.glob("*.png")):
            print(f"  [OK ] {fig.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
