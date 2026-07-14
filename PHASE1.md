# Website Governance Longitudinal Study

網站治理與第三方資源依賴的縱貫性量化研究 — **Phase 1：研究基礎建設與資料管線**

---

## 📌 專案狀態（2026-07-14 更新）：Phase 1 已完成 ✅

| 項目 | 狀態 |
|------|------|
| 研究環境（.venv + requirements） | ✅ 已建置 |
| 單元測試（pytest，31 個） | ✅ 全部通過 |
| Tranco Top 1M 名單 | ✅ `dataset/raw/tranco/tranco_top_1m.csv`（1,000,000 筆，名單 ID `74JZX`，已填入 pilot report） |
| 正式分層抽樣（pilot_30 / pilot_100 / sample_full） | ✅ 已完成（seed=42） |
| pilot_30 完整管線 | ✅ 90 任務，成功 56（62%），TDI 趨勢 0.200 → 0.242 → 0.295 |
| pilot_100 完整管線 | ✅ 300 任務，成功 166（55%），TDI 趨勢 0.102 → 0.121 → 0.125 |
| 第三方偵測抽查 | ✅ Top 第三方網域合理（GTM、Google APIs、AWS、CloudFront、jsDelivr…） |
| Phase 1 成功標準六個檔案 | ✅ 全部到位（目前輸出為 pilot_100 版本） |

### 初步結果摘要（pilot_100，2026-07-14 執行）

- 快照下載成功率 55%（166/300）；失敗幾乎都是 `missing_snapshot`（131），僅 3 個 `invalid_html`，無 timeout 最終失敗。
- 解析出 10,845 筆資源，其中第三方 4,452 筆（41%）。
- **45 個網站擁有完整三年（2022/2024/2026）面板資料**——縱貫分析的核心樣本。
- 平均 TDI 逐年上升（0.102 → 0.121 → 0.125），方向與「第三方依賴加深」假設一致；pilot 樣本僅供管線驗證，不可推論母體。
- 注意：TDI 的 min-max 正規化以「該批資料」為基準，pilot_30 與 pilot_100 的 TDI 絕對值**不可互相比較**，只看各自批內的跨年趨勢。

### ⚠️ Pilot 階段的重要發現

各 Tier 快照成功率：Tier1 僅 **40%**（12/30），反而低於 Tier2/Tier3 的 57%。原因：**Tranco 前 1000 名包含大量基礎設施網域**（`akadns.net`、`fastly.net`、`googleapis.com` 等 CDN/DNS 網域），它們因被大量引用而排名高，但沒有真正的「首頁」可供 Wayback 存檔，嚴格說也不屬於「網站治理」的研究對象。**Phase 2 開始前需決定處理方式**：用 `included=0` 排除並在 `note` 註明，或在 `category` 標註後分開分析。

### 下一步（Phase 2）

