"""
embed_charts.py
將 charts/ 資料夾中的三張 chart HTML 直接內嵌進 REPORT.html，
讓報告無需依賴外部 chart 檔案，只要有網路即可透過 CDN 載入 Plotly。
"""

import re, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(BASE_DIR, '..', 'REPORT.html')
CHARTS_DIR  = os.path.join(BASE_DIR, '..', 'charts')

CHART_FILES = [
    ('charts/chart_01_industry.html', 'chart_01_industry.html'),
    ('charts/chart_02_pct_bar.html',  'chart_02_pct_bar.html'),
    ('charts/chart_03_tfidf_heatmap.html', 'chart_03_tfidf_heatmap.html'),
]

CDN_TAG = '<script charset="utf-8" src="https://cdn.plot.ly/plotly-3.5.0.min.js"'

def extract_body(chart_html: str) -> str:
    """從 chart HTML 擷取需要內嵌的部分：移除 <html>/<head>/<body> 包裝與 CDN script tag。"""
    # 取出 <body>...</body> 內容
    body_match = re.search(r'<body>(.*?)</body>', chart_html, re.DOTALL)
    if not body_match:
        return chart_html
    body = body_match.group(1)

    # 移除 CDN <script ... src="https://cdn.plot.ly/..."> ... </script>
    # Plotly 的 CDN script 是 self-closing 或有 integrity，用寬鬆 regex 去掉
    body = re.sub(r'<script[^>]+cdn\.plot\.ly[^>]*>\s*</script>', '', body, flags=re.DOTALL)
    body = re.sub(r'<script[^>]+cdn\.plot\.ly[^>]*/>', '', body, flags=re.DOTALL)

    # 移除最外層的 <div>...</div> 包裝（Plotly 多包一層空 div）
    body = body.strip()
    if body.startswith('<div>') and body.endswith('</div>'):
        body = body[5:-6].strip()

    return body.strip()

# ── 讀取 REPORT.html ──────────────────────────────────────────────────────────
with open(REPORT_PATH, encoding='utf-8') as f:
    report = f.read()

# ── 確保 head 有 Plotly CDN（只加一次）─────────────────────────────────────
plotly_cdn_head = (
    '  <script src="https://cdn.plot.ly/plotly-3.5.0.min.js" '
    'charset="utf-8" crossorigin="anonymous"></script>\n'
)
if 'cdn.plot.ly' not in report:
    report = report.replace('</head>', plotly_cdn_head + '</head>')
    print('  ✓ 已在 <head> 加入 Plotly CDN')
else:
    print('  ✓ Plotly CDN 已存在於 <head>')

# ── 逐一替換 iframe → 內嵌 chart ─────────────────────────────────────────────
for iframe_src, chart_filename in CHART_FILES:
    chart_path = os.path.join(CHARTS_DIR, chart_filename)
    if not os.path.exists(chart_path):
        print(f'  ⚠ 找不到 {chart_path}，略過')
        continue

    with open(chart_path, encoding='utf-8') as f:
        chart_html = f.read()

    body_content = extract_body(chart_html)

    # 找出對應的 <div class="chart-wrapper">...<iframe src="charts/xxx">...</iframe></div>
    pattern = (
        r'(<div class="chart-wrapper">\s*)'
        r'(<iframe[^>]+src="' + re.escape(iframe_src) + r'"[^>]*></iframe>)'
        r'(\s*</div>)'
    )
    _body = body_content  # capture in closure
    def _repl(m):
        return m.group(1) + _body + m.group(3)
    new_report, count = re.subn(pattern, _repl, report, flags=re.DOTALL)

    if count == 0:
        print(f'  ⚠ 找不到 iframe src="{iframe_src}"，略過')
    else:
        report = new_report
        print(f'  ✓ 已內嵌 {chart_filename}')

# ── 寫回 REPORT.html ──────────────────────────────────────────────────────────
with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    f.write(report)

print('\n✅ 完成！REPORT.html 現已為獨立報告，不需要 charts/ 資料夾。')
