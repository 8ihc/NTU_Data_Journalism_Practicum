# CLAUDE.md — 104 求職資料分析專案指南

## 專案概述

本專案為新聞資料分析課程 Assignment 104 Job + Text Processing。  
目標：爬取 104 求職網**暑期實習**職缺資訊，分析**薪資結構與產業分布**，並以新聞報導形式呈現。

### 新聞角度（雙主軸）
1. **電視業 100% 不支薪**：23 筆電視業暑期實習全數不支薪，與整體市場形成強烈反差
2. **STEM／金融業薪資最高**：本資料月薪最高達 **160,000 元**（AI 量化實習生，證券及期貨業）；半導體、IC設計、電腦周邊業集中在月薪 > 3 萬

---

## 實際目錄結構

```
104_Job_Data/
├── CLAUDE.md                        # 本檔案：AI 行為準則與專案指南
├── LOG.md                           # 操作日誌（AI 自動維護）
├── REPORT.html                      # 完整新聞報導（最終交付）
├── requirements.txt                 # Python 套件清單
├── data/
│   ├── raw/
│   │   ├── internships_raw.json     # 最終分析資料（465 筆過濾後，434 有效）
│   │   ├── internships_raw.csv      # 同上 CSV 版本
│   │   ├── checkpoint.json          # 爬蟲斷點存檔（465 筆）
│   │   ├── checkpoint_full_2090.json # 原始爬取備份（2090 筆）
│   │   ├── eda_summary.txt          # 初步資料摘要
│   │   ├── salary_groups.txt        # 薪資分組統計
│   │   └── industry_table.csv       # 前 15 大產業統計表
│   └── processed/
│       └── internships_labeled.csv  # 已標記薪資組別的資料
├── scripts/
│   ├── scraper.py                   # 爬蟲主程式（兩階段 API）
│   ├── analysis.py                  # 主分析腳本（圖表生成）
│   └── proto_industry.py            # 產業圖原型比較腳本
└── charts/
    ├── chart_01_industry.html        # 全產業樹狀圖（Treemap）
    ├── chart_02_pct_bar.html         # 前 15 大產業薪資結構百分比橫條圖
    └── chart_03_tfidf_heatmap.html   # TF-IDF 關鍵詞熱力圖
```

---

## 資料概況

| 項目 | 數值 |
|------|------|
| 原始爬取筆數 | 2,090 筆 |
| 過濾後（職缺名稱含「暑期」） | 465 筆 |
| 最終分析筆數 | 434 筆 |
| 涵蓋產業數 | 66 種 |
| 爬取日期 | 2026-05-24 |
| 資料來源 | 104 人力銀行公開 API |

---

## 薪資分組定義（6 組）

| 組別 key | 標籤 | 顏色 | 定義 |
|---------|------|------|------|
| `mianyi` | 待遇面議 | `#F2C94C` 暖黃 | salary 欄位含「面議」 |
| `piecerate` | 不支薪 | `#9B051E` 酒紅 | 論件計酬且 salary_min = salary_max = 0 |
| `hourly_basic` | 基本時薪 | `#F76977` 粉紅 | 時薪制，salary_max = 196 元 |
| `hourly_above` | 高於基本時薪 | `#F4C6C6` 淡粉 | 時薪制，salary_max > 196 元 |
| `basic` | 月薪 ≤ 3萬 | `#92BDE4` 淺藍 | 月薪制，salary_min ≤ 30,000 元 |
| `high` | 月薪 > 3萬 | `#1A4F8A` 深藍 | 月薪制，salary_min > 30,000 元 |

> 30,000 元閾值略高於 2025 年法定基本月薪（27,470 元），作為高低月薪實習的分析門檻。

---

## AI 行為準則

### 1. 日誌記錄（強制執行）

**每次執行任何操作前後，必須自動更新 LOG.md。**

格式如下：

```markdown
## [YYYY-MM-DD HH:MM]
**Prompt：** <使用者輸入的完整提示>
**操作：** <AI 執行的具體動作描述>
**結果：** <執行結果摘要，含檔案變動、資料量等>
---
```

- 使用台灣時間（UTC+8）
- 每次對話開始與結束都需記錄
- 若有錯誤，亦需記錄錯誤訊息與處理方式

### 2. 程式碼規範

- Python 使用 `requests` 爬蟲，配合 104 官方 API 端點
- 爬取時加入 `time.sleep(1~3)` 延遲，避免過度請求
- 資料儲存為 UTF-8 編碼的 CSV/JSON
- 所有腳本需有簡短說明註解
- 圖表使用 Plotly 輸出為獨立 HTML（`include_plotlyjs='cdn'`）

### 3. 資料倫理

- 僅爬取公開職缺資訊，不收集個人資料
- 遵守 104 網站 robots.txt 規範
- 資料僅供學術分析用途

### 4. 報告維護

- 分析結果即時更新至 `REPORT.html`
- 圖表輸出至 `charts/`，以 `<iframe>` 嵌入報告
- 報告需包含：新聞引言、爬蟲設計、遇到的困難、資料量說明、圖表說明、結論

---

## 分析方法摘要

| 項目 | 內容 |
|------|------|
| 資料來源 | 104 人力銀行公開 API（搜尋 + detail 兩階段） |
| 爬取欄位 | 職缺名稱、公司名稱、薪資文字、薪資上下限、產業別、工作描述、其他條件、地點、學歷、科系、語言、技能、年資 |
| 主要分析欄位 | salary、salary_min、salary_max、industry、job_description、other_condition |
| 薪資分組 | 6 組（詳見上表） |
| 產業圖 | Plotly Treemap（面積＝職缺數，顏色＝主要薪資組別） |
| 薪資結構圖 | 前 15 大產業 100% 橫條堆疊圖 |
| 文字分析 | jieba 斷詞 + scikit-learn TF-IDF，跨組關鍵詞熱力圖 |

---

## 使用工具

| 工具 | 類型 | 用途 |
|------|------|------|
| Claude Sonnet 4.6 | AI | 爬蟲設計、分析腳本、圖表生成、報告撰寫 |
| jieba | 非 AI 套件 | 中文斷詞（TF-IDF 前處理） |
| scikit-learn TfidfVectorizer | 非 AI 套件 | 跨組關鍵詞差異分析 |
| Plotly | 非 AI 套件 | 互動式視覺化圖表 |

---

*本 CLAUDE.md 由 Claude Sonnet 4.6 建立，最後更新：2026-05-24。*
