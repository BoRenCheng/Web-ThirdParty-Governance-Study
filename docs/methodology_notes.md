# 方法論筆記（Methodology Notes）

本文件記錄 Phase 1 的研究方法設計理由，供論文方法章節與口試答辯使用。

---

## 1. 為什麼使用 Tranco List

網站排名名單有很多選擇（Alexa、Majestic、Umbrella 等），但學術研究普遍改用 **Tranco**（Le Pochat et al., NDSS 2019），理由：

1. **抗操縱**：Tranco 合併多個來源（目前含 Cloudflare Radar、Majestic、Chrome UX Report 等）並取 30 天平均，單日灌流量無法擠進名單。
2. **可重現**：每份名單有永久 ID，論文中引用該 ID，任何人都能下載同一份名單重現抽樣。
3. **持續維護**：Alexa 已於 2022 年停止服務，Tranco 是目前 web measurement 領域的事實標準。

## 2. 為什麼採用 Tier1 / Tier2 / Tier3 分層抽樣

網站流量呈極端長尾分布：頭部網站（Google、YouTube）與長尾小網站的技術資源、治理能力天差地遠。若做簡單隨機抽樣，樣本會幾乎全是長尾網站，頭部網站可能一個都抽不到。分層抽樣確保三個母體區段都有足夠觀察數：

- **Tier1（rank 1~1000）**：頭部網站，通常有專職工程與資安團隊。
- **Tier2（rank 1001~50000）**：中型網站，商業化程度高但資源有限。
- **Tier3（rank 50001~1000000）**：長尾網站，多數使用現成套件與第三方服務。

這樣的分層讓後續可以比較「治理能力不同的網站，第三方依賴的演變是否不同」——這是治理策略矩陣的基礎。

## 3. 為什麼先做 pilot_30

30 個網站 × 3 個年份 = 90 個下載任務，約 10~15 分鐘可跑完。目的：

1. 在小樣本上驗證整條管線（抽樣 → 下載 → 解析 → 指標 → 圖表）能穩定跑通。
2. 及早暴露問題：快照缺漏率多高？哪些錯誤類型常見？解析結果合不合理？
3. 避免一開始就對 Wayback Machine 發出上萬個請求，浪費資源也不禮貌。

pilot_30 ⊆ pilot_100 ⊆ sample_full（子集設計），pilot 階段下載的資料在擴大樣本時可直接沿用。

## 4. 為什麼使用 Wayback Machine

縱貫性研究需要「過去的網站長什麼樣子」，但我們無法回到 2022 年去爬網站。Internet Archive 的 Wayback Machine 是唯一大規模、公開、可程式化存取的網頁歷史檔案庫，其 CDX API 可以精確查詢某網域在特定日期範圍的所有快照。這是縱貫性 web measurement 研究的標準資料來源（例如 Lerner et al., USENIX Security 2016 用它研究追蹤技術 20 年演變）。

## 5. 為什麼選擇 2022、2024、2026

1. **等距觀測**（每兩年一點），符合縱貫性研究設計。
2. 2022~2026 涵蓋了重要的治理環境變化：GDPR 執法成熟、第三方 cookie 退場政策反覆、供應鏈攻擊（如 Polyfill.io 事件）引發的第三方風險意識。
3. 每年固定取**暑期（6~8 月，目標日 7/15）**的快照，控制季節效應（避開聖誕購物季、年末行銷高峰的暫時性第三方腳本）。

## 6. 為什麼第一階段先做靜態解析

靜態解析（直接分析 HTML 原始碼）的優點：

1. **可行性**：Wayback 保存的是 HTML 原始碼，靜態解析對歷史資料完全可行。
2. **速度與規模**：不需要瀏覽器，一秒可解析數十份 HTML。
3. **可重現**：同一份 HTML 解析結果永遠相同。

缺點是抓不到 JavaScript 動態注入的資源（例如 GTM 再載入的追蹤器），因此第二階段會用 Headless Chrome 對「現在的網站」做動態量測，估計靜態解析的低估幅度（校準係數）。

## 7. 第三方資源如何定義

採用 web measurement 文獻的標準定義：**registrable domain（eTLD+1）比較法**。

- 取網站網域與資源網址各自的 registrable domain（用 Public Suffix List 處理 `.co.uk`、`.com.tw` 等複合頂級域）。
- 兩者**不同** → 第三方；**相同** → 第一方。
- 例：`example.com` 的頁面載入 `cdn.example.com/app.js` → 第一方（同為 example.com）；載入 `www.google-analytics.com/analytics.js` → 第三方。
- 相對路徑（`/main.js`）沒有網域，視為第一方。

已知限制：同一公司的不同網域（例如 facebook.com 與 fbcdn.net）會被算成第三方。這在 Phase 2 加入 entity mapping（如 DuckDuckGo Tracker Radar 的公司對照表）後修正。

## 8. TDI 第一版如何計算

TDI（Third-party Dependency Index）第一版：

```
TDI = 0.5 × normalized(third_party_script_count)
    + 0.5 × normalized(third_party_domain_count)
```

- **third_party_script_count**：第三方 `<script src>` 數量。script 可執行任意程式碼，是技術耦合與攻擊面的核心，因此單獨計權。
- **third_party_domain_count**：第三方 registrable domain 的不重複個數，衡量「依賴的廣度」（依賴多少個不同供應商）。
- 兩者先做 **min-max 正規化**（對整批資料、所有年份合併計算，因此跨年可直接比較），再等權平均。
- 等權（0.5 / 0.5）是第一版的中性選擇；權重敏感度分析留待正式分析階段。

## 9. 第一階段的限制

1. 只做靜態解析，動態注入的第三方資源會低估。
2. Wayback 快照可能不完整（某些網站某些年份沒有快照、或存到錯誤頁）。
3. 2026 年資料在 2026-08-31 之前不完整，快照可用性偏低。
4. 只解析首頁，內頁的第三方資源不在範圍內。
5. 第三方判定以 registrable domain 為準，未做公司實體對應（CDN 子公司會被當成獨立第三方）。
6. TDI 權重為先驗設定，尚未做敏感度分析。
7. pilot_30 樣本量小，統計檢定力不足，僅供管線驗證，不可推論母體。

## 10. 下一階段（Phase 2+）計畫

1. **Tracker classification**：用 EasyList / EasyPrivacy / Tracker Radar 把第三方資源分類（分析、廣告、CDN、社群…）。
2. **TMI（Tracking & Monetization Index）**：衡量追蹤與變現類第三方的強度。
3. **Supplier mapping 與 SCI（Supplier Concentration Index）**：把網域對應到公司實體，計算供應商集中度（HHI 型指標）。
4. **Headless Chrome 動態量測**：對當前網站做動態載入量測，建立靜態→動態的校準係數。
5. **完整統計檢定**：擴大到 sample_full（1000 站），做跨年變化的檢定與混合效果模型。
6. **治理策略矩陣**：以 TDI × SCI（或 TMI）將網站定位到治理策略象限。
