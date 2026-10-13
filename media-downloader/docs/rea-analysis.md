# 用 REA 分析 dyxhsdownloader.com（2026-10-13）

## 工具

[REA — Reverse Engineer Anything](https://github.com/morluto/rea)（MIT，本次用 `rea-agents` 6.4.0）。它能分析原生程序、JS/Electron 应用和网站，本次用的是不需要额外引擎的静态 JS 分析：

```bash
mkdir sitedump && cd sitedump
curl -sS https://dyxhsdownloader.com/ -o index.html
curl -sS https://dyxhsdownloader.com/assets/index-<hash>.js -o index.js   # 首页 <script src> 里的打包文件
npx -y rea-agents@latest analyze-javascript-application "$(pwd)" --format json > rea.json
```

## REA 给出的结构

| 类型 | 发现 | 位置（index.js） |
|---|---|---|
| 网络端点 | `fetch("/api/parse")`，唯一的业务接口 | 40:102447 |
| 前端路由 | `/douyin` `/xiaohongshu` `/kuaishou` `/bilibili` `/weibo` `/tiktok` `/instagram` `/twitter` `/reddit` | 40:61920–62283 |
| 页面参数 | `url` / `text` / `q`（从地址栏带入要解析的链接） | 40:104332–104361 |

顺着 REA 标出的位置读源码，得到：

1. **调用方式**：`POST /api/parse`，body 为 `{url, originalUrl, userInput}`，请求头带 `X-Turnstile-Token`（Cloudflare 人机验证）。没有验证返回 403“安全验证未通过”；限流时返回 429/503 + `Retry-After`，前端显示冷却倒计时。
2. **解析全部在服务端**：前端只做链接抠取、平台判断、展示和下载按钮，抖音/小红书等的去水印逻辑不在前端代码里，静态分析拿不到。
3. **链接识别规则**（`Bc` 和 `$c` 两个函数）：已原样移植到 `mediadl/linkparse.py`，包括 Reddit 的严格帖子链接正则、微博 `t.cn` 短链等。
4. **结果页能力**（界面文案字典）：下载无水印视频、备用源、封面、背景音频、全选/已选、打包下载全部、Live 动图及动图 ZIP；元信息展示作者、描述、时长、大小、格式、分辨率、水印状态（已去除/尽力去除/未知/保留）；提示 “CDN 链接约 5 分钟过期”。
5. **错误分类**（`Eh` 函数）：不支持平台 / 私密或已删除 / 风控限流（含 B 站 -412）/ 超时 / 网络 / 上游错误。
6. 其它：最近 8 条解析记录存 localStorage；接了 Datadog RUM 统计解析成功率。

## 结论和取舍

- 网站的核心能力在它服务端，“逆向”到的只有接口契约。直接在本地调用它的 `/api/parse` 需要过它的 Turnstile 验证，这既不稳定也不该做，所以本地版**不依赖这个网站**。
- 本地版按上面的功能清单、识别规则和字段设计，用各平台的公开页面数据（抖音分享页、小红书笔记页、快手分享页/GraphQL、FixTweet、Reddit JSON）和 yt-dlp 自己实现解析。
- 平台侧的风控（快手滑块验证、小红书 xsec_token、抖音偶发不返回数据）照实处理：给出明确提示，需要时用户自己提供 cookies，不绕过验证码。
