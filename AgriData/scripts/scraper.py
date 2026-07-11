# -*- coding: utf-8 -*-
"""
AgriData 爬蟲：台灣農產品批發市場交易行情（蔬菜類）
資料來源：https://amis.afa.gov.tw/m_veg/VegProdDayTransInfo.aspx
目標市場：台北一(109)、台北二(104)、板橋區(220)、三重區(241)
時間範圍：近兩年

依賴套件（請先執行）：
    pip install requests beautifulsoup4 pandas lxml
"""

import io
import os
import time
import calendar
from datetime import datetime, date

import requests
from bs4 import BeautifulSoup
import pandas as pd

# ── 設定 ────────────────────────────────────────────────────────────────────
BASE_URL  = "https://amis.afa.gov.tw/m_veg/VegProdDayTransInfo.aspx"
MARKETS   = ['104', '109', '220', '241']   # 台北二、台北一、板橋、三重
DATA_DIR  = os.path.join(os.path.dirname(__file__), '..', 'data')
OUT_FILE    = os.path.join(DATA_DIR, 'veg_taipei_raw.csv')
MONTHLY_DIR = os.path.join(DATA_DIR, 'monthly')

# 近兩年區間
START_YEAR, START_MONTH = 2024, 5
END_YEAR,   END_MONTH   = 2026, 5

AJAX_HEADERS = {
    'User-Agent'       : ('Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/148.0.0.0 Mobile Safari/537.36'),
    'Accept'           : '*/*',
    'Accept-Language'  : 'zh-TW,zh;q=0.8',
    'Origin'           : 'https://amis.afa.gov.tw',
    'Referer'          : BASE_URL,
    'x-microsoftajax'  : 'Delta=true',
    'x-requested-with' : 'XMLHttpRequest',
}


# ── 日期工具 ─────────────────────────────────────────────────────────────────
def ad_to_roc(dt: date) -> str:
    """將 date 物件轉為民國年字串，例如 date(2024,5,1) → '113/05/01'"""
    return f"{dt.year - 1911:03d}/{dt.month:02d}/{dt.day:02d}"


def generate_month_ranges():
    """產生從 START 到 END 每個月的 (roc起始, roc結束) 清單"""
    ranges = []
    y, m = START_YEAR, START_MONTH
    today = date.today()
    while (y, m) <= (END_YEAR, END_MONTH):
        first = date(y, m, 1)
        last  = date(y, m, calendar.monthrange(y, m)[1])
        if last > today:
            last = today
        if first <= today:
            ranges.append((ad_to_roc(first), ad_to_roc(last)))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return ranges


# ── ASP.NET AJAX Delta 解析 ───────────────────────────────────────────────────
def parse_delta(text: str) -> dict:
    """
    解析 ASP.NET UpdatePanel Delta 格式回應。
    格式：{長度}|{類型}|{id}|{內容(依長度)}|...
    回傳 {(type, id): content} 字典。
    """
    result = {}
    i = 0
    n = len(text)
    while i < n:
        try:
            p1 = text.index('|', i)
            raw_len = text[i:p1]
            if not raw_len.isdigit():
                break
            length = int(raw_len);  i = p1 + 1

            p2 = text.index('|', i)
            type_ = text[i:p2];     i = p2 + 1

            p3 = text.index('|', i)
            id_   = text[i:p3];     i = p3 + 1

            content = text[i:i + length]
            i += length + 1         # +1 for trailing |

            result[(type_, id_)] = content
        except (ValueError, IndexError):
            break
    return result


def extract_vs_from_html(html: str) -> dict:
    """從 HTML 字串中取出 __VIEWSTATE / __VIEWSTATEGENERATOR / __EVENTVALIDATION"""
    soup = BeautifulSoup(html, 'html.parser')
    def val(name):
        tag = soup.find('input', {'name': name})
        return tag['value'] if tag else ''
    return {
        '__VIEWSTATE'          : val('__VIEWSTATE'),
        '__VIEWSTATEGENERATOR' : val('__VIEWSTATEGENERATOR'),
        '__EVENTVALIDATION'    : val('__EVENTVALIDATION'),
    }


