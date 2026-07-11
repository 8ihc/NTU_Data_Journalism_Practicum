"""
104 暑期實習職缺分析腳本（Plotly 版）
=====================================
薪資分組（5 組，共 327 筆）：
  1. 待遇面議  : salary = "待遇面議"
  2. 論件計酬  : salary = "論件計酬0元"（min=max=0）
  3. 月薪-給下限: 月薪 X 元以上（salary_max = 9999999）
  4. 月薪-基本 : 月薪明確區間，salary_min <= 30,000
  5. 月薪-高薪 : 月薪明確區間，salary_min >  30,000

輸出：charts/ 資料夾，每張圖表一個 .html 檔
"""

import json, os, re, io, sys, collections
import numpy as np

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import jieba
import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp

# ── 路徑設定 ─────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
RAW_JSON   = os.path.join(BASE_DIR, '..', 'data', 'raw', 'internships_raw.json')
PROC_DIR   = os.path.join(BASE_DIR, '..', 'data', 'processed')
CHARTS_DIR = os.path.join(BASE_DIR, '..', 'charts')
os.makedirs(PROC_DIR,   exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

# ── 色票（報導者風格）────────────────────────────────────────────────────────
C_GREEN_DARK   = '#0E3532'
C_GREEN_HEAVY  = '#3C927A'
C_GREEN_MAIN   = '#6EE5B5'
C_GREEN_PASTEL = '#99ECC9'
C_GREEN_FADED  = '#C4F2DC'
C_GRAY_900     = '#1A1A1A'
C_GRAY_700     = '#4A4A4A'
C_GRAY_500     = '#8A8A8A'
C_GRAY_400     = '#AAAAAA'
C_GRAY_300     = '#CCCCCC'
C_YELLOW       = '#F2C94C'   # 暖黃 accent

# ── 5 組定義 ─────────────────────────────────────────────────────────────────
GROUP_ORDER  = ['mianyi', 'piecerate', 'hourly_basic', 'hourly_above', 'basic', 'high']
GROUP_LABELS = {
    'mianyi':       '待遇面議',
    'piecerate':    '不支薪',
    'hourly_basic': '基本時薪',
    'hourly_above': '高於基本時薪',
    'basic':        '月薪 <= 3萬',
    'high':         '月薪 > 3萬',
}
GROUP_COLORS = {
    'mianyi':       '#F2C94C',  # 暖黃：待遇面議（未揭露）
    'piecerate':    '#9B051E',  # 酒紅：不支薪（警示）
    'hourly_basic': '#F76977',  # 粉紅：基本時薪（= 196）
    'hourly_above': '#F4C6C6',  # 淡粉：高於基本時薪（> 196）
    'basic':        '#92BDE4',  # 淺藍：月薪 <= 3萬
    'high':         '#1A4F8A',  # 深藍：月薪 > 3萬
}

HOURLY_MIN_WAGE = 196  # 2026 基本時薪

def assign_group(j):
    sal = j.get('salary') or ''
    mn  = j.get('salary_min') or 0
    mx  = j.get('salary_max') or 0
    if '面議' in sal:
        return 'mianyi'
    if '論件計酬' in sal:
        return 'piecerate' if (mn == 0 and mx == 0) else None
    if '部分工時' in sal and '月薪' in sal:
        return 'high' if mn > 30000 else None
    if '時薪' in sal:
        # range 只要有高於 196 的就算高薪；salary_max=9999999 也算高於基本
        if mx > HOURLY_MIN_WAGE:
            return 'hourly_above'
        return 'hourly_basic'  # salary_max <= 196，即剛好等於基本時薪
    if '月薪' in sal:
        return 'basic' if mn <= 30000 else 'high'
    return None

# ── 停用詞 ───────────────────────────────────────────────────────────────────
STOPWORDS = set("""
的 了 在 是 我 有 和 就 不 人 都 一 一個 上 也 很 到 說 要 去 你
我們 那 好 會 這 他 她 為 以 可以 如 及 與 或 等 而 但 對 從 並
中 下 後 前 來 還 個 能 時 年 月 日 地 得 著 過 其 各 可 被 把
由 將 因 所以 因此 然後 但是 不過 雖然 如何 做 使 讓 給 向
工作 職缺 實習生 實習 暑期 暑假 計畫 公司 我們 機會 相關
負責 具備 歡迎 擔任 安排 提供 需要 進行 協助 參與 完成
以上 以下 不限 不拘 優先 錄取 面試 投遞 履歷 如有 進而
填寫 期間 全則 如若 不率 為期 申請 加入 完整 時薪 介紹 涵蓋
""".split())

def tokenize(text):
    text = re.sub(r'[a-zA-Z0-9\s\n\r\t【】（）()《》「」、，。！？：；…—·／/\-_]', ' ', text)
    words = jieba.lcut(text)
    return [w for w in words
            if len(w) >= 2
            and w not in STOPWORDS
            and not re.fullmatch(r'[\d\s]+', w)]

def get_word_freq(jobs, max_words=80):
    counter = collections.Counter()
    for j in jobs:
        text = (j.get('job_description') or '') + ' ' + (j.get('other_condition') or '')
        counter.update(tokenize(text))
    return dict(counter.most_common(max_words))

def hex_to_rgba(hex_col, alpha):
    r = int(hex_col[1:3], 16)
    g = int(hex_col[3:5], 16)
    b = int(hex_col[5:7], 16)
    return f'rgba({r},{g},{b},{alpha:.2f})'

def save_chart(fig, filename):
    path = os.path.join(CHARTS_DIR, filename)
    fig.write_html(path, include_plotlyjs='cdn', full_html=True)
    print(f'  ✓ {filename}')

LAYOUT_BASE = dict(
    font=dict(family='Noto Sans TC, Microsoft JhengHei, sans-serif',
              color=C_GRAY_900),
    plot_bgcolor='white',
    paper_bgcolor='white',
    margin=dict(l=60, r=40, t=80, b=60),
    hoverlabel=dict(bgcolor='white', font_size=13,
                    font_family='Noto Sans TC, Microsoft JhengHei'),
)

# =============================================================================
# 圖 01：薪資組別分布
# =============================================================================
def chart_group_dist(df):
    counts = df['group'].value_counts().reindex(GROUP_ORDER).fillna(0).astype(int)
    total  = counts.sum()
    labels = [GROUP_LABELS[g] for g in GROUP_ORDER]
    colors = [GROUP_COLORS[g] for g in GROUP_ORDER]
    pcts   = [f'{v/total*100:.1f}%' for v in counts.values]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels,
        y=counts.values,
        marker_color=colors,
        marker_line_color=C_GRAY_300,
        marker_line_width=1,
        text=[f'{v}<br>{p}' for v, p in zip(counts.values, pcts)],
        textposition='outside',
        textfont=dict(size=13, color=C_GRAY_700),
        hovertemplate='<b>%{x}</b><br>職缺數：%{y}<br>占比：%{customdata}<extra></extra>',
        customdata=pcts,
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text='暑期實習薪資揭露方式分布',
                   subtitle=dict(text=f'資料來源：104 人力銀行｜分析樣本 N={total}'),
                   font=dict(size=20, color=C_GREEN_DARK),
                   x=0.05),
        xaxis=dict(title='薪資揭露組別', showgrid=False,
                   tickfont=dict(size=13)),
        yaxis=dict(title='職缺數量', showgrid=True,
                   gridcolor=C_GRAY_300, zeroline=False,
                   range=[0, counts.max() * 1.25]),
        showlegend=False,
        height=480,
    )
    save_chart(fig, 'chart_01_group_dist.html')

