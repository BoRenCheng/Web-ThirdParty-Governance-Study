# 網站第三方資源依賴之縱貫性量化實證研究：治理策略矩陣與去風險化演進
Longitudinal quantitative study on web third-party resource dependency and de-risking evolution (2022-2026).

![Field](https://img.shields.io/badge/Field-Web_Governance-blue.svg)
![Methodology](https://img.shields.io/badge/Method-Longitudinal_Study-orange.svg)
![Status](https://img.shields.io/badge/Research-2022--2026-green.svg)

本研究聚焦於網站前端「第三方資源依賴」所引發的治理風險。隨著 Web 開發轉向模組化，治理核心已由伺服器端擴張至「瀏覽器端供應鏈韌性」。本專案實作了雙軌量測機制，並分析 2022 至 2026 年的縱貫性數據，驗證企業在數位資產管理上的「去風險化」演變趨勢。

## 研究摘要 

本計畫利用 **Tranco List** 抽樣並透過 **Wayback Machine** 重建歷史數據，導入結合靜態解析與 **Headless Chrome** 動態模擬的校準機制。我們開發了三項核心量化指標來建構「網站治理策略矩陣」，旨在揭示不同產業的治理路徑差異，為數位供應鏈優化提供實證依據。

---

## 目前實作進度：Phase 1 已完成（2026-07-14）

研究已從 Proposal 進入可實作階段，第一階段資料管線（抽樣 → 歷史快照 → 靜態解析 → TDI → 圖表）已完整跑通：

- ✅ **Tranco 分層抽樣**：名單 ID [`74JZX`](https://tranco-list.eu/list/74JZX/1000000)，Tier1/2/3 分層、固定 seed=42 可重現，pilot_30 ⊆ pilot_100 ⊆ sample_full（1000 站）
- ✅ **Wayback Machine 歷史重建**：2022 / 2024 / 2026 三時點，pilot_100 共 300 個快照任務，成功 166（55%）
- ✅ **靜態解析與第三方偵測**：10,845 筆資源，其中第三方 4,452 筆；45 個網站具完整三年面板資料
- ✅ **TDI 第一版**：平均 TDI 逐年上升（0.102 → 0.121 → 0.125）
- ✅ 31 個單元測試全數通過；5 張初步圖表（見 [`figures/`](figures/)）
- 🔜 **Phase 2**：TMI（追蹤強度）、SCI（供應商集中度）、Headless Chrome 動態校準

詳細文件：

| 文件 | 內容 |
|------|------|
| [PHASE1.md](PHASE1.md) | Phase 1 完整說明：安裝、執行方式、專案架構、TDI 解釋 |
| [docs/phase1_pilot_report.md](docs/phase1_pilot_report.md) | Pilot 執行報告（含自動統計與問題觀察） |
| [docs/methodology_notes.md](docs/methodology_notes.md) | 方法論設計理由 |
| [docs/data_dictionary.md](docs/data_dictionary.md) | 所有資料表的欄位定義 |

---

## 核心量化指標 

本研究定義了三項關鍵維度來衡量網站的第三方風險：

1. **TDI (Third-party Dependency Index, 第三方依賴度)**：衡量網站對外部資源的引用比例與依賴深度。
2. **TMI (Tracking Messaging Intensity, 追蹤強度)**：評估第三方腳本中具備追蹤與指紋識別特徵的行為強度。
3. **SCI (Supplier Concentration Index, 供應商集中度)**：分析第三方資源供應商的市場集中情況，評估單一供應商故障時的連鎖風險。

---

## 技術實作 

### 1. 雙軌量測機制 
* **靜態解析 (Static Analysis)**：解析 HTML/JavaScript 原始碼中的資源引用路徑。
* **動態模擬 (Dynamic Simulation)**：運用 **Headless Chrome** 模擬真實瀏覽行為，捕捉動態加載的腳本與 API 調用行為，有效減少靜態分析的遺漏誤差。

### 2. 數據重建與追蹤
* 透過 **Wayback Machine API** 自動化重建指定網站在 2022 至 2026 年間的時點數據，確保研究具備縱貫性 (Longitudinal) 的分析深度。

---

## 預計研究產出：治理策略矩陣

我們將網站歸納至四個象限，用以識別其治理成熟度：
* **高依賴-高追蹤 (風險區)**
* **低依賴-低追蹤 (韌性區)**
* **高依賴-低追蹤 (功能導向)**
* **低依賴-高追蹤 (隱私敏感)**

研究結果證實，隨著監管政策與資安意識提升，頂尖網站正呈現出明顯的 **「去風險化 」** 趨勢，即減少不必要的第三方依賴並提升供應商多樣性。

* **研究企劃書**: [網站第三方資源依賴的縱貫性量化實證研究_治理策略矩陣與去風險化演進](網站第三方資源依賴的縱貫性量化實證研究_治理策略矩陣與去風險化演進.pdf)

---
## 授權
Copyright (c) 2026 Bo-Ren Cheng(BoRenCheng)

本專案採用 MIT License 授權。

