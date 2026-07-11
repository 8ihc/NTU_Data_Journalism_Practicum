"""
104 求職網「暑期實習」職缺爬蟲
================================
API 確認日期：2026-05-24（由使用者實際瀏覽器 Network 面板確認）

搜尋 API：GET https://www.104.com.tw/jobs/search/api/jobs
詳細 API：GET https://www.104.com.tw/api/jobs/{jobId}

執行方式：
    python scraper.py

斷點續抓：若中途中斷，重新執行會自動讀取 checkpoint.json 繼續。
"""

import requests
import json
import csv
import time
import random
import os
from datetime import datetime

# ── 路徑設定 ──────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
RAW_DIR    = os.path.join(BASE_DIR, '..', 'data', 'raw')
os.makedirs(RAW_DIR, exist_ok=True)

CHECKPOINT = os.path.join(RAW_DIR, 'checkpoint.json')
OUT_JSON   = os.path.join(RAW_DIR, 'internships_raw.json')
OUT_CSV    = os.path.join(RAW_DIR, 'internships_raw.csv')

# ── 共用 Headers（由瀏覽器 Network 面板確認）────────────────────────────────
BASE_HEADERS = {
    'User-Agent':      ('Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) '
                        'AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/148.0.0.0 Mobile Safari/537.36'),
    'Accept':          'application/json, text/plain, */*',
    'Accept-Language': 'zh-TW,zh;q=0.5',
    'DNT':             '1',
}

# ── 欄位預設值（與 parse_detail 完全對應）────────────────────────────────────
DETAIL_DEFAULTS = {
    # 1. 工作基本資訊（data.header）
    'job_name':          '',
    'cust_name':         '',
    'cust_url':          '',
    'appear_date':       '',
    # 2. 公司與產業背景（data 根層）
    'industry':          '',
    'employees':         '',
    'china_corp':        None,
    # 3. 詳細工作內容與型態（data.jobDetail）
    'job_description':   '',
    'job_category':      '',
    'salary':            '',
    'salary_min':        None,
    'salary_max':        None,
    'address_region':    '',
    'address_detail':    '',
    'landmark':          '',
    'need_emp':          '',
    'manage_resp':       '',
    'business_trip':     '',
    'work_shift':        '',
    'work_period_note':  '',
    'vacation_policy':   '',
    'start_working_day': '',
    # 4. 條件要求（data.condition）
    'accept_role':       '',
    'work_exp':          '',
    'edu':               '',
    'major':             '',
    'language':          '',
    'local_language':    '',
    'specialty':         '',
    'skill':             '',
    'certificate':       '',
    'driver_license':    '',
    'other_condition':   '',
}


# =============================================================================
# 輔助函式：安全處理陣列欄位
# =============================================================================

def join_list(lst, sep=', ', key=None):
    """
    將陣列安全地轉成以 sep 分隔的字串。
    - lst 為空或 None → 回傳 ''
    - key 不為 None → 取陣列中每個 dict 的指定 key
    - key 為 None，元素為 dict → 自動取 'description' 或 'name'
    - key 為 None，元素為字串 → 直接使用
    """
    if not lst:
        return ''
    parts = []
    for item in lst:
        if not item:
            continue
        if key:
            parts.append(str(item.get(key, '')))
        elif isinstance(item, dict):
            # dict 元素優先取 description，其次 name
            val = item.get('description') or item.get('name', '')
            if val:
                parts.append(str(val))
        else:
            parts.append(str(item))
    return sep.join(p for p in parts if p)


def parse_language(lang_list):
    """
    將 language 陣列轉成可讀字串。
    範例輸出：英文（聽:中等/說:中等/讀:精通/寫:精通）
    """
    if not lang_list:
        return ''
    parts = []
    for l in lang_list:
        name    = l.get('language', '')
        ability = l.get('ability', {})
        detail  = (f"聽:{ability.get('listening','')}"
                   f"/說:{ability.get('speaking','')}"
                   f"/讀:{ability.get('reading','')}"
                   f"/寫:{ability.get('writing','')}")
        parts.append(f"{name}（{detail}）")
    return '、'.join(parts)


# =============================================================================
# Phase 1：搜尋列表
# =============================================================================