def update_vs_from_delta(delta: dict, vs: dict) -> dict:
    """從 Delta 字典中更新 ViewState；優先取 hiddenField，其次從 updatePanel HTML"""
    new_vs = vs.copy()

    # 方法一：hiddenField 直接帶值
    for (type_, id_), content in delta.items():
        if type_ == 'hiddenField' and id_ in new_vs:
            new_vs[id_] = content

    # 方法二：若 hiddenField 沒有更新，從最大的 updatePanel HTML 中解析
    if new_vs == vs:
        for (type_, _), content in delta.items():
            if type_ == 'updatePanel' and '__VIEWSTATE' in content:
                parsed = extract_vs_from_html(content)
                if parsed['__VIEWSTATE']:
                    new_vs.update(parsed)
                    break

    return new_vs


# ── 三步驟爬取 ───────────────────────────────────────────────────────────────
def step1_get_page(session: requests.Session) -> dict:
    """步驟一：GET 頁面，取得初始 ViewState"""
    r = session.get(BASE_URL, timeout=30)
    r.raise_for_status()
    return extract_vs_from_html(r.text)


def step2_switch_all_products(session: requests.Session, vs: dict,
                               start_roc: str, end_roc: str) -> dict:
    """步驟二：POST 切換「全部產品」，取回更新後的 ViewState"""
    data = [
        ('ctl00$ScriptManager_Master',
         'ctl00$contentPlaceHolder$ucVegProduct$updatePanel'
         '|ctl00$contentPlaceHolder$ucVegProduct$radlProductRange$0'),
        ('ctl00_contentPlaceHolder_ucVegMarket',  MARKETS[0]),
        ('ctl00_contentPlaceHolder_ucVegProduct', 'ALL'),
        ('__EVENTTARGET',
         'ctl00$contentPlaceHolder$ucVegProduct$radlProductRange$0'),
        ('__EVENTARGUMENT',  ''),
        ('__LASTFOCUS',      ''),
        ('__VIEWSTATE',           vs['__VIEWSTATE']),
        ('__VIEWSTATEGENERATOR',  vs['__VIEWSTATEGENERATOR']),
        ('__EVENTVALIDATION',     vs['__EVENTVALIDATION']),
        ('ctl00$contentPlaceHolder$ucDateScope$rblDateScope',   'P'),
        ('ctl00$contentPlaceHolder$ucSolarLunar$radlSolarLunar','S'),
        ('ctl00$contentPlaceHolder$txtSTransDate', start_roc),
        ('ctl00$contentPlaceHolder$txtETransDate', end_roc),
        ('ctl00$contentPlaceHolder$ucVegMarket$radlMarketRange','P'),
    ]
    for m in MARKETS:
        data.append(('ctl00$contentPlaceHolder$ucVegMarket$lstMarket', m))
    data += [
        ('ctl00$contentPlaceHolder$ucVegProduct$radlProductRange', 'A'),
        ('__ASYNCPOST', 'true'),
    ]

    r = session.post(BASE_URL, data=data, headers=AJAX_HEADERS, timeout=30)
    r.raise_for_status()
    delta = parse_delta(r.text)
    return update_vs_from_delta(delta, vs)


def step3_query(session: requests.Session, vs: dict,
                start_roc: str, end_roc: str) -> pd.DataFrame:
    """步驟三：POST 查詢，解析結果表格，回傳 DataFrame"""
    data = [
        ('ctl00$ScriptManager_Master',
         'ctl00$ScriptManager_Master|ctl00$contentPlaceHolder$btnQuery'),
        ('ctl00_contentPlaceHolder_ucVegMarket',  MARKETS[0]),
        ('ctl00_contentPlaceHolder_ucVegProduct', 'ALL'),
        ('ctl00$contentPlaceHolder$ucDateScope$rblDateScope',   'P'),
        ('ctl00$contentPlaceHolder$ucSolarLunar$radlSolarLunar','S'),
        ('ctl00$contentPlaceHolder$txtSTransDate', start_roc),
        ('ctl00$contentPlaceHolder$txtETransDate', end_roc),
        ('ctl00$contentPlaceHolder$ucVegMarket$radlMarketRange','P'),
    ]
    for m in MARKETS:
        data.append(('ctl00$contentPlaceHolder$ucVegMarket$lstMarket', m))
    data += [
        ('ctl00$contentPlaceHolder$ucVegProduct$radlProductRange', 'A'),
        ('__EVENTTARGET',    ''),
        ('__EVENTARGUMENT',  ''),
        ('__LASTFOCUS',      ''),
        ('__VIEWSTATE',           vs['__VIEWSTATE']),
        ('__VIEWSTATEGENERATOR',  vs['__VIEWSTATEGENERATOR']),
        ('__EVENTVALIDATION',     vs['__EVENTVALIDATION']),
        ('__ASYNCPOST', 'true'),
        ('ctl00$contentPlaceHolder$btnQuery', '查詢'),
    ]

    r = session.post(BASE_URL, data=data, headers=AJAX_HEADERS, timeout=60)
    r.raise_for_status()

    delta = parse_delta(r.text)

    # 找含有 <table> 的 updatePanel 區塊
    table_html = None
    for (type_, id_), content in delta.items():
        if type_ == 'updatePanel' and '<table' in content:
            table_html = content
            break

    if not table_html:
        return pd.DataFrame()

    # 用 pandas 直接讀取 HTML 表格
    try:
        dfs = pd.read_html(io.StringIO(table_html), header=0)
        # 篩出欄數 >= 5 的資料表（排除導覽/頁碼小表）
        data_dfs = [df for df in dfs if df.shape[1] >= 5]
        if not data_dfs:
            return pd.DataFrame()
        return pd.concat(data_dfs, ignore_index=True)
    except Exception as e:
        print(f"    [WARN] 表格解析失敗：{e}")
        return pd.DataFrame()