檢視 `figures/` 與 `docs/phase1_pilot_report.md` 後，依 [第 11 節](#11-下一階段phase-2) 依序加入 tracker 分類、TMI、SCI 與動態校準。

---

## 1. 專案簡介

現代網站大量依賴第三方資源：分析工具（Google Analytics）、廣告、CDN、字型、社群外掛……。這種依賴帶來效率，也帶來**技術耦合、隱私外洩與供應鏈攻擊面**。

本研究是一個**縱貫性（longitudinal）量化研究**：追蹤同一批網站在 **2022、2024、2026** 三個時間點的歷史快照，量測它們對第三方資源的依賴程度是否改變，最終目標是建立**網站治理策略矩陣**。

本 repository 目前是 **Phase 1**：把研究從 Proposal 變成「可以實際跑通的資料管線」。

## 2. 第一階段目標

Phase 1 **只做**以下事情（刻意不做完整研究）：

| 做 | 不做（留給 Phase 2+） |
|----|----------------------|
| Tranco List 分層抽樣（pilot_30 / pilot_100 / sample_full） | 一開始就跑 1000 個網站 |
| Wayback Machine 歷史快照下載（2022 / 2024 / 2026） | Headless Chrome 動態量測 |
| HTML 靜態解析 | JavaScript 動態注入資源的偵測 |
| 第三方資源清單（third-party detection） | tracker 分類（TMI） |
| TDI 第三方依賴度指標**第一版** | 供應商集中度（SCI） |
| 初步圖表與 pilot report | 完整統計檢定 |

> **Playwright 說明**：requirements.txt 刻意不含 playwright。Headless Chrome 動態量測是 Phase 2 的「動態校準」才需要，到時再安裝。

## 3. 研究資料管線

Phase 1 的核心就是讓這條管線穩定跑通：

```
Tranco Top 1M（你手動下載）
      │
      ▼  crawler/tranco_sampler.py（分層隨機抽樣，seed=42 可重現）
pilot_30.csv / pilot_100.csv / sample_full.csv
      │
      ▼  crawler/wayback_downloader.py（CDX API 查詢 + 下載）
snapshot_metadata.csv ＋ dataset/raw/wayback/{year}/{site_id}.html
      │
      ▼  parser/run_static_parser.py（BeautifulSoup 靜態解析）
static_resources.csv（每個外部資源一列，含 is_third_party 判斷）
      │
      ▼  indicators/compute_tdi.py
tdi_scores.csv（每個 網站×年份 一個 TDI 分數）
      │
      ▼  analysis/generate_phase1_figures.py
figures/*.png ＋ docs/phase1_pilot_report.md
```

## 4. 專案架構

```
website-governance-longitudinal-study/
├── config/            # 所有設定集中在這裡
│   ├── paths.py       #   路徑管理（全部 pathlib，無硬編絕對路徑）
│   ├── constants.py   #   研究常數（年份、Tier、抽樣數、請求節流）
│   └── settings.py    #   執行設定（隨機種子、API 端點、User-Agent）
├── crawler/           # 資料收集
│   ├── tranco_sampler.py      # Tranco 分層抽樣
│   ├── wayback_cdx.py         # CDX API 查詢 + 最佳快照選擇
│   ├── wayback_downloader.py  # HTML 快照下載器
│   └── utils.py               # 日誌、日期、禮貌性 sleep
├── parser/            # HTML 解析
│   ├── domain_extractor.py    # registrable domain / 第三方判斷
│   ├── html_parser.py         # 單檔 HTML 靜態解析
│   └── run_static_parser.py   # 批次解析主程式
├── indicators/        # 指標計算
│   ├── normalize.py           # min-max 正規化
│   └── compute_tdi.py         # TDI 第一版
├── analysis/          # 分析與圖表
│   ├── generate_phase1_figures.py
│   └── 01_phase1_pilot_analysis.ipynb   # 互動式檢視結果的 notebook
├── scripts/           # 執行腳本
│   ├── init_dirs.py           # 初始化資料夾
│   └── phase1_run_pipeline.py # 一鍵跑完整條管線
├── dataset/
│   ├── raw/           # 原始資料（不進 Git！見 .gitignore）
│   │   ├── tranco/    #   Tranco CSV 放這裡
│   │   └── wayback/   #   下載的 HTML 快照（{year}/{site_id}.html）
│   ├── processed/     # 處理後資料（體積小，進 Git）
│   │   ├── samples/     # 抽樣結果
│   │   ├── resources/   # snapshot_metadata、static_resources
│   │   └── indicators/  # tdi_scores
│   └── external/      # 外部補充資料（Phase 2 的 tracker 清單等）
├── figures/           # 圖表輸出
├── logs/              # 執行紀錄（不進 Git）
├── docs/              # 研究文件（資料字典、方法論、pilot report）
├── paper/             # 論文草稿
└── tests/             # pytest 單元測試
```

## 5. 安裝方式（Windows PowerShell）

在專案根目錄開 PowerShell（VS Code 內建終端機即可）：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

之後每次開新終端機，記得先 `.venv\Scripts\activate` 啟動虛擬環境。

驗證安裝：

```powershell
python -m scripts.init_dirs
pytest
```

兩個都成功就代表環境沒問題。

## 6. 如何準備 Tranco List

> ✅ 本專案已完成此步驟（2026-07-14）。以下說明保留給重新下載名單時參考。

1. 到 <https://tranco-list.eu/> 下載最新的 **Full list**（CSV，約 1,000,000 列，21~25 MB）。
2. 下載的檔案通常叫 `top-1m.csv`，請**改名**後放到：

   ```
   dataset/raw/tranco/tranco_top_1m.csv
   ```

   也可以在 PowerShell 中執行：

   ```powershell
   Rename-Item dataset\raw\tranco\top-1m.csv tranco_top_1m.csv
   ```

3. 格式（無標題列或有標題列都支援）：

   ```
   rank,domain
   1,google.com
   2,youtube.com
   ```

> **重要**：請記下你下載的名單 ID（網頁上會顯示，例如 `Z3XVN`），寫進 `docs/phase1_pilot_report.md` 的 Sample 一節——這是研究可重現性的關鍵。
>
> **Demo 模式**：還沒有 Tranco CSV、只想測試程式流程時，可執行 `python -m crawler.tranco_sampler --demo`。它會用隨機假網域產生樣本檔，**demo 產生的資料絕對不能當作研究結果**，拿到真實名單後請重跑正式抽樣。

## 7. 如何執行第一階段

### 方法 A：一步一步執行（了解每個步驟在做什麼）

```powershell
# 1. 建立所有資料夾
python -m scripts.init_dirs

# 2. 分層抽樣（需要先放好 Tranco CSV）
python -m crawler.tranco_sampler --input dataset/raw/tranco/tranco_top_1m.csv

# 3. 下載 Wayback 快照（30 網站 × 3 年 = 90 個任務，約 10~15 分鐘）
python -m crawler.wayback_downloader --sample dataset/processed/samples/pilot_30.csv

# 4. 靜態解析 HTML
python -m parser.run_static_parser --metadata dataset/processed/resources/snapshot_metadata.csv

# 5. 計算 TDI
python -m indicators.compute_tdi --resources dataset/processed/resources/static_resources.csv --metadata dataset/processed/resources/snapshot_metadata.csv

# 6. 產生圖表
python -m analysis.generate_phase1_figures
```

### 方法 B：一鍵執行

```powershell
python -m scripts.phase1_run_pipeline --sample dataset/processed/samples/pilot_30.csv
```

會依序跑步驟 3~6，並自動把統計數字填進 `docs/phase1_pilot_report.md`，最後列出所有產出檔案。

> 所有指令都要**在專案根目錄**、**啟動 .venv 之後**執行。

## 8. 主要輸出檔案

| 檔案 | 內容 |
|------|------|
| `dataset/processed/samples/pilot_30.csv` | 30 個抽樣網站（site_id、domain、rank、tier） |
| `dataset/processed/resources/snapshot_metadata.csv` | 每個 網站×年份 的快照下載紀錄（含成功/失敗與原因） |
| `dataset/processed/resources/static_resources.csv` | HTML 中解析出的所有外部資源（含第三方判斷） |
| `dataset/processed/indicators/tdi_scores.csv` | 每個 網站×年份 的 TDI 分數 |
| `figures/*.png` | 5 張圖：Tier 分布、script 數、網域數、TDI 分布、TDI 趨勢 |
| `docs/phase1_pilot_report.md` | Pilot 報告（管線自動填入統計） |

每個 CSV 的完整欄位說明見 [docs/data_dictionary.md](docs/data_dictionary.md)。

## 9. TDI 指標解釋

**TDI（Third-party Dependency Index，第三方依賴度指標）第一版：**

```
TDI = 0.5 × script_norm + 0.5 × domain_norm
```

- `script_norm`：第三方 `<script src>` 數量的 min-max 正規化值（0~1）
- `domain_norm`：第三方網域（registrable domain）個數的 min-max 正規化值（0~1）

**直觀解讀**：TDI 越高，代表網站越依賴第三方腳本與外部網域——可能表示**技術耦合更深、攻擊面更廣、治理負擔更高**。

- script 數衡量「依賴的深度」：每個第三方 script 都能在你的頁面執行任意程式碼。
- 網域數衡量「依賴的廣度」：依賴多少個不同的外部供應商。

正規化是對整批資料（所有網站所有年份合併）計算的，所以同一批資料內、不同年份的 TDI 可以直接比較；但**不同批次執行之間的 TDI 不可直接比較**（正規化基準不同）。

「第三方」的判斷規則：比較網站與資源的 registrable domain（eTLD+1）。`cdn.example.com` 對 `example.com` 是**第一方**；`google-analytics.com` 對 `example.com` 是**第三方**。詳見 [docs/methodology_notes.md](docs/methodology_notes.md) 第 7 節。

## 10. 目前限制

1. **只做靜態解析**：JavaScript 動態注入的第三方資源（例如透過 GTM 載入的追蹤器）抓不到，TDI 是低估值。
2. **Wayback HTML 可能不完整**：部分快照可能缺漏資源或存到錯誤頁。
3. **2026 快照可能尚未完整**：2026-08-31 之前執行時，查詢期間會自動截到今天，部分網站標記 `missing_snapshot` 是正常現象。
4. **只解析首頁**，內頁不在範圍。
5. **尚未加入 TMI 與 SCI**：目前只有依賴「量」，還沒有追蹤強度與供應商集中度。
6. **尚未加入 Headless Chrome 動態校準**（Phase 2 才做，屆時才需安裝 Playwright）。
7. 第三方判定未做公司實體對應（同公司不同網域會被算成第三方）。

## 11. 下一階段（Phase 2+）

1. **Tracker classification**：用 EasyPrivacy / Tracker Radar 清單為第三方資源分類。
2. **TMI**（Tracking & Monetization Index）：追蹤與變現強度指標。
3. **Supplier mapping**：網域 → 公司實體對應。
4. **SCI**（Supplier Concentration Index）：供應商集中度（HHI 型指標）。
5. **Headless Chrome 動態量測**：對當前網站量測動態載入資源，建立靜態→動態校準係數。
6. **治理策略矩陣**：以 TDI × SCI / TMI 將網站定位到治理策略象限，完成研究核心產出。

---

## 附：常見問題

**Q：在 VS Code 打開 Tranco CSV 時跳出「exceeds the csv.maxFileSizeMB limit (10 MB)」警告？**
這不是錯誤。VS Code 只是提醒「這個檔案很大，用 CSV 檢視器開會拖慢編輯器」。按 **Cancel** 關掉即可——Tranco CSV 不需要人工打開，程式會自己讀取。真的想看內容時按 Continue This Time，或改用終端機：`Get-Content dataset\raw\tranco\tranco_top_1m.csv -TotalCount 10`。

**Q：跑到一半網路斷了怎麼辦？**
重新執行 downloader 即可，它會整批重跑（pilot_30 規模小，重跑成本低）。每個網站的錯誤都只會記錄在 `error_message`，不會中斷整批。

**Q：為什麼有些網站是 `missing_snapshot`？**
Wayback Machine 沒有收錄該網站在該期間的快照，長尾網站（Tier3）與 2026 年特別常見。這本身就是研究資料（快照可用性），會呈現在 pilot report。

**Q：`tests/` 在測什麼？**
`pytest` 會驗證三個核心邏輯：網域解析（`cdn.example.com` → `example.com`）、第三方判斷（子網域=第一方、外部網域=第三方）、TDI 計算（欄位齊全、數值在 0~1、零第三方網站補 0）。改動程式後請先跑 `pytest` 再跑管線。