def fetch_search_page(page: int, pagesize: int = 20) -> dict:
    """呼叫搜尋 API，回傳單頁 JSON"""
    url = 'https://www.104.com.tw/jobs/search/api/jobs'
    params = {
        'keyword':   '暑期實習',
        'kwop':      '7',           # 只搜職務名稱
        'mode':      's',
        'order':     '15',          # 相關度排序
        'page':      page,
        'pagesize':  pagesize,
        'jobsource': 'joblist_search',
    }
    headers = {**BASE_HEADERS, 'Referer': 'https://www.104.com.tw/jobs/search/'}
    resp = requests.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def collect_all_jobs() -> list:
    """
    Phase 1：依序抓完所有搜尋結果頁面，建立基本職缺清單。
    detail 欄位先填入預設值，等 Phase 2 覆寫。
    """
    print('=' * 60)
    print('Phase 1：收集職缺列表')
    print('=' * 60)

    first       = fetch_search_page(1)
    meta        = first['metadata']['pagination']
    total_pages = meta['lastPage']
    total_jobs  = meta['total']
    print(f'總筆數：{total_jobs}，共 {total_pages} 頁\n')

    all_jobs = []
    seen     = set()

    for page in range(1, total_pages + 1):
        try:
            raw   = first if page == 1 else fetch_search_page(page)
            items = raw.get('data', [])

            new_count = 0
            for item in items:
                job_no = item.get('jobNo', '')
                if not job_no or job_no in seen:
                    continue
                seen.add(job_no)

                # 搜尋列表可取得的基本欄位 + detail 預設值
                # 從 link.job 取出 detail API 用的 slug（e.g. "8pzqf"）
                job_link = item.get('link', {}).get('job', '')
                job_slug = job_link.rstrip('/').split('/')[-1] if job_link else ''

                record = {
                    'job_no':          job_no,    # 數字 ID（搜尋結果用）
                    'job_slug':        job_slug,   # 英數字 slug（detail API 用）
                    # 列表頁薪資（用於快速篩選；detail 會填入精確值）
                    'salary_low_list': item.get('salaryLow', 0),
                    'salary_high_list':item.get('salaryHigh', 0),
                    'desc_snippet':    item.get('description', ''),
                    'detail_fetched':  False,
                }
                # 合併 detail 欄位預設值
                record.update(DETAIL_DEFAULTS)
                # 從列表預填部分 header 欄位（detail 會覆寫為完整版）
                record['job_name']    = item.get('jobName', '')
                record['cust_name']   = item.get('custName', '')
                record['appear_date'] = item.get('appearDate', '')
                record['industry']    = item.get('coIndustryDesc', '')

                all_jobs.append(record)
                new_count += 1

            print(f'  第 {page:3d}/{total_pages} 頁  +{new_count} 筆  累計 {len(all_jobs)} 筆')

        except Exception as e:
            print(f'  第 {page} 頁錯誤：{e}，略過')

        time.sleep(random.uniform(0.8, 1.5))

    print(f'\nPhase 1 完成，共收集 {len(all_jobs)} 筆\n')
    return all_jobs


# =============================================================================
# Phase 2：職缺詳細頁
# =============================================================================

def fetch_job_detail(job_slug: str) -> dict:
    """呼叫 detail API，回傳單筆職缺 JSON（job_slug 為 URL 中的英數字 ID）"""
    url     = f'https://www.104.com.tw/api/jobs/{job_slug}'
    headers = {**BASE_HEADERS, 'Referer': f'https://www.104.com.tw/job/{job_slug}'}
    resp    = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def parse_detail(raw: dict) -> dict:
    """
    將 detail API 回應解析為欄位 dict。
    嚴格對照欄位規格表，所有陣列欄位都有空值防護。
    """
    d      = raw.get('data', {})
    header = d.get('header', {})
    jd     = d.get('jobDetail', {})
    cond   = d.get('condition', {})

    # ── workPeriod（含防錯）────────────────────────────
    work_period      = jd.get('workPeriod') or {}
    work_period_note = work_period.get('note', '')
    shifts           = work_period.get('shifts') or {}
    work_shift       = ', '.join(shifts.keys()) if shifts else ''

    return {
        # 1. 工作基本資訊（data.header）
        'job_name':          header.get('jobName', ''),
        'cust_name':         header.get('custName', ''),
        'cust_url':          header.get('custUrl', ''),
        'appear_date':       header.get('appearDate', ''),

        # 2. 公司與產業背景（data 根層）
        'industry':          d.get('industry', ''),
        'employees':         d.get('employees', ''),
        'china_corp':        d.get('chinaCorp'),

        # 3. 詳細工作內容與型態（data.jobDetail）
        'job_description':   jd.get('jobDescription', ''),
        'job_category':      join_list(jd.get('jobCategory'), key='description'),
        'salary':            jd.get('salary', ''),
        'salary_min':        jd.get('salaryMin'),
        'salary_max':        jd.get('salaryMax'),
        'address_region':    jd.get('addressRegion', ''),
        'address_detail':    jd.get('addressDetail', ''),
        'landmark':          jd.get('landmark', ''),
        'need_emp':          jd.get('needEmp', ''),
        'manage_resp':       jd.get('manageResp', ''),
        'business_trip':     jd.get('businessTrip', ''),
        'work_shift':        work_shift,
        'work_period_note':  work_period_note,
        'vacation_policy':   jd.get('vacationPolicy', ''),
        'start_working_day': jd.get('startWorkingDay', ''),

        # 4. 條件要求（data.condition）
        'accept_role':       join_list(
                                 cond.get('acceptRole', {}).get('role'),
                                 key='description'
                             ),
        'work_exp':          cond.get('workExp', ''),
        'edu':               cond.get('edu', ''),
        'major':             join_list(cond.get('major')),
        'language':          parse_language(cond.get('language')),
        'local_language':    join_list(cond.get('localLanguage')),
        'specialty':         join_list(cond.get('specialty')),
        'skill':             join_list(cond.get('skill')),
        'certificate':       join_list(cond.get('certificate')),
        'driver_license':    join_list(cond.get('driverLicense')),
        'other_condition':   cond.get('other', ''),
    }


