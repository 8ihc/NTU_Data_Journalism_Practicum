# CLAUDE.md — AgriData 專案 AI 指令文件

> 本文件專為 Claude Code（AI Agent）而寫。目的是讓 Claude 像資深工程師一樣理解本專案的背景、所有技術決策與分析邏輯，在任何時間點接手都能產出一致且符合期望的程式碼與文字。

---

## 專案背景

**研究題目**：小吃店的「燙青菜」為什麼老是只有這幾種？
以大台北地區為例，從農產品批發市場交易資料，探討常見蔬菜之價格、價格穩定性與交易量。

**資料來源**：農業部農糧署「農產品批發市場交易行情站」
- 主要來源：https://amis.afa.gov.tw/main/Main.aspx（ASP.NET WebForms，歷史完整資料）
- 備用參考：https://data.moa.gov.tw/Service/OpenData/FromM/FarmTransData.aspx（JSON API，但僅涵蓋台北二市場，實測確認不足）

**研究對象**：大台北地區四個批發市場（台北一 109、台北二 104、板橋區 220、三重區 241）

**時間範圍**：2024/05/01 ～ 2026/05/14（25 個月，595 個不重複交易日）

---

## 技術棧

| 用途 | 套件 | 說明 |
|------|------|------|
| HTTP 請求 | `requests` | 以 `requests.Session()` 模擬 ASP.NET POST，不需啟動瀏覽器 |
| HTML 解析 | `beautifulsoup4` | 解析爬取回傳的 HTML 表格 |
| 資料處理 | `pandas` | 清理、轉換、統計指標計算 |
| 視覺化 | `plotly` | 互動式圖表，輸出 `.html`，嵌入 REPORT.html |

> `playwright` 與 `matplotlib` 最初列入計畫，但實際執行後確認不需要。
> amis.afa.gov.tw 可用純 requests 模擬，Plotly 已取代 matplotlib。

---

## 目錄結構

```
AgriData/
├── CLAUDE.md                  # 本文件：AI 行為指導
├── LOG.md                     # 操作日誌（含所有 user prompt 與 AI 動作）
├── REPORT.html                # 最終報告（直接在瀏覽器開啟）
├── scraper/
│   ├── scraper.py             # 爬蟲：爬取 amis.afa.gov.tw，輸出 veg_taipei_raw.csv
│   ├── analyze.py             # 清理 + 指標計算，輸出 veg_taipei_clean.csv、veg_stats.csv
│   └── visualize.py           # 視覺化，輸出 charts/*.html
├── data/
│   ├── veg_taipei_raw.csv     # 爬取原始資料（442,151 筆）
│   ├── veg_taipei_clean.csv   # 清理後資料（442,115 筆）
│   ├── veg_stats.csv          # 每品項分析指標（412 種蔬菜）
│   └── monthly/               # 斷點續爬暫存（每月一個 CSV）
└── charts/
    ├── scatter_price_stability.html
    ├── bar_avg_price_rank.html
    ├── bar_price_cv.html
    └── heatmap_seasonal.html
```

---

## 開發規範

### 程式碼
- 所有 `.py` 檔使用 **UTF-8** 編碼，檔頭加 `# -*- coding: utf-8 -*-`
- 函式與變數使用 `snake_case`；常數使用 `UPPER_SNAKE_CASE`
- 每個函式寫一行 docstring 說明用途
- 爬蟲每次 HTTP 請求後加入 `time.sleep(1~2)`，避免對政府伺服器造成負擔
- Windows 終端為 CP950 編碼，`print()` 中避免使用 Emoji，改用純文字

### 資料
- CSV 以 `utf-8-sig` 編碼儲存（確保 Excel 可正確開啟中文）
- 民國年字串（如 `113/05/01`）以正規表示式分割後加 1911 轉為西元年整數
- 蔬菜品項（`crop` 欄位）**不做任何合併**，全部 412 個細分品項各自獨立計算

### 圖表
- 所有圖表以 Plotly 產出，存至 `charts/`，格式為 `.html`
- `fig.write_html(out, include_plotlyjs='cdn', full_html=True)`
- 圖表標題與副標題一律用**繁體中文**；滑鼠 hover 文字同樣用繁體中文
- 嵌入 REPORT.html 時使用 `<iframe>`，不使用 `<img>`

---

## 分析指標設計決策

### 品項不合併的原因
同一蔬菜的不同品種價差可能顯著，
合併會掩蓋對採購決策有意義的差異。視覺化選代表品項時，以與通俗名稱最直接對應、
且日均交易量最大的細分品種為準。

### wavg_price（交易量加權均價）
```
wavg_price = Σ(avg_price × volume) / Σ(volume)
```
不直接對所有列的 avg_price 取算術平均，因為交易量小的日子（3,000 公斤）
與交易量大的日子（80,000 公斤）應有不同權重，才能真實反映市場行情。

### price_cv_y1 / price_cv_y2（價格變異係數，分兩年）
```
CV = std(每日 avg_price) / mean(每日 avg_price)
```
- **不加權**：對餐廳採購者而言，每天的報價各佔一天、一票，不因當日交易量大小而加權
- **分兩年計算**：年際整體漲跌（如甘藍 Y1 均價 20.5 元 → Y2 12.9 元）若合併計算，
  會虛增 CV，使「兩年都穩定」與「某年整體漲了一次」無法區分
- 年份分界：`CUTOFF = '2025/05'`（第一年 2024/05–2025/04，第二年 2025/05–2026/05）

