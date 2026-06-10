# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

美股 AI 板块监测 Dashboard — 纯前端单页应用，16 只美股按 4 赛道分组，展示实时报价、K线、成交量、技术指标、新闻。

线上地址：`https://brianchang7190.github.io/ai-dashboard/`

## 架构

```
Yahoo Finance API ← Deno Deploy 代理 ← 浏览器 (点击 Refresh, 实时)
Yahoo Finance API ← GitHub Actions ← data.json ← 浏览器 (自动加载, ~1分延迟)
                                         ↑
                                GitHub Pages 托管
```

- **index.html**：整个前端，HTML + CSS + JS 全部内联（零依赖）
- **fetch_data.py**：GitHub Actions 定时执行，抓取 Quote + K线 + 新闻 → data.json
- **proxy_deno.js**：Deno Deploy 代理，转发 Yahoo Finance 请求（解决 CORS）
- **proxy.py**：本地开发用 Python 代理（备选）

## 数据流

```
页面加载 → fetch('data.json') → 渲染基础数据
   ↓ (如果 LIVE_PROXY 已配置)
点 Refresh → fetch(LIVE_PROXY + '/api/stock?symbol=NVDA,AMD,...') → 实时覆盖报价
   ↓ (如果 LIVE_PROXY 为空)
          → 只读 data.json，不尝试实时
```

3 种模式自动切换：
- `file://` → Mock 模拟数据
- `https://` + `LIVE_PROXY` 已配 → data.json + Deno 代理实时覆盖
- `https://` + `LIVE_PROXY` 为空 → 纯 data.json

模式判断在 `IS_FILE` / `LIVE_PROXY` 两个变量，不可再用 `USE_MOCK`（已移除）。

## 赛道与标的

定义在 JS 的 `SECTORS` 对象中，结构：
```js
{ id, numeral, name, tag, stocks: [{symbol, name, basePrice}] }
```

4 赛道：chip / cloud / app / cyber。预留 5 赛道（foundation/data/cyber/robotics/fintech）在注释中。

## 关键文件

| 文件 | 用途 |
|------|------|
| `index.html` | 唯一交付物，~1300 行，三部分：CSS 变量/样式、HTML 结构、JS 逻辑 |
| `fetch_data.py` | GitHub Actions 数据抓取，输出 data.json |
| `.github/workflows/fetch-data.yml` | 每 5 分钟触发，循环 5 次（~1 分钟间隔） |
| `proxy_deno.js` | Deno Deploy 代理，支持批量 `?symbol=A,B,C` |
| `data.json` | Actions 自动生成，包含 quotes / klines / news |

## 开发

- 本地预览：双击 `index.html`（Mock 模式）
- 本地实时：`python3 proxy.py` → 打开 `http://localhost:8765`
- 推送到 GitHub Pages 即自动部署

## 技术指标计算

- MA20 / RSI14 / 量比（V×ratio）：`computeIndicators(daily)` 函数，纯前端计算
- K线图：Canvas 手绘，蜡烛图 + MA20 叠加线 + 成交量柱 + 十字光标 tooltip
- 资金流向：涨跌%方向 × 成交量颜色（绿=流入，红=流出）