# =============================================================================
# 圖 02：各組描述字數箱形圖
# =============================================================================
def chart_desc_length(df):
    fig = go.Figure()
    for g in GROUP_ORDER:
        data = df[df['group'] == g]['desc_len'].dropna()
        fig.add_trace(go.Box(
            y=data,
            name=GROUP_LABELS[g],
            marker_color=GROUP_COLORS[g],
            line_color=C_GRAY_700,
            fillcolor=hex_to_rgba(GROUP_COLORS[g], 0.7),
            boxmean='sd',
            hovertemplate=(
                '<b>%{x}</b><br>'
                '中位數：%{median}<br>'
                '上四分位：%{q3}<br>'
                '下四分位：%{q1}<extra></extra>'
            ),
        ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text='各薪資組別：工作描述字數分布',
                   subtitle=dict(text='以 job_description + other_condition 欄位合計字元數計算'),
                   font=dict(size=20, color=C_GREEN_DARK),
                   x=0.05),
        xaxis=dict(title='薪資揭露組別', showgrid=False),
        yaxis=dict(title='字元數', showgrid=True,
                   gridcolor=C_GRAY_300, zeroline=False),
        showlegend=False,
        height=500,
    )
    save_chart(fig, 'chart_02_desc_length.html')

# =============================================================================
# 圖 03：各組條件填寫率
# =============================================================================
def chart_requirements(df):
    metrics = [
        ('has_language', '有語言要求', C_GREEN_HEAVY),
        ('has_major',    '有科系要求', C_GREEN_MAIN),
        ('has_skill',    '有技能要求', C_GREEN_FADED),
    ]
    labels = [GROUP_LABELS[g] for g in GROUP_ORDER]
    fig = go.Figure()
    for col, name, color in metrics:
        rates = [df[df['group'] == g][col].mean() * 100 for g in GROUP_ORDER]
        fig.add_trace(go.Bar(
            name=name,
            x=labels,
            y=rates,
            marker_color=color,
            marker_line_color=C_GRAY_300,
            marker_line_width=0.5,
            text=[f'{v:.0f}%' for v in rates],
            textposition='outside',
            textfont=dict(size=11),
            hovertemplate=f'<b>%{{x}}</b><br>{name}：%{{y:.1f}}%<extra></extra>',
        ))
    fig.update_layout(
        **LAYOUT_BASE,
        title=dict(text='各薪資組別：條件欄位填寫率',
                   subtitle=dict(text='語言、科系、技能要求欄位是否有填寫'),
                   font=dict(size=20, color=C_GREEN_DARK),
                   x=0.05),
        barmode='group',
        xaxis=dict(title='薪資揭露組別', showgrid=False),
        yaxis=dict(title='填寫率（%）', showgrid=True,
                   gridcolor=C_GRAY_300, range=[0, 115]),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        height=500,
    )
    save_chart(fig, 'chart_03_requirements.html')

