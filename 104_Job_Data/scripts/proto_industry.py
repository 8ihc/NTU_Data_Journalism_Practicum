"""
產業分布圖原型（快速比較用）
輸出兩個候選圖表：
  A. 全產業樹狀圖 (Treemap)         → charts/proto_A_treemap.html
  B. 前 15 大產業 100% 橫條堆疊圖   → charts/proto_B_pct_bar.html
"""

import json, os, sys, io, collections
from collections import Counter, defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import plotly.graph_objects as go

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
RAW_JSON   = os.path.join(BASE_DIR, '..', 'data', 'raw', 'internships_raw.json')
CHARTS_DIR = os.path.join(BASE_DIR, '..', 'charts')
os.makedirs(CHARTS_DIR, exist_ok=True)

# ── 色票 ──────────────────────────────────────────────────────────────────────
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
C_YELLOW       = '#F2C94C'

HOURLY_MIN_WAGE = 196

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
    'mianyi':       '#F2C94C',  # 暖黃
    'piecerate':    '#9B051E',  # 酒紅
    'hourly_basic': '#F76977',  # 粉紅
    'hourly_above': '#F4C6C6',  # 淡粉
    'basic':        '#92BDE4',  # 淺藍
    'high':         '#1A4F8A',  # 深藍
}

LAYOUT_BASE = dict(
    font=dict(family='Noto Sans TC, Microsoft JhengHei, sans-serif', color=C_GRAY_900),
    plot_bgcolor='white',
    paper_bgcolor='white',
    hoverlabel=dict(bgcolor='white', font_size=13,
                    font_family='Noto Sans TC, Microsoft JhengHei'),
)

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
        return 'hourly_above' if mx > HOURLY_MIN_WAGE else 'hourly_basic'
    if '月薪' in sal:
        return 'basic' if mn <= 30000 else 'high'
    return None

# ── 載入 & 分組 ───────────────────────────────────────────────────────────────
print('載入資料...')
with open(RAW_JSON, encoding='utf-8') as f:
    all_jobs = json.load(f)

kept = []
for j in all_jobs:
    g = assign_group(j)
    if g:
        j['group'] = g
        kept.append(j)
print(f'  有效職缺：{len(kept)} 筆')

# 每個產業 × 薪資組別 的筆數
ind_group: dict[str, Counter] = defaultdict(Counter)
for j in kept:
    ind = (j.get('industry') or '其他').strip()
    ind_group[ind][j['group']] += 1

# ─────────────────────────────────────────────────────────────────────────────
# CHART A：全產業 Treemap
#   矩形面積 = 該產業職缺數
#   顏色     = 該產業最主要的薪資組別
# ─────────────────────────────────────────────────────────────────────────────
print('繪製 A：Treemap...')

industries = sorted(ind_group.keys(), key=lambda x: -sum(ind_group[x].values()))
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

# 圖例說明：薪資組別 → 顏色
legend_traces = []
for g in GROUP_ORDER:
    legend_traces.append(go.Scatter(
        x=[None], y=[None],
        mode='markers',
        marker=dict(size=12, color=GROUP_COLORS[g], symbol='square'),
        name=GROUP_LABELS[g],
        showlegend=True,
    ))

fig_a = go.Figure(legend_traces)
fig_a.add_trace(go.Treemap(
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
    textfont=dict(size=12, family='Noto Sans TC, Microsoft JhengHei'),
))
fig_a.update_layout(
    **LAYOUT_BASE,
    margin=dict(l=20, r=20, t=100, b=20),
    title=dict(
        text='全產業職缺數量與主要薪資型態（樹狀圖）',
        subtitle=dict(text='矩形面積＝職缺數；顏色＝該產業最多職缺的薪資組別｜hover 顯示完整薪資分布'),
        font=dict(size=20, color=C_GREEN_DARK),
        x=0.05,
    ),
    legend=dict(
        orientation='h', yanchor='top', y=-0.02,
        xanchor='left', x=0,
        font=dict(size=12),
        title=dict(text='顏色＝主要薪資型態'),
    ),
    height=640,
)
path_a = os.path.join(CHARTS_DIR, 'proto_A_treemap.html')
fig_a.write_html(path_a, include_plotlyjs='cdn', full_html=True)
print(f'  ✓ proto_A_treemap.html')

# ─────────────────────────────────────────────────────────────────────────────
# CHART B：前 15 大產業 100% 橫條堆疊圖
#   y 軸 = 產業（依總職缺數排序）
#   x 軸 = 各薪資組別在該產業的佔比（%）
# ─────────────────────────────────────────────────────────────────────────────
print('繪製 B：前 15 大產業百分比堆疊橫條圖...')

top15 = [ind for ind, _ in
         sorted(ind_group.items(), key=lambda x: -sum(x[1].values()))[:15]]
top15_rev = list(reversed(top15))   # 從上到下：職缺最少→最多（讓最多的在最下方最顯眼）
totals = {ind: sum(ind_group[ind].values()) for ind in top15}

fig_b = go.Figure()
for g in GROUP_ORDER:
    pcts, hover_b, customdata_b = [], [], []
    for ind in top15_rev:
        cnt   = ind_group[ind].get(g, 0)
        total = totals[ind]
        pct   = round(cnt / total * 100, 1) if total > 0 else 0
        pcts.append(pct)
        hover_b.append(f'<b>{GROUP_LABELS[g]}</b><br>{ind}（共 {total} 筆）<br>本組：{cnt} 筆（{pct}%）')

    if any(p > 0 for p in pcts):
        fig_b.add_trace(go.Bar(
            name=GROUP_LABELS[g],
            y=top15_rev,
            x=pcts,
            orientation='h',
            marker_color=GROUP_COLORS[g],
            marker_line_color='white',
            marker_line_width=0.5,
            customdata=hover_b,
            hovertemplate='%{customdata}<extra></extra>',
        ))

# y 軸標籤加入總筆數
ytick_labels = [f'{ind}（{totals[ind]}）' for ind in top15_rev]

fig_b.update_layout(
    **LAYOUT_BASE,
    margin=dict(l=220, r=40, t=30, b=60),
    barmode='stack',
    xaxis=dict(title='佔比（%）', range=[0, 105],
               showgrid=True, gridcolor=C_GRAY_300,
               ticksuffix='%'),
    yaxis=dict(title='', showgrid=False,
               tickvals=top15_rev,
               ticktext=ytick_labels,
               tickfont=dict(size=12)),
    legend=dict(
        orientation='h', yanchor='bottom', y=1.02,
        xanchor='right', x=1,
        font=dict(size=11),
    ),
    height=580,
)
path_b = os.path.join(CHARTS_DIR, 'chart_02_pct_bar.html')
fig_b.write_html(path_b, include_plotlyjs='cdn', full_html=True)
print(f'  ✓ proto_B_pct_bar.html')

print('\n✅ 兩張原型圖完成！請開啟 charts/ 資料夾比較。')