# ── 主程式 ───────────────────────────────────────────────────────────────────
def main():
    """批次爬取近兩年大台北地區所有蔬菜交易資料，儲存為 CSV"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MONTHLY_DIR, exist_ok=True)

    month_ranges = generate_month_ranges()
    total = len(month_ranges)
    print(f"[AgriData] 爬蟲啟動")
    print(f"   目標市場：台北一、台北二、板橋、三重")
    print(f"   月份區間：{total} 個月")
    print(f"   斷點續爬：已完成的月份將自動跳過\n")

    session = requests.Session()
    session.headers.update({'User-Agent': AJAX_HEADERS['User-Agent']})

    errors = []

    for i, (start_roc, end_roc) in enumerate(month_ranges, 1):
        # 月份檔名，例如 monthly/115-04.csv
        month_tag  = start_roc[:6].replace('/', '-')   # '115/04' → '115-04'
        month_file = os.path.join(MONTHLY_DIR, f"{month_tag}.csv")

        # 已存在則跳過（斷點續爬）
        if os.path.exists(month_file):
            existing = pd.read_csv(month_file, encoding='utf-8-sig')
            print(f"[{i:02d}/{total}] {start_roc[:7]}  [SKIP] 已存在 {len(existing):,} 筆")
            continue

        print(f"[{i:02d}/{total}] {start_roc} ~ {end_roc}", end='  ')
        try:
            vs  = step1_get_page(session);  time.sleep(1)
            vs  = step2_switch_all_products(session, vs, start_roc, end_roc)
            time.sleep(1)
            df  = step3_query(session, vs, start_roc, end_roc)

            if df.empty:
                print("(no data)")
            else:
                df['_month'] = start_roc[:7]
                df.to_csv(month_file, index=False, encoding='utf-8-sig')
                print(f"OK {len(df):,} rows -> {month_tag}.csv")

            time.sleep(2)

        except requests.RequestException as e:
            print(f"[FAIL] network error: {e}")
            errors.append((start_roc, str(e)))
            time.sleep(5)
        except Exception as e:
            print(f"[FAIL] error: {e}")
            errors.append((start_roc, str(e)))
            time.sleep(3)

    # ── 合併所有月份 CSV → 最終檔案 ──────────────────────────────────────────
    monthly_files = sorted([
        f for f in os.listdir(MONTHLY_DIR) if f.endswith('.csv')
    ])

    if not monthly_files:
        print("\n[WARN] 未取得任何資料。請確認網路連線，或網站結構是否已變更。")
        return

    print(f"\n合併 {len(monthly_files)} 個月份檔案...")
    all_dfs = [
        pd.read_csv(os.path.join(MONTHLY_DIR, f), encoding='utf-8-sig')
        for f in monthly_files
    ]
    result = pd.concat(all_dfs, ignore_index=True)
    result.drop_duplicates(inplace=True)
    result.to_csv(OUT_FILE, index=False, encoding='utf-8-sig')

    print(f"{'='*50}")
    print(f"[DONE] {len(result):,} rows total")
    print(f"       saved: {OUT_FILE}")
    if errors:
        print(f"[WARN] failed months ({len(errors)}): {[e[0] for e in errors]}")
        print(f"       re-run the script to retry failed months")


if __name__ == '__main__':
    main()
