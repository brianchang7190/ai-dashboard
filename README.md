# 美股 AI 板块监测 Dashboard

单文件 Web Dashboard，监测美股 AI 板块（芯片 / 云基础设施 / 应用软件）的关键行情指标。

## 快速开始

### 方式 1：Mock 数据模式（无需 API Key）

直接用浏览器打开 `index.html` 即可看到效果，数据为模拟数据。

### 方式 2：接入真实 Alpha Vantage API

#### 2.1 申请 API Key

1. 访问 [alphavantage.co](https://www.alphavantage.co/support/#api-key)
2. 填写邮箱，免费获取 API Key
3. 免费额度：5 次请求/分钟，500 次/天

#### 2.2 部署 Vercel 代理（推荐）

```bash
# 安装 Vercel CLI
npm i -g vercel

# 在项目目录执行
cd ai-dashboard
vercel

# 设置环境变量
# 在 Vercel Dashboard → Settings → Environment Variables
# 添加: ALPHA_VANTAGE_API_KEY = 你的Key
```

部署后，将 `index.html` 中的：
```js
const USE_MOCK = true;
```
改为：
```js
const USE_MOCK = false;
```

#### 2.3 直接用浏览器打开（不推荐，Key 会暴露）

将 `index.html` 中的 `AV_API_KEY` 设为你的 Key，`USE_MOCK` 设为 `false`。

> ⚠️ 此方式会让 API Key 暴露在前端代码中，仅建议临时演示使用。

## 功能说明

| 功能 | 说明 |
|------|------|
| 赛道看板 | 3 个赛道（芯片/云基建/应用软件），可折叠，每赛道 4 只标的 |
| 标的卡片 | 显示代码、名称、最新价、涨跌幅、成交量条 |
| K 线图 | Canvas 手绘日线蜡烛图 + 成交量柱，支持 30/60/90 日切换，鼠标悬停查看 OHLC |
| 赛道对比 | 右侧面板，按平均涨跌幅排序，显示涨跌家数 |
| 刷新 | 手动刷新按钮（15s 防抖），快捷键 `Ctrl+R` |
| 缓存 | localStorage 缓存（盘中 5 分钟/盘后 30 分钟有效期） |
| 响应式 | 桌面三栏 → 平板两栏 → 手机单栏 |

## 覆盖标的

| 赛道 | 标的 |
|------|------|
| 🔴 AI 芯片 / 半导体 | NVDA, AMD, AVGO, TSM |
| ☁️ 云基础设施 | MSFT, AMZN, GOOGL, ORCL |
| 💼 AI 应用软件 | CRM, PLTR, SNOW, CRWD |

## 扩展赛道（代码中已预留注释）

- 🧠 大模型 / 平台层：META, AAPL 等
- 📊 数据分析 / 大数据：ESTC, CFLT, DDOG 等
- 🔒 AI 网络安全：PANW, ZS, NET, S 等
- 🤖 机器人 / 自动驾驶：TSLA, ISRG, MBLY 等
- 💰 金融科技 / 消费 AI：SQ, PYPL, SOFI, DUOL, SHOP 等

取消 `index.html` 中对应注释块并加入 `SECTORS` 即可激活。

## 技术栈

- 纯 HTML + CSS + JS（零 npm 依赖，零框架）
- Canvas API 手绘 K 线图
- Vercel Serverless Functions（可选代理）
- Alpha Vantage 免费 API

## 文件结构

```
ai-dashboard/
├── index.html    ← 主页面（HTML+CSS+JS 全部内联）
├── api/
│   └── stock.js  ← Vercel Serverless 代理函数
└── README.md
```