# =============================================================================
# 圖 04：全產業分布樹狀圖（Treemap）
# =============================================================================
def chart_industry_dist(groups_jobs):
    """矩形面積 = 該產業職缺總數；顏色 = 該產業最主要的薪資組別。
    hover 顯示完整薪資組別分布明細。
    """
    from collections import Counter, defaultdict

    # 重建「每產業 × 每薪資組」筆數
    ind_group: dict = defaultdict(Counter)
    for key in GROUP_ORDER:
        for j in groups_jobs[key]:
            ind = (j.get('industry') or '其他').strip()
            ind_group[ind][key] += 1

    # 依總數排序（大 → 小）
    industries = sorted(ind_group.keys(),
                        key=lambda x: -sum(ind_group[x].values()))

    labels, values, colors, hovers = [], [], [], []
    for ind in industries:
        cnt_by_grp = ind_group[ind]
        total      = sum(cnt_by_grp.values())
        dominant   = max(cnt_by_grp, key=cnt_by_grp.get)
        labels.append(ind)
        values.append(total)
        colors.append(GROUP_COLORS[dominant])
        breakdown = '<br>'.join(
            f'{GROUP_LABELS[g]}：{cnt_by_grp.get(g, 0)} 筆'
            for g in GROUP_ORDER if cnt_by_grp.get(g, 0) > 0
        )
        hovers.append(f'<b>{ind}</b><br>合計：{total} 筆<br>─────<br>{breakdown}')

    # 圖例：用 dummy Scatter 呈現顏色說明
    legend_traces = []
    for g in GROUP_ORDER:
        if any(ind_group[ind].get(g, 0) > 0 for ind in industries):
            legend_traces.append(go.Scatter(
                x=[None], y=[None],
                mode='markers',
                marker=dict(size=12, color=GROUP_COLORS[g], symbol='square'),
                name=GROUP_LABELS[g],
            ))

    fig = go.Figure(legend_traces)
    fig.add_trace(go.Treemap(
        labels=labels,
        parents=['' for _ in labels],
        values=values,
        marker=dict(
            colors=colors,
            line=dict(width=1.5, color='white'),
        ),
        hovertemplate='%{customdata}<extra></extra>',
        customdata=hovers,
        textinfo='label+value',
        textfont=dict(size=12,
                      family='Noto Sans TC, Microsoft JhengHei'),
    ))

    tm_layout = {k: v for k, v in LAYOUT_BASE.items() if k != 'margin'}
    tm_layout['margin'] = dict(l=20, r=20, t=20, b=20)
    fig.update_layout(
        **tm_layout,
        legend=dict(
            orientation='h', yanchor='top', y=-0.01,
            xanchor='left', x=0,
            font=dict(size=12),
            title=dict(text='顏色＝主要薪資型態  '),
        ),
        height=660,
    )
    save_chart(fig, 'chart_01_industry.html')

