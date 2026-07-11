# -*- coding: utf-8 -*-
"""
AgriData 視覺化（Plotly 互動版）
輸入：data/veg_stats.csv、data/veg_taipei_clean.csv
輸出：charts/ 底下 4 個互動 HTML 檔案
"""

import os
import warnings
import numpy as np
import pandas as pd
import plotly.graph_objects as go

warnings.filterwarnings('ignore')

DATA_DIR   = os.path.join(os.path.dirname(__file__), '..', 'data')
CHARTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'charts')
STATS_FILE = os.path.join(DATA_DIR, 'veg_stats.csv')
CLEAN_FILE = os.path.join(DATA_DIR, 'veg_taipei_clean.csv')

TOP_BAR     = 45
TOP_HEATMAP = 20

# 報導者色盤
C_RED_MAIN   = '#F80B28'
C_RED_HEAVY  = '#C40D23'
C_RED_DARK   = '#9B051E'
C_RED_FADED  = '#F4C6C6'
C_RED_PASTEL = '#F76977'
C_GRAY_900   = '#262626'
C_GRAY_700   = '#4A4A4A'
C_GRAY_600   = '#808080'
C_GRAY_500   = '#9C9C9C'
C_GRAY_400   = '#CDCDCD'
C_GRAY_300   = '#D8D8D8'
C_GRAY_200   = '#E2E2E2'
C_GRAY_100   = '#F1F1F1'

FONT_FAMILY = 'Noto Sans TC, Microsoft JhengHei, PingFang TC, sans-serif'

C_GREEN_DARK   = '#0E3532'
C_GREEN_HEAVY  = '#3C927A'
C_GREEN_MAIN   = '#6EE5B5'
C_GREEN_PASTEL = '#99ECC9'
C_GREEN_FADED  = '#C4F2DC'

C_BLANCHED = C_GREEN_HEAVY  # 燙青菜標示色（主）

BLANCHED = ['LF2 蕹菜 小葉', 'LO1 甘薯葉', 'LA1 甘藍 初秋', 'LI3 萵苣菜 本島圓葉',
            'SX1 芽菜類 綠豆芽', 'LB2 小白菜 蚵仔白', 'SX2 芽菜類 黃豆芽']

BASE_LAYOUT = dict(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family=FONT_FAMILY, color=C_GRAY_900, size=13),
    hoverlabel=dict(
        bgcolor='white',
        bordercolor=C_GRAY_300,
        font=dict(family=FONT_FAMILY, size=13),
    ),
)

XAXIS_STYLE = dict(gridcolor=C_GRAY_200, linecolor=C_GRAY_300, zeroline=False)
YAXIS_STYLE = dict(gridcolor=C_GRAY_200, linecolor=C_GRAY_300, zeroline=False)


def get_top(stats, n):
    """依供貨率降冪、日均量次排序，取前 n 名"""
    return (stats
            .sort_values(['availability', 'avg_daily_volume'], ascending=[False, False])
            .head(n)
            .copy())


def strip_code(s):
    """'LA1 甘藍 初秋' → '甘藍 初秋'"""
    parts = s.split(' ', 1)
    return parts[1] if len(parts) > 1 else s


def blanched_colors(crops, col_yes, col_no):
    """依是否為燙青菜回傳顏色列表"""
    return [col_yes if c in BLANCHED else col_no for c in crops]


def save_html(fig, filename):
    out = os.path.join(CHARTS_DIR, filename)
    fig.write_html(
        out, include_plotlyjs='cdn', full_html=True,
        config={
            'displayModeBar': True,
            'responsive': True,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
        },
    )
    print(f'[OK] {out}')


