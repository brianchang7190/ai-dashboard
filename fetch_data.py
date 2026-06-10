"""GitHub Actions 数据抓取 — 调腾讯财经 API 获取全部 AI 标的"""
import urllib.request, json, time

SECTORS = {
    "chip":  ["NVDA","AMD","AVGO","TSM"],
    "cloud": ["MSFT","AMZN","GOOGL","ORCL"],
    "app":   ["CRM","PLTR","SNOW","CRWD"],
    "cyber": ["PANW","ZS","NET","S"],
}

all_symbols = []
for sec in SECTORS.values():
    all_symbols.extend(sec)

# 腾讯财经批量查询
codes = ','.join(f'us{s}' for s in all_symbols)
url = f'https://sqt.gtimg.cn/utf8/q={codes}'

try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        text = r.read().decode('utf-8')
except Exception as e:
    print(f'Fetch failed: {e}')
    exit(1)

# 解析
import re
result = {}
for m in re.finditer(r'v_us(\w+)="([^"]*)"', text):
    sym = m.group(1).upper()
    f = m.group(2).split('~')
    if len(f) < 35: continue
    price = float(f[3]) if f[3] else 0
    prev_close = float(f[4]) if f[4] else price
    change_pct = float(f[32]) if f[32] else 0
    volume = int(f[6]) if f[6] else 0
    if not price: continue
    result[sym] = {
        'symbol': sym,
        'price': price,
        'prevClose': prev_close,
        'change': round(price - prev_close, 2),
        'changePercent': round(change_pct, 2),
        'volume': volume,
    }

output = {
    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'quotes': result,
}

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False)

print(f'OK: {len(result)} quotes → data.json')
for s, q in result.items():
    print(f'  {s}: ${q["price"]} ({q["changePercent"]:+.2f}%)')
