/**
 * Vercel Serverless Function — Yahoo Finance 代理
 *
 * 调用方式：
 *   GET /api/stock?symbol=NVDA
 *
 * 返回 Yahoo Finance v8 chart API 原始 JSON
 */

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Cache-Control', 's-maxage=120, stale-while-revalidate=60');

  if (req.method === 'OPTIONS') return res.status(200).end();

  const { symbol } = req.query;
  if (!symbol) return res.status(400).json({ error: '缺少 symbol 参数' });

  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=3mo&interval=1d`;

  try {
    const resp = await fetch(url);
    if (!resp.ok) return res.status(resp.status).json({ error: `Yahoo Finance 返回 ${resp.status}` });
    const data = await resp.json();
    return res.status(200).json(data);
  } catch (err) {
    console.error('Proxy error:', err);
    return res.status(502).json({ error: '代理请求失败', detail: err.message });
  }
}