# ── 圖一：價格 × 穩定性 散點圖 ──────────────────────────────────────────────
def chart_scatter(stats):
    """availability=1.0 的全部品項，hover 顯示詳細資訊，燙青菜紅色標注"""
    top = stats[stats['availability'] >= 1.0].copy()
    top['cv_avg'] = top[['price_cv_y1', 'price_cv_y2']].mean(axis=1)

    # 點大小：日均交易量對數正規化到 8~48
    log_vol = np.log1p(top['avg_daily_volume'])
    size = (log_vol - log_vol.min()) / (log_vol.max() - log_vol.min()) * 40 + 8

    is_bl     = top['crop'].isin(BLANCHED)
    normal    = top[~is_bl].copy()
    highlight = top[is_bl].copy()

    fig = go.Figure()

    # 一般品項：只有 marker，hover 顯示詳細資訊
    fig.add_trace(go.Scatter(
        x=normal['wavg_price'],
        y=normal['cv_avg'],
        mode='markers',
        marker=dict(
            size=size[normal.index],
            color=C_GRAY_500,
            opacity=0.55,
            line=dict(width=0),
        ),
        name='其他品項',
        customdata=np.stack([
            normal['crop'],
            normal['avg_daily_volume'].round(0),
            normal['price_cv_y1'].round(3),
            normal['price_cv_y2'].round(3),
        ], axis=1),
        hovertemplate=(
            '<b>%{customdata[0]}</b><br>'
            '均價：%{x:.1f} 元/kg<br>'
            'CV 第一年：%{customdata[2]}<br>'
            'CV 第二年：%{customdata[3]}<br>'
            'CV 兩年均：%{y:.3f}<br>'
            '日均交易量：%{customdata[1]:,.0f} kg'
            '<extra></extra>'
        ),
    ))

    # 燙青菜：紅色 + 文字標注
    fig.add_trace(go.Scatter(
        x=highlight['wavg_price'],
        y=highlight['cv_avg'],
        mode='markers+text',
        text=[strip_code(c) for c in highlight['crop']],
        textposition='top right',
        textfont=dict(size=12, color=C_GREEN_DARK, family=FONT_FAMILY),
        marker=dict(
            size=size[highlight.index],
            color=C_BLANCHED,
            opacity=0.9,
            line=dict(width=1, color='white'),
        ),
        name='常見燙青菜',
        customdata=np.stack([
            highlight['crop'],
            highlight['avg_daily_volume'].round(0),
            highlight['price_cv_y1'].round(3),
            highlight['price_cv_y2'].round(3),
        ], axis=1),
        hovertemplate=(
            '<b>%{customdata[0]}</b><br>'
            '均價：%{x:.1f} 元/kg<br>'
            'CV 第一年：%{customdata[2]}<br>'
            'CV 第二年：%{customdata[3]}<br>'
            'CV 兩年均：%{y:.3f}<br>'
            '日均交易量：%{customdata[1]:,.0f} kg'
            '<extra></extra>'
        ),
    ))

    med_p = top['wavg_price'].median()
    med_c = top['cv_avg'].median()
    fig.add_vline(x=med_p, line_dash='dot', line_color='#9E7A4E', line_width=1.5,
                  annotation=dict(text=f'均價中位數 {med_p:.1f} 元',
                                  font=dict(size=11, color='#9E7A4E')),
                  annotation_position='top right')
    fig.add_hline(y=med_c, line_dash='dot', line_color='#493018', line_width=1.5,
                  annotation=dict(text=f'CV 中位數 {med_c:.2f}',
                                  font=dict(size=11, color='#493018')),
                  annotation_position='bottom right')

    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(
            text=('大台北蔬菜批發市場：價格、穩定性與日均供應量<br>'
                  '<sup>全年無間斷供貨品項 108 種｜2024.05–2026.05'
                  '｜圓圈大小 = 日均交易量</sup>'),
            font=dict(size=17, color=C_GRAY_900),
            x=0.02, xanchor='left',
        ),
        xaxis=dict(title='交易量加權均價（元/公斤）', **XAXIS_STYLE),
        yaxis=dict(title='CV（越低越穩定）', **YAXIS_STYLE),
        legend=dict(
            x=0.98, y=0.98, xanchor='right', yanchor='top',
            bgcolor='rgba(255,255,255,0.85)',
            bordercolor=C_GRAY_300, borderwidth=1,
        ),
        height=580,
        margin=dict(l=60, r=40, t=90, b=60),
    )
    save_html(fig, 'scatter_price_stability.html')


