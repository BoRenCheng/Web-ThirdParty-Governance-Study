# 資料字典（Data Dictionary）

本文件說明專案中所有 CSV 檔案的欄位定義。

---

## 1. 樣本檔：`sample_full.csv` / `pilot_100.csv` / `pilot_30.csv`

位置：`dataset/processed/samples/`
產生程式：`crawler/tranco_sampler.py`
每一列 = 一個被抽中的網站。三個檔案欄位相同，pilot_30 ⊆ pilot_100 ⊆ sample_full。

| 欄位 | 型態 | 意義 | 範例 |
|------|------|------|------|
| site_id | 字串 | 網站唯一編號，依 sample_full 順序編成，三個檔案中同網站編號相同 | `S000001` |
| domain | 字串 | 網站主網域（來自 Tranco List） | `google.com` |
| rank | 整數 | Tranco 排名（越小越熱門） | `1` |
| tier | 字串 | 分層：Tier1（1~1000）、Tier2（1001~50000）、Tier3（50001~1000000） | `Tier1` |
| category | 字串 | 網站類別，Phase 1 一律 `unknown`，之後階段再標註 | `unknown` |
| included | 整數 | 是否納入分析：1=納入、0=排除（排除原因寫在 note） | `1` |
| note | 字串 | 備註，預設空白 | （空） |

---

## 2. 快照中繼資料：`snapshot_metadata.csv`

位置：`dataset/processed/resources/`
產生程式：`crawler/wayback_downloader.py`
每一列 = 一個「網站 × 年份」的快照下載任務（30 個網站 × 3 年 = 90 列）。

| 欄位 | 型態 | 意義 | 範例 |
|------|------|------|------|
| site_id | 字串 | 網站編號（對應樣本檔） | `S000001` |
| domain | 字串 | 網站主網域 | `google.com` |
| rank | 整數 | Tranco 排名 | `1` |
| tier | 字串 | 分層 | `Tier1` |
| target_year | 整數 | 目標年份 | `2022` |
| target_from | 字串 | 實際查詢起始日 YYYYMMDD（若放寬過期間，會是放寬後的日期） | `20220601` |
| target_to | 字串 | 實際查詢結束日 YYYYMMDD（2026 年會自動壓到今天） | `20220831` |
| timestamp | 字串 | 選中快照的 Wayback 時間戳（YYYYMMDDhhmmss），找不到快照時為空 | `20220715083012` |
| original | 字串 | 快照對應的原始網址 | `https://google.com/` |
| status_code | 字串 | 快照當時的 HTTP 狀態碼（CDX 回報，理論上都是 200） | `200` |
| mime_type | 字串 | 快照的 MIME 類型 | `text/html` |
| snapshot_url | 字串 | 人類可讀的 Wayback 網址（可貼到瀏覽器查看） | `https://web.archive.org/web/20220715083012/https://google.com/` |
| downloaded | 整數 | 1=下載成功、0=失敗或缺漏 | `1` |
| local_path | 字串 | HTML 存放的相對路徑（相對於專案根目錄） | `dataset/raw/wayback/2022/S000001.html` |
| error_message | 字串 | 失敗原因：`missing_snapshot` / `timeout` / `http_error:xxx` / `empty_response` / `invalid_html`；成功時為空 | `missing_snapshot` |

---

## 3. 靜態資源清單：`static_resources.csv`

位置：`dataset/processed/resources/`
產生程式：`parser/run_static_parser.py`
每一列 = HTML 中的一個外部資源引用（同一資源被引用兩次會有兩列）。

| 欄位 | 型態 | 意義 | 範例 |
|------|------|------|------|
| site_id | 字串 | 網站編號 | `S000001` |
| domain | 字串 | 網站主網域 | `example.com` |
| year | 整數 | 快照年份 | `2022` |
| tag | 字串 | HTML 標籤名稱：`script` / `link` / `iframe` / `img` / `source` | `script` |
| source_attr | 字串 | 資源網址來自哪個屬性：`src` 或 `href` | `src` |
| resource_type | 字串 | 資源類型：`script` / `link` / `iframe` / `image` / `media` | `script` |
| resource_url | 字串 | 正規化後的完整資源網址 | `https://www.google-analytics.com/analytics.js` |
| resource_domain | 字串 | 資源的完整主機名（含子網域） | `www.google-analytics.com` |
| registrable_domain | 字串 | 資源的可註冊網域（eTLD+1），第三方計數以此為準 | `google-analytics.com` |
| is_third_party | 整數 | 1=第三方（registrable domain 與網站不同）、0=第一方 | `1` |
| local_html_path | 字串 | 來源 HTML 檔案路徑 | `dataset/raw/wayback/2022/S000001.html` |

---

## 4. TDI 分數：`tdi_scores.csv`

位置：`dataset/processed/indicators/`
產生程式：`indicators/compute_tdi.py`
每一列 = 一個「網站 × 年份」的 TDI 分數（只包含快照下載成功的組合）。

| 欄位 | 型態 | 意義 | 範例 |
|------|------|------|------|
| site_id | 字串 | 網站編號 | `S000001` |
| domain | 字串 | 網站主網域 | `example.com` |
| year | 整數 | 年份 | `2022` |
| third_party_script_count | 整數 | 第三方 `<script src>` 數量 | `12` |
| third_party_domain_count | 整數 | 第三方 registrable domain 的不重複個數 | `8` |
| third_party_resource_count | 整數 | 第三方資源總數（所有標籤類型） | `25` |
| script_norm | 浮點數 | script 數的 min-max 正規化值（0~1，對整批資料計算） | `0.34` |
| domain_norm | 浮點數 | 網域數的 min-max 正規化值（0~1） | `0.42` |
| tdi | 浮點數 | 第三方依賴度指標 = 0.5 × script_norm + 0.5 × domain_norm | `0.38` |

注意：某網站某年若「完全沒有第三方資源」，仍會出現在此檔中，所有數值為 0。
