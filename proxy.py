"""
美股 AI 板块监测 — 本地代理 (国内优化版)
数据源: 新浪财经 + 东方财富
启动: python3 proxy.py → http://localhost:8765
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request, urllib.parse, json, re, os, time

PORT = 8765

# ====== 新浪财经 — 实时报价 ======
def fetch_sina_quotes(symbols):
    """批量获取美股实时报价"""
    codes = ','.join(f'gb_{s.lower()}' for s in symbols)
    url = f'https://hq.sinajs.cn/list={codes}'
    try:
        req = urllib.request.Request(url, headers={'Referer': 'https://finance.sina.com.cn'})
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode('gbk')
    except Exception as e:
        print(f'[SINA ERR] {e}')
        return {}

    result = {}
    for line in raw.strip().split('\n'):
        if not line.strip(): continue
        # var hq_str_gb_nvda="name,price,change_pct,..."
        m = re.match(r'var hq_str_gb_(\w+)="(.*)"', line)
        if not m: continue
        sym = m.group(1).upper()
        fields = m.group(2).split(',')
        if len(fields) < 10: continue
        result[sym] = {
            'symbol': sym,
            'name': fields[0],
            'price': float(fields[1]) if fields[1] else 0,
            'changePercent': float(fields[2]) if fields[2] else 0,
            'volume': int(float(fields[10])) if len(fields) > 10 and fields[10] else 0,
            'high': float(fields[6]) if len(fields) > 6 and fields[6] else 0,
            'low': float(fields[7]) if len(fields) > 7 and fields[7] else 0,
            'prevClose': float(fields[26]) if len(fields) > 26 and fields[26] else 0,
        }
        # 修正 prevClose
        if result[sym]['prevClose'] == 0 and result[sym]['price'] and result[sym]['changePercent']:
            chg = result[sym]['changePercent']
            result[sym]['prevClose'] = round(result[sym]['price'] / (1 + chg/100), 2)
    return result

# ====== K线数据 (多源尝试) ======
def fetch_kline(symbol, days=90):
    """获取美股日线，依次尝试多个数据源"""
    # 源1: 东方财富
    k = _try_eastmoney(symbol, days)
    if k: return k
    # 源2: Yahoo Finance (可能被墙，但在代理服务器上也许可访问)
    k = _try_yahoo(symbol, days)
    if k: return k
    return []

def _try_eastmoney(symbol, days):
    try:
        url = (f'https://push2his.eastmoney.com/api/qt/stock/kline/get?'
               f'secid=105.{symbol}&fields1=f1,f2,f3,f4,f5,f6'
               f'&fields2=f51,f52,f53,f54,f55,f56'
               f'&klt=101&fqt=0&end=20500101&lmt={days}')
        req = urllib.request.Request(url, headers={
            'Referer': 'https://quote.eastmoney.com/',
            'User-Agent': 'Mozilla/5.0'
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        klines = data.get('data', {}).get('klines', []) if data.get('data') else []
        if not klines: return []
        daily = []
        for line in klines:
            parts = line.split(',')
            if len(parts) < 6: continue
            daily.append({
                'date': parts[0], 'open': float(parts[1]),
                'close': float(parts[2]), 'high': float(parts[3]),
                'low': float(parts[4]), 'volume': int(float(parts[5])),
            })
        return daily
    except: return []

def _try_yahoo(symbol, days):
    try:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=3mo&interval=1d'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=15) as r:
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
        return daily
    except: return []

# ====== HTTP 服务器 ======
class Proxy(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        qs = self.path.split('?', 1)[1] if '?' in self.path else ''
        params = dict(p.split('=', 1) for p in qs.split('&') if '=' in p)

        if path == '/api/stock':
            sym = params.get('symbol', '').upper()
            if not sym:
                self.reply({'error': 'missing symbol'}, 400); return

            # 并行获取 quote + kline
            quotes = fetch_sina_quotes([sym])
            q = quotes.get(sym)
            daily = fetch_kline(sym)

            if not q:
                self.reply({'error': f'no data for {sym}'}, 502); return

            # 构造与 Yahoo Finance 兼容的响应格式
            self.reply({
                'chart': {
                    'result': [{
                        'meta': {
                            'symbol': sym,
                            'regularMarketPrice': q['price'],
                            'chartPreviousClose': q['prevClose'],
                            'previousClose': q['prevClose'],
                            'regularMarketVolume': q['volume'],
                            'fiftyTwoWeekHigh': None,
                            'fiftyTwoWeekLow': None,
                        },
                        'timestamp': [
                            int(time.mktime(time.strptime(d['date'], '%Y-%m-%d')))
                            for d in daily
                        ],
                        'indicators': {
                            'quote': [{
                                'open': [d['open'] for d in daily],
                                'high': [d['high'] for d in daily],
                                'low': [d['low'] for d in daily],
                                'close': [d['close'] for d in daily],
                                'volume': [d['volume'] for d in daily],
                            }]
                        }
                    }]
                }
            })

        elif path == '/api/news':
            # 新闻: 尝试 Yahoo RSS, 失败返回空
            try:
                syms = 'NVDA,AMD,AVGO,MSFT,AMZN,GOOGL,CRM,PLTR,CRWD,PANW'
                url = f'https://feeds.finance.yahoo.com/rss/2.0/headline?s={syms}&region=US&lang=en-US'
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as r:
                    xml = r.read().decode()
                items = self.parse_rss(xml)
                self.reply({'items': items})
            except Exception as e:
                print(f'[NEWS ERR] {e}')
                self.reply({'items': []})

        elif path == '/' or path == '/index.html':
            here = os.path.dirname(os.path.abspath(__file__))
            try:
                with open(os.path.join(here, 'index.html'), 'rb') as f:
                    self.send_response(200); self.cors()
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers(); self.wfile.write(f.read())
            except FileNotFoundError:
                self.reply({'error': 'index.html missing'}, 404)

        else:
            self.reply({'error': 'not found'}, 404)

    def do_OPTIONS(self):
        self.send_response(200); self.cors(); self.end_headers()

    def cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')

    def reply(self, data, code=200):
        self.send_response(code); self.cors()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def parse_rss(self, xml):
        items = []
        for m in re.finditer(r'<item>(.*?)</item>', xml, re.DOTALL):
            item = m.group(1)
            t = re.search(r'<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>', item)
            l = re.search(r'<link>(.*?)</link>', item)
            d = re.search(r'<pubDate>(.*?)</pubDate>', item)
            if t and l:
                lo = t.group(1).lower()
                bull = bool(re.search(r'\b(beat|surge|jump|rise|gain|bull|upgrade|rally|record|strong|growth|breakthrough)\b', lo))
                bear = bool(re.search(r'\b(miss|drop|fall|decline|bear|downgrade|sell|crash|weak|loss|negative|warn|cut)\b', lo))
                s = 'Bullish' if bull and not bear else ('Bearish' if bear and not bull else 'neutral')
                items.append({'title':t.group(1), 'link':l.group(1), 'pubDate':(d.group(1) if d else '')[:11], 'sentiment':s})
        return items[:15]

    def log_message(self, fmt, *args):
        print(f'[{self.log_date_time_string()}] {args[0]}')

if __name__ == '__main__':
    print(f'◆ 代理已启动 → http://localhost:{PORT}')
    HTTPServer(('0.0.0.0', PORT), Proxy).serve_forever()