# =============================================================================
# 圖 05：TF-IDF 熱力圖（跨組比較）
# =============================================================================
def chart_wordcloud(groups_jobs):
    for key in GROUP_ORDER:
        jobs  = groups_jobs[key]
        label = GROUP_LABELS[key]
        color = GROUP_COLORS[key]
        n     = 60

        wf = get_word_freq(jobs, max_words=n)
        sorted_wf = sorted(wf.items(), key=lambda x: -x[1])
        if not sorted_wf:
            print(f'  ⚠ {label} 無文字，略過')
            continue

        words  = [w for w, _ in sorted_wf]
        freqs  = [f for _, f in sorted_wf]
        max_f  = max(freqs)
        sizes  = [12 + 46 * (f / max_f) ** 0.6 for f in freqs]
        colors = [hex_to_rgba(color, 0.35 + 0.65 * f / max_f) for f in freqs]

        rng = np.random.default_rng(42)
        x   = rng.uniform(-4, 4, len(words))
        y   = rng.uniform(-2, 2, len(words))

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x, y=y,
            mode='text',
            text=words,
            textfont=dict(size=sizes, color=colors,
                          family='Noto Sans TC, Microsoft JhengHei'),
            hovertemplate='<b>%{text}</b><br>出現次數：%{customdata}<extra></extra>',
            customdata=freqs,
        ))
        wc_layout = {k: v for k, v in LAYOUT_BASE.items() if k != 'margin'}
        wc_layout['margin'] = dict(l=20, r=20, t=90, b=20)
        fig.update_layout(
            **wc_layout,
            title=dict(text=f'【{label}】高頻詞文字雲',
                       subtitle=dict(text=f'已過濾停用詞，jieba 斷詞，前 {n} 詞依頻率調整字體大小'),
                       font=dict(size=18, color=C_GREEN_DARK),
                       x=0.05),
            xaxis=dict(visible=False, range=[-5, 5]),
            yaxis=dict(visible=False, range=[-2.5, 2.5]),
            height=420,
        )
        save_chart(fig, f'chart_04_wc_{key}.html')

