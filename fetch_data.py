"""GitHub Actions 数据抓取 — Quote(腾讯) + K线(Yahoo) + 新闻(RSS)"""
import urllib.request, json, re, time, ssl

SECTORS = {
    "chip":  ["NVDA","AMD","AVGO","TSM"],
    "cloud": ["MSFT","AMZN","GOOGL","ORCL"],
    "app":   ["CRM","PLTR","SNOW","CRWD"],
    "cyber": ["PANW","ZS","NET","S"],
}

all_symbols = []
for sec in SECTORS.values():
    all_symbols.extend(sec)

# ====== Quote: 腾讯财经 ======
print("Fetching quotes from Tencent...")
codes = ','.join(f'us{s}' for s in all_symbols)
try:
    req = urllib.request.Request(f'https://sqt.gtimg.cn/utf8/q={codes}', headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        text = r.read().decode('utf-8')
except Exception as e:
    print(f'Tencent failed: {e}'); exit(1)

quotes = {}
for m in re.finditer(r'v_us(\w+)="([^"]*)"', text):
    sym = m.group(1).upper()
    f = m.group(2).split('~')
    if len(f) < 35: continue
    price = float(f[3]) if f[3] else 0
    prev_close = float(f[4]) if f[4] else price
    change_pct = float(f[32]) if f[32] else 0
    volume = int(f[6]) if f[6] else 0
    if not price: continue
    quotes[sym] = {
        'symbol': sym, 'price': price, 'prevClose': prev_close,
        'change': round(price - prev_close, 2), 'changePercent': round(change_pct, 2),
        'volume': volume,
    }
print(f'  Quotes: {len(quotes)}')

# ====== K-line: Yahoo Finance ======
print("Fetching K-lines from Yahoo Finance...")
klines = {}
ctx = ssl.create_default_context()
for sym in all_symbols:
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=3mo&interval=1d'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'})
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            data = json.loads(r.read().decode())
        result = data['chart']['result'][0]
        ts = result['timestamp']
        q = result['indicators']['quote'][0]
        daily = []
        for i in range(len(ts)):
            o, h, l, c, v = q['open'][i], q['high'][i], q['low'][i], q['close'][i], q['volume'][i]
            if None in (o, h, l, c): continue
            from datetime import datetime
            daily.append({
                'date': datetime.utcfromtimestamp(ts[i]).strftime('%Y-%m-%d'),
                'open': o, 'high': h, 'low': l, 'close': c, 'volume': v or 0,
            })
        if daily:
            klines[sym] = daily
            print(f'  {sym}: {len(daily)} pts')
    except Exception as e:
        print(f'  {sym}: FAIL ({e})')
    time.sleep(0.3) # 礼貌间隔

# ====== News: Yahoo RSS ======
print("Fetching news...")
news = []
try:
    syms = 'NVDA,AMD,AVGO,MSFT,AMZN,GOOGL,CRM,PLTR,CRWD,PANW'
    url = f'https://feeds.finance.yahoo.com/rss/2.0/headline?s={syms}&region=US&lang=en-US'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        xml = r.read().decode()
    for item_m in re.finditer(r'<item>(.*?)</item>', xml, re.DOTALL):
        item = item_m.group(1)
        t = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', item)
        l = re.search(r'<link>(.*?)</link>', item)
        d = re.search(r'<pubDate>(.*?)</pubDate>', item)
        if t and l:
            lo = t.group(1).lower()
            bull = bool(re.search(r'\b(beat|surge|jump|rise|gain|bull|upgrade|rally|record|strong|growth|breakthrough)\b', lo))
            bear = bool(re.search(r'\b(miss|drop|fall|decline|bear|downgrade|sell|crash|weak|loss|negative|warn|cut)\b', lo))
            sentiment = 'Bullish' if bull and not bear else ('Bearish' if bear and not bull else 'neutral')
            news.append({'title': t.group(1), 'link': l.group(1), 'pubDate': (d.group(1) if d else '')[:11], 'sentiment': sentiment})
    print(f'  News: {len(news)} articles')
except Exception as e:
    print(f'  News: FAIL ({e})')

# ====== 输出 ======
output = {
    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'quotes': quotes,
    'klines': klines,
    'news': news[:15],
}

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False)

print(f'\nDone: {len(quotes)} quotes + {len(klines)} klines + {len(news)} news → data.json')
