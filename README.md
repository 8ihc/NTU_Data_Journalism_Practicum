# 新聞資料分析實習作品集
**2026 NTU Data Journalism Practicum Portfolio**

國立臺灣大學新聞研究所｜2026「新聞資料處理與視覺呈現」課程作業成果

---

## 課程專題 Course Projects

### 🥬 小吃店的燙青菜為什麼老是那幾種？
**[AgriData/](AgriData/)**

從農業部批發市場交易資料，用資料分析解答一個日常觀察。

爬取大台北四個批發市場（台北一、台北二、板橋、三重）2024–2026 年共 **442,115 筆**蔬菜交易記錄，分析 412 個品項的均價、價格穩定性與供貨率。資料顯示，七種常見燙青菜的供貨率均為 1.00，均價全數低於 108 個品項的中位數（50.1 元）；即使在季節高峰期，這些蔬菜的價格仍屬相對便宜。研究也發現，不同燙青菜的季節高低峰並不完全重疊，讓餐廳得以靈活調配，形成緩衝機制。

**技術亮點**：自製爬蟲模擬 ASP.NET WebForms POST 請求、Plotly 互動式視覺化（散點圖、排行長條圖、季節熱圖）、交易量加權均價與變異係數設計

→ **[查看完整報告 REPORT.html](AgriData/REPORT.html)**

---

*Why do Taiwanese street food stalls always serve the same handful of blanched vegetables? Scraped 442,115 wholesale transaction records from four Taipei-area vegetable markets (2024–2026) to analyze price, price stability, and availability across 412 vegetable varieties. All seven "blanched staples" had 100% availability and prices below the median across all items — even at seasonal peaks. The data also suggests a substitution-pool effect: because different vegetables have non-overlapping seasonal price swings, restaurants can flexibly swap between them, keeping overall costs stable.*

*Tech: custom ASP.NET scraper (requests + BeautifulSoup), pandas, Plotly interactive charts*

---

### 💼 電視業暑期實習，100% 不支薪
**[104_Job_Data/](104_Job_Data/)**

爬取 104 人力銀行 434 筆暑期實習職缺，分析台灣各產業實習薪資結構的落差。

**主要發現**：電視業 23 筆職缺全數不支薪（TVBS、八大電視），是本資料中唯一此狀況的產業；另一端，月薪最高的職缺來自證券及期貨業（AI 量化實習生，**16 萬元**）。TF-IDF 文字分析初步顯示，不支薪職缺的描述偏重媒體製作技能（社群、剪輯、新聞），高薪職缺則偏重工程技術詞彙，兩者語言生態明顯不同。資料為 2026 年 5 月 24 日單日爬取，不代表整體市場長期樣貌。

**技術亮點**：104 官方 API 兩階段爬蟲、jieba 中文斷詞、TF-IDF 跨組關鍵詞熱力圖、Plotly Treemap

→ **[查看完整報告 REPORT.html](104_Job_Data/REPORT.html)**

---

*Scraped 434 summer internship listings from 104.com.tw and analyzed salary structure across 66 industries. Key finding: all 23 TV broadcasting internship listings (from TVBS and Ba-Da TV) offer zero pay — the only industry in the dataset with 100% unpaid internships. TF-IDF text analysis of job descriptions reveals that unpaid listings cluster around media production skills (editing, social media, news), while high-salary listings cluster around quantitative and engineering terms. Note: data reflects a single-day snapshot (2026-05-24) and may not represent long-term market trends.*

*Tech: two-stage API scraper, jieba tokenization, scikit-learn TF-IDF, Plotly Treemap & heatmap*

---

## 課堂作業 Assignments

| 作業 | 主題 | 資料來源 |
|------|------|----------|
| [AS01](assignments/AS01_google_trend.html) | Google Trends 趨勢視覺化 | Google Trends |
| [AS02](assignments/AS02_counting_data.html) | 進口違規品項計數 ＋ 蔬果農藥殘留 | 食藥署、衛福部 |
| [AS03](assignments/AS03_know-your-data.html) | 家庭消費支出 ＋ 各鄉鎮人口密度 | 主計總處、內政部 |
| [AS04](assignments/AS04_join_edu_data.html) | 教育資料合併分析 | 教育部 |
| [AS05](assignments/AS05_survey_presentation.html) | 問卷資料分析與呈現 | 課堂調查資料 |

所有作業使用 R（tidyverse、ggplot2）撰寫，原始碼為 `.Rmd` 格式。

---

## 關於我 About

臺大社會學系學生，關注資料新聞與調查報導。
熟悉使用 R 與 Python 進行資料清理、分析、視覺化與網路爬蟲。
擅長使用 Claude Code 等 AI 工具完成任務。

目前尋求新聞資料分析與視覺化相關實習機會。