// Deno Deploy 代理 — 粘贴到 dash.deno.com Playground 直接部署
// 无需 import，使用 Deno 内置 API

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

  // /api/stock?symbol=NVDA
  if (path === "/api/stock" && symbol && /^[A-Za-z0-9.]+$/.test(symbol)) {
    try {
      const yahooUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=1d&interval=1d`;
      const resp = await fetch(yahooUrl, {
        headers: { "User-Agent": "Mozilla/5.0" },
      });
      const data = await resp.json();
      return new Response(JSON.stringify(data), {
        headers: { ...cors, "Content-Type": "application/json" },
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 502, headers: { ...cors, "Content-Type": "application/json" },
      });
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
      return new Response(JSON.stringify({ items: items.slice(0, 15) }), {
        headers: { ...cors, "Content-Type": "application/json" },
      });
    } catch (e) {
      return new Response(JSON.stringify({ items: [] }), {
        headers: { ...cors, "Content-Type": "application/json" },
      });
    }
  }

  return new Response("AI Dashboard Proxy OK", {
    headers: { ...cors, "Content-Type": "text/plain" },
  });
});