# =============================================================================
# 圖 05：TF-IDF 熱力圖（跨組比較）
# =============================================================================
def chart_tfidf_heatmap(groups_jobs, top_per_group=8):
    from sklearn.feature_extraction.text import TfidfVectorizer

    valid_keys, corpora = [], []
    for key in GROUP_ORDER:
        texts = []
        for j in groups_jobs[key]:
            text = (j.get('job_description') or '') + ' ' + (j.get('other_condition') or '')
            toks = tokenize(text)
            if toks:
                texts.append(' '.join(toks))
        if texts:
            corpora.append(' '.join(texts))
            valid_keys.append(key)

    vec      = TfidfVectorizer(max_features=5000)
    mat      = vec.fit_transform(corpora)
    features = vec.get_feature_names_out()

    # 每組取 top_per_group 個獨特詞，聯集作為 y 軸
    selected = []
    seen     = set()
    for idx in range(len(valid_keys)):
        scores  = mat[idx].toarray().flatten()
        top_idx = scores.argsort()[-top_per_group:][::-1]
        for i in top_idx:
            w = features[i]
            if w not in seen:
                selected.append(w)
                seen.add(w)

    # 建立熱力圖矩陣
    z      = []
    labels = [GROUP_LABELS[k] for k in valid_keys]
    for w in selected:
        row = []
        for idx in range(len(valid_keys)):
            scores = mat[idx].toarray().flatten()
            fidx   = list(features).index(w) if w in features else -1
            row.append(round(float(scores[fidx]), 4) if fidx >= 0 else 0.0)
        z.append(row)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=labels,
        y=selected,
        colorscale=[
            [0.0,  '#FFFFFF'],
            [0.3,  '#D6E8F7'],  # 極淺藍
            [0.6,  '#92BDE4'],  # 淺藍
            [0.85, '#4D8FC4'],  # 中藍
            [1.0,  '#1A4F8A'],  # 深藍
        ],
        hoverongaps=False,
        hovertemplate='<b>%{y}</b><br>%{x}<br>TF-IDF：%{z:.4f}<extra></extra>',
        colorbar=dict(title='TF-IDF', tickfont=dict(size=11)),
        xgap=2, ygap=1,
    ))
    hm_layout = {k: v for k, v in LAYOUT_BASE.items() if k != 'margin'}
    hm_layout['margin'] = dict(l=100, r=60, t=30, b=60)
    fig.update_layout(
        **hm_layout,
        xaxis=dict(side='bottom', tickfont=dict(size=12)),
        yaxis=dict(autorange='reversed', tickfont=dict(size=11)),
        height=max(420, len(selected) * 22 + 120),
    )
    save_chart(fig, 'chart_03_tfidf_heatmap.html')