### 篩選邏輯（四張圖各自）
| 圖表 | 篩選條件 | 品項數 |
|------|----------|--------|
| 圖一 散點圖 | `availability >= 1.0` | 108 種 |
| 圖二 均價排行 | `availability >= 1.0`，取均價最低 `TOP_BAR=45` 種 | 45 種 |
| 圖三 CV 排行 | `availability >= 1.0`，取 cv_avg 最低 20 種 | 20 種 |
| 圖四 季節熱圖 | 僅七種常見燙青菜 | 7 種 |

以供貨率（availability）為主要篩選依據，而非總交易量（公斤數），
是為了避免重型蔬菜（瓜類、根莖類）因單位重量大而獲得不公平排名優勢。

### 七種常見燙青菜（BLANCHED）
```python
BLANCHED = [
    'LF2 蕹菜 小葉',        # 空心菜
    'LO1 甘薯葉',            # 地瓜葉
    'LA1 甘藍 初秋',         # 高麗菜
    'LI3 萵苣菜 本島圓葉',   # 大陸妹
    'SX1 芽菜類 綠豆芽',     # 綠豆芽
    'LB2 小白菜 蚵仔白',     # 小白菜
    'SX2 芽菜類 黃豆芽',     # 黃豆芽
]
```
來源：Yahoo 新聞「高大空地豆」（高麗菜、大陸妹、空心菜、地瓜葉、豆芽）＋作者觀察（小白菜）＋豆芽細分

---

## 視覺化色票規範

```python
# 綠色系主色調（報導者風格，背景透明）
C_GREEN_DARK   = '#0E3532'
C_GREEN_HEAVY  = '#3C927A'
C_GREEN_MAIN   = '#6EE5B5'
C_GREEN_PASTEL = '#99ECC9'
C_GREEN_FADED  = '#C4F2DC'

# 灰色輔助色
C_GRAY_900 = '#1A1A1A'
C_GRAY_700 = '#4A4A4A'
C_GRAY_500 = '#8A8A8A'
C_GRAY_400 = '#AAAAAA'
C_GRAY_300 = '#CCCCCC'

# 語義色
C_BLANCHED = C_GREEN_HEAVY   # '#3C927A'，燙青菜標注色
C_MED_PRICE = '#9E7A4E'      # 均價中位數線
C_MED_CV    = '#493018'      # CV 中位數線
```

---

## 重要技術注意事項

### amis.afa.gov.tw 爬取流程（三步驟）
每個月份執行一次：
1. **GET** 頁面 → 取得 `__VIEWSTATE`、`__EVENTVALIDATION`、`__VIEWSTATEGENERATOR`
2. **POST**（切換全部產品）→ 觸發 AJAX，從 Delta 回應解析更新後的 ViewState
3. **POST**（執行查詢）→ 帶入日期範圍與市場代碼，從 Delta 回應解析 HTML 表格

### ASP.NET Delta 格式解析
回應格式：`{長度}|{類型}|{id}|{內容}|...`，依長度欄位切割（不能用 `split('|')`）。
找到 `type == 'updatePanel'` 且內容含 `<table` 的區塊，再用 `pd.read_html(io.StringIO(content))` 解析。

### pandas 3.0 相容性
`pd.read_html(html_string)` 在 pandas 3.0+ 會將字串誤判為檔案路徑，
必須改為 `pd.read_html(io.StringIO(html_string))`。

### 民國年轉換
```python
def roc_to_ad_year(roc_str):
    """從民國年字串取出西元年整數，例如 '113/05/01' → 2024"""
    parts = re.split(r'[/.-]', str(roc_str).strip())
    return int(parts[0]) + 1911
```

---

## 資料欄位定義：上價、中價、下價、平均價

> 來源：https://uptogo.com.tw/財經/產業分析/上價中價下價是什麼意思？/

| 欄位 | 計算基礎 | 意涵 |
|------|---------|------|
| **上價** | 最高 20% 交易的加權均值 | 優等品行情 |
| **中價** | 中間 60% 交易的加權均值 | 大宗批發主流價，零售商進貨主要參考 |
| **下價** | 最低 20% 交易的加權均值 | 低階品行情 |
| **平均價** | 全部交易的加權均值 | 整體市場行情代表值，本專案主要指標 |

本專案以**平均價**為主要指標；上下價差率＝（上價 − 下價）/ 平均價，作為品質分散程度的輔助指標。

---

## LOG.md 記錄規範

> **注意**：Claude Code 無法讀取對話訊息的確切發送時間，因此時間戳記為估算值，僅供參考。

每次對話後在 LOG.md 補記：
1. `[User Prompt]` — 使用者的原始輸入（逐字或摘要）
2. `[Action]` — AI 執行的具體操作（含使用的工具或修改的檔案）

格式：
```
- **[User Prompt]** 使用者輸入的 prompt 原文
- **[Action]** AI 執行的動作說明
```

---

## REPORT.html 撰寫規範

- 使用**繁體中文**撰寫
- 圖表以 `<iframe>` 嵌入（非 `<img>`）：
  ```html
  <iframe src="charts/xxx.html" style="width:100%;height:620px;border:none;" loading="lazy"></iframe>
  ```
- 每張圖表前後需有說明段落，解釋圖表呈現的現象與結論，引用具體數字
- 報告章節順序：題目背景（含研究對象說明）、資料來源、爬蟲設計、困難與解決、資料量統計、分析方法說明、視覺化圖表說明、結論
- 說明文字應保守表述推論（用「推測」「可能」「與…有關」，避免斷言因果）
