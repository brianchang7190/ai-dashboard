// Deno Deploy 代理 — 支持单个和批量查询
// GET /api/stock?symbol=NVDA       → 单只
// GET /api/stock?symbol=NVDA,AMD   → 批量 (一次返回全部)

Deno.serve(async (req) => {
  const url = new URL(req.url);
  const path = url.pathname;
  const symbol = url.searchParams.get("symbol") || "";

  const cors = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
  };

  if (req.method === "OPTIONS") {
    return new Response(null, { status: 200, headers: cors });
  }

  // /api/stock?symbol=NVDA 或 ?symbol=NVDA,AMD,AVGO
  if (path === "/api/stock" && symbol) {
    const symbols = symbol.split(",").filter(s => /^[A-Za-z0-9.]+$/.test(s));
    if (!symbols.length) return json({ error: "invalid" }, 400, cors);

    try {
      // 并行请求所有标的
      const results = {};
      const fetches = symbols.map(async (sym) => {
        try {
          const yahooUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(sym)}?range=1d&interval=1d`;
          const resp = await fetch(yahooUrl, { headers: { "User-Agent": "Mozilla/5.0" } });
          if (resp.ok) {
            const data = await resp.json();
            const meta = data?.chart?.result?.[0]?.meta;
            if (meta?.regularMarketPrice) {
              results[sym] = { price: meta.regularMarketPrice, volume: meta.regularMarketVolume || 0 };
            }
          }
        } catch (_) { /* skip */ }
      });
      await Promise.all(fetches);
      return json(results, 200, cors);
    } catch (e) {
      return json({ error: e.message }, 502, cors);
    }
  }

  // /api/news
  if (path === "/api/news") {
    try {
      const syms = "NVDA,AMD,AVGO,MSFT,AMZN,GOOGL,CRM,PLTR,CRWD,PANW";
      const rssUrl = `https://feeds.finance.yahoo.com/rss/2.0/headline?s=${syms}&region=US&lang=en-US`;
      const resp = await fetch(rssUrl, { headers: { "User-Agent": "Mozilla/5.0" } });
      const xml = await resp.text();
      const items = [];
      const re = /<item>([\s\S]*?)<\/item>/g;
      let m;
      while ((m = re.exec(xml)) !== null) {
        const item = m[1];
        const t = (item.match(/<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?<\/title>/) || [])[1] || "";
        const l = (item.match(/<link>(.*?)<\/link>/) || [])[1] || "#";
        if (t) items.push({ title: t, link: l, sentiment: "neutral" });
      }
      return json({ items: items.slice(0, 15) }, 200, cors);
    } catch (_) {
      return json({ items: [] }, 200, cors);
    }
  }

  return new Response("AI Dashboard Proxy OK", { headers: { ...cors, "Content-Type": "text/plain" } });
});

function json(data, status, cors) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...cors, "Content-Type": "application/json" },
  });
}
