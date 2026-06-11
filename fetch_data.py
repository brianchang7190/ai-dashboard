"""GitHub Actions 数据抓取 — 全部使用 Yahoo Finance (Quote + K线 + News)"""
import urllib.request, json, re, time, ssl
from datetime import datetime

SECTORS = {
    "chip":       ["NVDA","AMD","AVGO","TSM"],
    "cloud":      ["MSFT","AMZN","GOOGL","ORCL"],
    "app":        ["CRM","PLTR","SNOW","CRWD"],
    "cyber":      ["PANW","ZS","NET","S"],
    "foundation": ["META","AAPL","BBAI","AI"],
    "data":       ["DDOG","MDB","ESTC","DT"],
    "robotics":   ["TSLA","ISRG","MBLY","PATH"],
    "fintech":    ["SOFI","DUOL","SHOP","PYPL"],
}

all_symbols = []
for sec in SECTORS.values():
    all_symbols.extend(sec)

ctx = ssl.create_default_context()
quotes = {}
klines = {}

# ====== Quote + K-line: Yahoo Finance (一次请求同时返回) ======
print("Fetching quotes + K-lines from Yahoo Finance...")
for sym in all_symbols:
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=6mo&interval=1d'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            data = json.loads(r.read().decode())

        result = data['chart']['result'][0]
        meta = result['meta']
        ts = result['timestamp']
        q = result['indicators']['quote'][0]

        # K-line (先解析，后用倒数第二天 close 作为 prevClose)
        daily = []
        for i in range(len(ts)):
            o, h, l, c, v = q['open'][i], q['high'][i], q['low'][i], q['close'][i], q['volume'][i]
            if None in (o, h, l, c): continue
            daily.append({
                'date': datetime.utcfromtimestamp(ts[i]).strftime('%Y-%m-%d'),
                'open': o, 'high': h, 'low': l, 'close': c, 'volume': v or 0,
            })
        if daily:
            klines[sym] = daily

        # Quote: 用 K 线倒数第二天 close 作为前收盘价（而非 chartPreviousClose）
        price = meta.get('regularMarketPrice')
        prev = daily[-2]['close'] if len(daily) >= 2 else (meta.get('regularMarketPreviousClose') or price)
        if price and prev:
            chg = round(price - prev, 2)
            quotes[sym] = {
                'symbol': sym, 'price': price, 'prevClose': prev,
                'change': chg, 'changePercent': round(chg / prev * 100, 2),
                'volume': meta.get('regularMarketVolume', 0) or 0,
                'high52w': meta.get('fiftyTwoWeekHigh'), 'low52w': meta.get('fiftyTwoWeekLow'),
            }
        else:
            quotes[sym] = None

        print(f'  {sym}: ${price} ({quotes[sym]["changePercent"]:+.2f}%) | prevClose=${prev} | {len(daily)} pts')

    except Exception as e:
        print(f'  {sym}: FAIL ({e})')
        quotes[sym] = None

    time.sleep(0.3)

# 清理 None
quotes = {k: v for k, v in quotes.items() if v}

# ====== News: Yahoo Finance RSS ======
print("Fetching news from Yahoo Finance RSS...")
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
except Exception as e:
    print(f'  News FAIL ({e})')

# 去重
seen=set(); news2=[]
for n in news:
    if n['title'] not in seen: seen.add(n['title']); news2.append(n)
news=news2
print(f'  {len(news)} articles')

# ====== 输出 ======
output = {
    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'quotes': quotes,
    'klines': klines,
    'news': news[:20],
}

with open('data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False)

print(f'\n✅ {len(quotes)} quotes + {len(klines)} klines + {len(news)} news → data.json')