# ── 圖二：均價排行橫條圖 ─────────────────────────────────────────────────────
def chart_price_bar(stats):
    """availability=1.0 中均價最低 40 名，由低到高排列，Y1/Y2 並排，燙青菜紅色"""
    top = (stats[stats['availability'] >= 1.0]
           .sort_values('wavg_price')
           .head(TOP_BAR)
           .copy())
    labels = [strip_code(c) for c in top['crop']]
    is_bl  = top['crop'].isin(BLANCHED)

    colors_y1 = blanched_colors(top['crop'], C_BLANCHED,   C_GRAY_700)
    colors_y2 = blanched_colors(top['crop'], C_GREEN_PASTEL, C_GRAY_400)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=top['wavg_price_y1'],
        orientation='h', name='第一年（2024.05–2025.04）',
        marker=dict(color=colors_y1, opacity=0.85),
        customdata=top[['crop', 'wavg_price_y1']].values,
        hovertemplate='<b>%{customdata[0]}</b><br>第一年均價：%{x:.1f} 元/kg<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        y=labels, x=top['wavg_price_y2'],
        orientation='h', name='第二年（2025.05–2026.05）',
        marker=dict(color=colors_y2, opacity=0.85),
        customdata=top[['crop', 'wavg_price_y2']].values,
        hovertemplate='<b>%{customdata[0]}</b><br>第二年均價：%{x:.1f} 元/kg<extra></extra>',
    ))

    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(
            text=('大台北蔬菜批發市場：年際均價比較<br>'
                  '<sup>全年無間斷供貨品項中均價最低 45 種｜由低到高排列｜綠色為常見燙青菜</sup>'),
            font=dict(size=17, color=C_GRAY_900),
            x=0.02, xanchor='left',
        ),
        barmode='group',
        xaxis=dict(title='交易量加權均價（元/公斤）', **XAXIS_STYLE),
        yaxis=dict(tickfont=dict(size=11), **YAXIS_STYLE),
        legend=dict(
            x=0.98, y=0.02, xanchor='right', yanchor='bottom',
            bgcolor='rgba(255,255,255,0.85)',
            bordercolor=C_GRAY_300, borderwidth=1,
        ),
        height=950,
        margin=dict(l=130, r=40, t=90, b=60),
    )
    save_html(fig, 'bar_avg_price_rank.html')


# ── 圖三：季節性熱圖 ─────────────────────────────────────────────────────────
def chart_heatmap(stats, clean):
    """月均價相對全期均價漲跌幅熱圖，僅顯示常見燙青菜"""
    top_crops = [c for c in BLANCHED if c in stats['crop'].values]
    df = clean[clean['crop'].isin(top_crops)].copy()

    if 'year_month' not in df.columns:
        print('[WARN] year_month 欄位不存在，跳過熱圖')
        return

    monthly = df.groupby(['crop', 'year_month'])['avg_price'].mean().reset_index()
    base    = df.groupby('crop')['avg_price'].mean()
    monthly['base'] = monthly['crop'].map(base)
    monthly['pct']  = (monthly['avg_price'] - monthly['base']) / monthly['base'] * 100

    pivot = monthly.pivot(index='crop', columns='year_month', values='pct')
    pivot = pivot.reindex(top_crops).dropna(how='all')
    col_labels = [c[2:] for c in pivot.columns]
    row_labels  = [strip_code(c) for c in pivot.index]

    # 色階：深灰（便宜）→ 米白（均值）→ 深綠（貴）
    colorscale = [
        [0.0, C_GRAY_700],
        [0.3, C_GRAY_300],
        [0.5, '#F9F9F9'],
        [0.7, C_GREEN_PASTEL],
        [1.0, C_GREEN_DARK],
    ]

    hover_text = []
    for i, crop in enumerate(pivot.index):
        row_hover = []
        for j, col in enumerate(pivot.columns):
            val = pivot.values[i, j]
            if np.isnan(val):
                row_hover.append(f'{strip_code(crop)}<br>{col}<br>無資料')
            else:
                sign = '+' if val >= 0 else ''
                row_hover.append(f'{strip_code(crop)}<br>{col}<br>{sign}{val:.1f}%')
        hover_text.append(row_hover)

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=col_labels,
        y=row_labels,
        colorscale=colorscale,
        zmid=0, zmin=-60, zmax=60,
        text=hover_text,
        hovertemplate='%{text}<extra></extra>',
        colorbar=dict(
            title=dict(text='漲跌幅（%）', side='right',
                       font=dict(size=12)),
            tickfont=dict(size=11),
            thickness=14, len=0.75,
        ),
    ))

    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(
            text=('大台北蔬菜批發市場：常見燙青菜月均價季節性漲跌熱圖<br>'
                  '<sup>顏色 = 相對全期均價漲跌幅（深綠偏貴、淺色偏便宜）</sup>'),
            font=dict(size=17, color=C_GRAY_900),
            x=0.02, xanchor='left',
        ),
        xaxis=dict(tickfont=dict(size=11), side='bottom', linecolor=C_GRAY_300),
        yaxis=dict(tickfont=dict(size=11), autorange='reversed',
                   linecolor=C_GRAY_300),
        height=520,
        margin=dict(l=130, r=80, t=90, b=70),
    )
    save_html(fig, 'heatmap_seasonal.html')


