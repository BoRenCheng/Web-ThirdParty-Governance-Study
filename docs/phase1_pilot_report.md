# Phase 1 Pilot Report

## 1. Objective

本階段（Phase 1）的目標**不是**產出最終研究結果，而是驗證研究資料管線是否可行：

- 能否從 Tranco List 做出可重現的分層抽樣？
- 能否穩定地從 Wayback Machine 取得三個年份的歷史 HTML？
- 靜態解析與第三方偵測是否正確？
- TDI 第一版能否順利計算並產生合理的分布？

當 `pilot_30.csv → snapshot_metadata.csv → HTML → static_resources.csv → tdi_scores.csv → figures` 這條管線可以完整跑通，研究即從 Proposal 進入可實作階段。

## 2. Sample

- 樣本來源：Tranco Top 1M，名單 ID **74JZX**（<https://tranco-list.eu/list/74JZX/1000000>）
  - 名單生成日：2026-07-13（每日名單，合併 crux / farsight / majestic / radar / umbrella 五來源，涵蓋 2026-06-14 ~ 2026-07-13 的 30 天平均）
  - 下載日期：2026-07-14
- Pilot size：30 個網站
- Tier 分布：Tier1（rank 1~1000）5 個、Tier2（rank 1001~50000）10 個、Tier3（rank 50001~1M）15 個
- 抽樣方法：各 Tier 內固定隨機種子（seed=42）隨機抽樣，pilot_30 ⊆ pilot_100 ⊆ sample_full

## 3. Data Collection

- 資料來源：Internet Archive Wayback Machine（CDX API）
- 目標年份：2022、2024、2026
- 查詢期間：每年 6/1~8/31（找不到時放寬至 5/1~9/30），選擇距 7/15 最近的快照
- 2026 特別處理：若執行日早於 2026-08-31，查詢結束日自動改為執行當日；找不到快照則標記 missing
- 下載方式：使用 Wayback `id_` 原始內容端點，取得未經改寫的原始 HTML

## 4. Static Parsing

解析以下 HTML 標籤中的資源網址：

| 標籤 | 屬性 | resource_type | 用於 TDI |
|------|------|---------------|----------|
| `script` | src | script | 是 |
| `link` | href | link | 網域數計入 |
| `iframe` | src | iframe | 網域數計入 |
| `img` | src | image | 保留，暫不用於 script 計數 |
| `source` | src | media | 保留 |

## 5. Third-party Definition

- 比較「網站網域」與「資源網址」的 registrable domain（eTLD+1，以 Public Suffix List 切分）。
- 不同 → 第三方；相同（含子網域）→ 第一方；無有效網域（相對路徑）→ 第一方。

## 6. TDI Calculation

```
TDI = 0.5 × min-max normalized(third_party_script_count)
    + 0.5 × min-max normalized(third_party_domain_count)
```

正規化對整批資料（所有網站 × 所有年份）計算，跨年可比較。TDI ∈ [0, 1]，越高代表越依賴第三方。

## 7. Preliminary Outputs

- `dataset/processed/resources/snapshot_metadata.csv` — 90 個快照任務的下載紀錄
- `dataset/processed/resources/static_resources.csv` — 所有解析出的資源
- `dataset/processed/indicators/tdi_scores.csv` — 每個 site-year 的 TDI
- `figures/` — 5 張圖表（Tier 分布、script 數、網域數、TDI 分布、TDI 趨勢）

### 自動統計結果

<!-- AUTO_RESULTS_START -->
<!-- 本區塊由 scripts/phase1_run_pipeline.py 自動產生 -->
- 報告更新日期：2026-07-14
- 使用樣本：`dataset\processed\samples\pilot_100.csv`
- 快照任務：300 個，下載成功 166 個，缺漏/失敗 134 個
    - missing_snapshot: 131
    - invalid_html: 3
- 解析出資源：10845 筆，其中第三方 4452 筆
- TDI 分數：166 筆 site-year
    - 2022 年平均 TDI：0.1020
    - 2024 年平均 TDI：0.1208
    - 2026 年平均 TDI：0.1248
<!-- AUTO_RESULTS_END -->

## 8. Problems Encountered

執行後請整理 `snapshot_metadata.csv` 的 `error_message` 統計，常見類型：

- `missing_snapshot`：該網站該期間沒有任何快照（長尾網站與 2026 年常見）
- `timeout`：Wayback 回應逾時（重試 3 次後放棄）
- `http_error:xxx`：下載時的 HTTP 錯誤
- `empty_response`：回應為空
- `invalid_html`：回應內容不像 HTML（可能是錯誤頁或非 HTML 資源）

### 實際觀察（pilot_100，2026-07-14）

1. **缺漏幾乎全是 `missing_snapshot`**（131/134），`invalid_html` 僅 3 個；timeout 都被重試機制救回，沒有造成最終失敗。執行期間 Wayback 曾短暫變慢（單一任務最長約 38 秒），節流與重試設計運作正常。
2. **Tier1 成功率反而最低**：Tier1 40%（12/30）< Tier2 57%（68/120）≈ Tier3 57%（86/150）。原因是 Tranco 前 1000 名含大量基礎設施網域（`akadns.net`、`domaincontrol.com`、`fastly.net`、`googleapis.com` 等 CDN/DNS），無實質首頁可存檔，也不屬於「網站治理」研究對象。
   - **待決定（Phase 2 前）**：(a) `included=0` 排除並在 `note` 註明，或 (b) 在 `category` 標註 `infrastructure` 後分開分析。
3. **45 個網站有完整三年面板**，為縱貫分析的核心子樣本。

## 9. Next Steps

1. 檢視 pilot_30 結果，確認缺漏率與解析品質可接受。
2. 擴大到 **pilot_100**：`python -m scripts.phase1_run_pipeline --sample dataset/processed/samples/pilot_100.csv`
3. 加入 **TMI**（tracking classification，需 tracker 清單）。
4. 加入 **SCI**（supplier concentration，需公司實體對應）。
5. 加入 **Headless Chrome 動態量測**（Playwright），建立靜態→動態校準係數。