# =============================================================================
# 圖 05：各組 TF-IDF Top 關鍵詞
# =============================================================================
def chart_tfidf(groups_jobs):
    from sklearn.feature_extraction.text import TfidfVectorizer

    valid_keys, corpora = [], []
    for key in GROUP_ORDER:
        texts = []
        for j in groups_jobs[key]:
            text = (j.get('job_description') or '') + ' ' + (j.get('other_condition') or '')
            toks = tokenize(text)
            if toks:
                texts.append(' '.join(toks))
        if texts:
            corpora.append(' '.join(texts))
            valid_keys.append(key)

    if len(valid_keys) < 2:
        print('  ⚠ TF-IDF 資料不足，略過')
        return

    vec      = TfidfVectorizer(max_features=5000)
    mat      = vec.fit_transform(corpora)
    features = vec.get_feature_names_out()
    top_n    = 10

    fig = sp.make_subplots(
        rows=1, cols=len(valid_keys),
        subplot_titles=[GROUP_LABELS[k] for k in valid_keys],
        shared_yaxes=False,
    )
    for idx, key in enumerate(valid_keys):
        scores  = mat[idx].toarray().flatten()
        top_idx = scores.argsort()[-top_n:][::-1]
        w       = [features[i] for i in top_idx][::-1]
        v       = [scores[i]   for i in top_idx][::-1]
        color   = GROUP_COLORS[key]

        fig.add_trace(go.Bar(
            x=v, y=w,
            orientation='h',
            marker_color=color,
            marker_line_color=C_GRAY_300,
            marker_line_width=0.5,
            hovertemplate='<b>%{y}</b><br>TF-IDF：%{x:.4f}<extra></extra>',
            showlegend=False,
        ), row=1, col=idx+1)

    tfidf_layout = {k: v for k, v in LAYOUT_BASE.items() if k != 'margin'}
    tfidf_layout['margin'] = dict(l=80, r=40, t=100, b=60)
    fig.update_layout(
        **tfidf_layout,
        title=dict(text='各薪資組別 TF-IDF Top 10 關鍵詞',
                   subtitle=dict(text='每組作為單一文件，與其他組比較後的相對重要詞彙'),
                   font=dict(size=20, color=C_GREEN_DARK),
                   x=0.05),
        height=500,
    )
    for i in range(1, len(valid_keys)+1):
        fig.update_xaxes(showgrid=True, gridcolor=C_GRAY_300,
                         tickfont=dict(size=10), row=1, col=i)
        fig.update_yaxes(tickfont=dict(size=11), row=1, col=i)

    save_chart(fig, 'chart_05_tfidf.html')

# =============================================================================
# 主程式
# =============================================================================
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--outdir', default=None,
                        help='輸出資料夾（預設：charts/）')
    args = parser.parse_args()
    if args.outdir:
        CHARTS_DIR = os.path.join(BASE_DIR, '..', args.outdir)
        os.makedirs(CHARTS_DIR, exist_ok=True)

    print('=' * 60)
    print('載入資料 & 分組...')
    with open(RAW_JSON, encoding='utf-8') as f:
        all_jobs = json.load(f)

    for j in all_jobs:
        j['group']        = assign_group(j)
        j['desc_len']     = len(j.get('job_description') or '')
        j['has_language'] = int(bool((j.get('language') or '').strip()))
        j['has_major']    = int(bool((j.get('major')    or '').strip()))
        j['has_skill']    = int(bool((j.get('skill')    or '').strip()))

    kept = [j for j in all_jobs if j['group'] is not None]
    df   = pd.DataFrame(kept)
    df.to_csv(os.path.join(PROC_DIR, 'internships_labeled.csv'),
              index=False, encoding='utf-8-sig')

    groups_jobs = {k: [j for j in kept if j['group'] == k] for k in GROUP_ORDER}

    print(f'\n分析資料集：{len(kept)} 筆')
    for k in GROUP_ORDER:
        print(f'  {GROUP_LABELS[k]}: {len(groups_jobs[k])} 筆')

    print('\n繪製圖表...')
    chart_group_dist(df)
    chart_desc_length(df)
    chart_requirements(df)

    print('  生成產業分布圖...')
    chart_industry_dist(groups_jobs)

    print('  生成 TF-IDF 熱力圖...')
    chart_tfidf_heatmap(groups_jobs)

    print('  生成 TF-IDF 長條圖...')
    chart_tfidf(groups_jobs)

    print('\n描述統計（描述字數）：')
    stats = df.groupby('group')['desc_len'].agg(['mean','median','min','max'])
    stats.index = [GROUP_LABELS[i] for i in stats.index]
    print(stats.round(0).to_string())

    print('\n條件填寫率：')
    rates = df.groupby('group')[['has_language','has_major','has_skill']].mean().mul(100).round(1)
    rates.index = [GROUP_LABELS[i] for i in rates.index]
    print(rates.to_string())

    print(f'\n✅ 完成！所有圖表已存至 charts/')
