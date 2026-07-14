# 每週進度紀錄（Weekly Progress）

> 每週固定記錄：完成了什麼、遇到什麼問題、下週計畫。口試與 meeting 前整理用。

---

## Week of 2026-07-13

### 完成事項
- 建立 Phase 1 研究專案架構（config / crawler / parser / indicators / analysis / scripts / tests / docs）。
- 完成 Tranco 分層抽樣程式（pilot_30 / pilot_100 / sample_full，固定 seed 可重現）。
- 完成 Wayback CDX 查詢與 HTML 下載器（timeout / retry / sleep / 錯誤記錄）。
- 完成 HTML 靜態解析與第三方偵測（registrable domain 比較法）。
- 完成 TDI 第一版計算與 5 張圖表。
- 建立 pytest 測試（domain extraction、third-party detection、TDI 計算）。

### 問題與待辦
- [ ] 下載 Tranco Top 1M 名單放入 `dataset/raw/tranco/tranco_top_1m.csv`（記下名單 ID）
- [ ] 跑 pilot_30 完整管線，檢查缺漏率
- [ ] 檢視 static_resources.csv 抽查 5 個網站，人工驗證第三方判斷

### 下週計畫
- 完成 pilot_30 執行與 pilot report 填寫

---

<!-- 之後每週往下加一節 -->