def enrich_with_details(jobs: list, save_every: int = 50) -> list:
    """
    Phase 2：逐一補充 detail 欄位。
    - detail_fetched=True 的跳過，支援斷點續抓
    - 每 save_every 筆自動存一次 checkpoint
    """
    print('=' * 60)
    print('Phase 2：抓取職缺詳細描述')
    print('=' * 60)

    pending = [j for j in jobs if not j['detail_fetched']]
    total   = len(pending)
    done    = 0
    errors  = 0

    print(f'待抓取：{total} 筆\n')

    try:
        for job in pending:
            try:
                raw    = fetch_job_detail(job['job_slug'])
                parsed = parse_detail(raw)
                job.update(parsed)
                job['detail_fetched'] = True
                done += 1
            except Exception as e:
                errors += 1
                print(f'  ✗ {job["job_slug"]}（{job["job_name"][:20]}）失敗：{e}')

            if (done + errors) % 10 == 0:
                pct = (done + errors) / total * 100
                print(f'  進度 {done + errors}/{total}（{pct:.0f}%）'
                      f'  成功 {done}  失敗 {errors}')

            if (done + errors) % save_every == 0:
                save_checkpoint(jobs)

            time.sleep(random.uniform(1.0, 2.0))

    except KeyboardInterrupt:
        print(f'\n[中斷] 正在儲存 checkpoint...')
        save_checkpoint(jobs)
        print(f'已儲存，下次重新執行會從第 {done + 1} 筆繼續。')

    print(f'\nPhase 2 完成  成功 {done} 筆  失敗 {errors} 筆\n')
    return jobs


# =============================================================================
# Checkpoint & 儲存
# =============================================================================

def save_checkpoint(jobs: list):
    with open(CHECKPOINT, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    print('  [checkpoint 已儲存]')


def load_checkpoint() -> list | None:
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT, encoding='utf-8') as f:
            return json.load(f)
    return None


def save_final(jobs: list):
    """儲存最終結果（JSON + CSV）"""
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)

    if jobs:
        # 輸出欄位順序（排除內部狀態欄位）
        fields = [k for k in jobs[0].keys()
                  if k not in ('detail_fetched',)]
        with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(jobs)

    print('=' * 60)
    print('儲存完成')
    print(f'  JSON：{OUT_JSON}')
    print(f'  CSV ：{OUT_CSV}')
    print(f'  共 {len(jobs)} 筆職缺')
    print('=' * 60)


# =============================================================================
# 主程式
# =============================================================================

if __name__ == '__main__':
    start = datetime.now()
    print(f'開始時間：{start.strftime("%Y-%m-%d %H:%M:%S")}\n')

    jobs = load_checkpoint()
    if jobs:
        fetched = sum(1 for j in jobs if j['detail_fetched'])
        print(f'[讀取 checkpoint]  共 {len(jobs)} 筆，已完成 detail {fetched} 筆\n')
    else:
        jobs = collect_all_jobs()
        save_checkpoint(jobs)

    jobs = enrich_with_details(jobs)
    save_final(jobs)

    elapsed = datetime.now() - start
    print(f'\n總耗時：{elapsed}')