# ── 圖四：CV 年際比較橫條圖 ──────────────────────────────────────────────────
def chart_cv_bar(stats):
    """Y1/Y2 CV 並排，availability=1.0 中 CV 最低前 20 名，由低到高，燙青菜紅色"""
    pool = stats[stats['availability'] >= 1.0].copy()
    pool['cv_avg'] = pool[['price_cv_y1', 'price_cv_y2']].mean(axis=1)
    top = pool.sort_values('cv_avg').head(TOP_HEATMAP).copy()
    labels = [strip_code(c) for c in top['crop']]
    is_bl  = top['crop'].isin(BLANCHED)

    colors_y1 = blanched_colors(top['crop'], C_BLANCHED,   C_GRAY_700)
    colors_y2 = blanched_colors(top['crop'], C_GREEN_PASTEL, C_GRAY_400)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=labels, x=top['price_cv_y1'],
        orientation='h', name='第一年 CV',
        marker=dict(color=colors_y1, opacity=0.85),
        customdata=top[['crop', 'price_cv_y1']].values,
        hovertemplate='<b>%{customdata[0]}</b><br>第一年 CV：%{x:.3f}<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        y=labels, x=top['price_cv_y2'],
        orientation='h', name='第二年 CV',
        marker=dict(color=colors_y2, opacity=0.85),
        customdata=top[['crop', 'price_cv_y2']].values,
        hovertemplate='<b>%{customdata[0]}</b><br>第二年 CV：%{x:.3f}<extra></extra>',
    ))

    if 'price_spread_ratio' in top.columns and top['price_spread_ratio'].notna().any():
        fig.add_trace(go.Scatter(
            x=top['price_spread_ratio'], y=labels,
            mode='markers',
            marker=dict(symbol='diamond', size=8, color=C_GREEN_DARK,
                        line=dict(width=1, color='white')),
            name='上下價差率',
            xaxis='x2',
            customdata=top[['crop', 'price_spread_ratio']].values,
            hovertemplate='<b>%{customdata[0]}</b><br>上下價差率：%{x:.3f}<extra></extra>',
        ))

    fig.update_layout(
        **BASE_LAYOUT,
        title=dict(
            text=('大台北蔬菜批發市場：年際價格穩定性比較<br>'
                  '<sup>全年無間斷供貨品項中 CV 最低 20 種｜CV 由低到高｜◆ 上下價差率（上軸）'
                  '｜綠色為常見燙青菜</sup>'),
            font=dict(size=17, color=C_GRAY_900),
            x=0.02, xanchor='left',
        ),
        barmode='group',
        xaxis=dict(title='CV（越低越穩定）', **XAXIS_STYLE),
        xaxis2=dict(
            title='上下價差率', overlaying='x', side='top',
            showgrid=False, linecolor=C_GRAY_300, color=C_GRAY_600,
        ),
        yaxis=dict(tickfont=dict(size=11), **YAXIS_STYLE),
        legend=dict(
            x=0.98, y=0.02, xanchor='right', yanchor='bottom',
            bgcolor='rgba(255,255,255,0.85)',
            bordercolor=C_GRAY_300, borderwidth=1,
        ),
        height=560,
        margin=dict(l=130, r=40, t=90, b=60),
    )
    save_html(fig, 'bar_price_cv.html')


# ── 主程式 ───────────────────────────────────────────────────────────────────
def main():
    os.makedirs(CHARTS_DIR, exist_ok=True)

    stats = pd.read_csv(STATS_FILE, encoding='utf-8-sig')
    clean = pd.read_csv(CLEAN_FILE, encoding='utf-8-sig', low_memory=False)
    print(f'stats: {len(stats)} items  clean: {len(clean):,} rows')

    chart_scatter(stats)
    chart_price_bar(stats)
    chart_heatmap(stats, clean)
    chart_cv_bar(stats)

    print(f'\n[DONE] 4 HTML charts saved to {CHARTS_DIR}')


if __name__ == '__main__':
    main()
