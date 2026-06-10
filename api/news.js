/**
 * Vercel Serverless Function — Yahoo Finance RSS → JSON 新闻代理
 *
 * GET /api/news
 * 返回 AI 相关美股的最新新闻（标题、链接、来源、时间）
 */

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=120');

  if (req.method === 'OPTIONS') return res.status(200).end();

  // 多只 AI 龙头标的的 RSS
  const symbols = ['NVDA','AMD','AVGO','MSFT','AMZN','GOOGL','CRM','PLTR','CRWD','PANW'];
  const rssUrl = `https://feeds.finance.yahoo.com/rss/2.0/headline?s=${symbols.join(',')}&region=US&lang=en-US`;

  try {
    const resp = await fetch(rssUrl);
    if (!resp.ok) return res.status(502).json({ error: 'RSS fetch failed' });

    const xml = await resp.text();

    // 简易 RSS 解析
    const items = [];
    const itemRegex = /<item>([\s\S]*?)<\/item>/g;
    let match;

    while ((match = itemRegex.exec(xml)) !== null) {
      const item = match[1];
      const title = (item.match(/<title><!\[CDATA\[(.*?)\]\]><\/title>/) || item.match(/<title>(.*?)<\/title>/))?.[1] || '';
      const link = (item.match(/<link>(.*?)<\/link>/))?.[1] || '#';
      const pubDate = (item.match(/<pubDate>(.*?)<\/pubDate>/))?.[1] || '';
      const source = (item.match(/<source>(.*?)<\/source>/))?.[1] || 'Yahoo Finance';
      const desc = (item.match(/<description><!\[CDATA\[(.*?)\]\]><\/description>/) || item.match(/<description>(.*?)<\/description>/))?.[1] || '';

      if (title && link) {
        // 简单情绪判断
        const lower = (title + ' ' + desc).toLowerCase();
        const bullish = /\b(beat|surge|jump|rise|gain|bull|upgrade|outperform|buy|rally|record|strong|growth|positive|breakthrough)\b/;
        const bearish = /\b(miss|drop|fall|decline|bear|downgrade|underperform|sell|crash|weak|loss|negative|risk|concern|warn|cut)\b/;
        let sentiment = 'neutral';
        const bullMatch = bullish.test(lower);
        const bearMatch = bearish.test(lower);
        if (bullMatch && !bearMatch) sentiment = 'Bullish';
        else if (bearMatch && !bullMatch) sentiment = 'Bearish';
        else if (bullMatch && bearMatch) sentiment = 'Mixed';

        items.push({ title, link, pubDate, source, sentiment });
      }
    }

    return res.status(200).json({ items: items.slice(0, 15) });
  } catch (err) {
    console.error('News proxy error:', err);
    return res.status(502).json({ error: '代理请求失败', detail: err.message });
  }
}
