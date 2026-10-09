---
name: staged-market-scrape
description: 用 Tavily 找、Apify 抓 Reddit/TikTok/Trends/YouTube/应用商店/X/Trustpilot 等数据和评论做市场调研；分阶段小样本验证质量再放量，每阶段交付 md 报告。
---

# 分阶段市场数据抓取（Tavily 找 + Apify 抓）

适用：产品前市场调研、竞品和用户痛点收集、需要从 Reddit / TikTok / Google Trends（以及 YouTube、Instagram、X、Amazon 评论等）拿数据和评论时。
核心原则：**先找后抓，小样本验证，逐级放量。** 每一阶段有预算上限和通过标准，不达标就停下来修，绝不一次花掉大额 API。每阶段都交付一份 md 报告（概况、数据质量、如何使用、待思考问题），不只给数据。
源码与更新：github.com/OliverOuyang/research-crawler（skills/staged-market-scrape、scripts/apify_stage.py、docs/）。

## 0. 准备（不花钱）

1. 确认凭证：Tavily 和 Apify 的 key 由环境注入（`APIFY_TOKEN` / `TAVILY_API_KEY` 环境变量，或代理为 api.apify.com、api.tavily.com 注入 Authorization）。**不要把 key 写进文件、命令输出或聊天。** 缺了就告诉用户去环境里加，不要让用户把 key 贴进聊天。
2. 把下面的 helper 存成会话临时目录里的 `apify_stage.py`（只用标准库）。
3. `python3 apify_stage.py whoami`：看套餐、本月已用金额和上限。把剩余额度当作总预算。**Apify 免费档下，多数付费 Actor 每次最多返回 10 条**（run 的 status message 会提示 “subscribe to a paid plan”），有的 Actor 直接拒绝免费用户（如 Amazon 评论）。S1 用免费档够了；S2 起建议升级 Starter，或把输入拆成多个小批次。
4. 跟用户确认（或按合理默认）调研问题：目标用户、品类、竞品、语言/地区、时间窗口。把它写成 3–8 个英文关键词 + 1 组“相关性正则”（例如 `note|notion|obsidian|goodnotes`），后面每阶段都用它测相关性。

## 1. 选 Actor（不花钱）

- 先用下方“已验证 Actor”表；没有覆盖的平台用 `apify_stage.py find "<platform> scraper"` 在商店里挑。
- 入选标准：近 30 天成功率 ≥ 95%、用户数多、最近 3 个月内更新过、**按条计费（pay-per-result/event）**而不是按月租。成功率低于 90% 的不用（例：官方 apify/google-trends-scraper 只有 57%）。
- `apify_stage.py schema <actor>` 读输入参数，确认：条数上限字段叫什么、是“每帖”还是“总数”、能否直接喂 URL。
- 记下单价，算出每阶段的预估花费，告诉用户。

## 2. 分阶段放量（每阶段都要过闸）

| 阶段 | 规模（每个源） | 单次预算上限 `--max-usd` | 目的 |
|---|---|---|---|
| S1 冒烟 | 10–20 条 | 0.2 | 跑通、看字段、看相关性 |
| S2 试点 | 100–200 条 | 1 | 验证质量标准、去噪比例、条数稳定 |
| S3 正式 | 达到样本量目标（定性 ≥ 200 有效条，比例结论 ≥ 400） | 按 S2 实际单价 × 1.3 | 出结论用 |
| S4 补充 | 只补缺口（某来源不足、某时间段缺失） | 按需 | 不重跑全量 |

每次 run 都带 `maxTotalChargeUsd`（helper 的 `--max-usd`）。部分 Actor 要求上限不低于某个值（实测 $0.45–$1），helper 会打印报错，按提示调高即可；它只是上限，实际按条计费。**下一阶段开始前，必须向用户报告上一阶段的结果和下一阶段的预估花费**；用户明确说过“自动跑完”才可连续执行。

### 闸门：每阶段跑完用 `apify_stage.py check` 检查，全部达标才放量
- 条数 ≥ 请求的 90%（否则记“部分失败”，查原因：分页、关键词太窄、Actor 单次上限）。
- 关键字段（id、时间、正文、互动数）缺失率 ≤ 5%；返回空数组、HTML 拦截页、error 字段都算失败。
- **相关性 ≥ 80%**（相关性正则命中，外加人工抽看 10 条）。不达标先改“找”的方式，不要加量。
- 去重后重复率 ≤ 5%；已删除/作者注销/广告/带外链的比例单独报告并剔除。
- 单价与预估偏差 ≤ 30%。

## 3. “找”和“抓”的分工（实测得出）

- **Reddit：不要用 Actor 的全站关键词搜索**，即使开 strictSearch 也会混入大量不相关热帖（实测 “note taking app” 返回 r/AmItheAsshole）。正确做法：先用 Tavily `/search`（`include_domains: ["reddit.com"]`，basic 深度省 credit）找帖子 URL，筛出含 `/comments/` 的链接，人工或用正则确认相关，再把 URL 列表交给 Actor 抓帖子 + 评论。也可以指定 subreddit。
- **TikTok：** 关键词搜索本身相关性好；评论用单独的评论 Actor，按视频 URL 串联，先挑互动高的视频。
- **Google Trends：** 一个关键词一条记录、包含整条曲线，成本可忽略；同一次请求里比较关键词，不要拼接多次请求的数值；剔除 `timeline_data.isPartial` 为 true 的点。
- **应用商店评论（App Store / Google Play）：** 按 App ID 抓，最便宜（约 $0.1/千条）。App Store 评论更长更具体；Google Play 大量“nice app”短评，要按 `HELPFULNESS` 排序或只取 1–3 星。
- **YouTube：** 先搜视频（加 `dateFilter` 控制时效），再挑评测/对比类视频抓热门评论；热门评论很多是玩笑，要按关键词筛，剔除 `authorIsChannelOwner=true` 的推广。
- **X：** 不加过滤会混入大量外语赠送和账号转卖。查询要带 `lang:en -filter:links` 和意图词，如 `<产品> (annoying OR wish OR bug OR switched OR hate)`。
- **Trustpilot：** 按 `source` 分开看，`BasicLink` 是商家邀请的评价，偏正面；`Organic` 偏负面。
- **Quora：** 搜索只给问题标题和回答数，且多为老问题，价值低；**Amazon 评论**抓取器免费档不可用。
- Tavily `/extract` 可以直接抽 Reddit 帖子正文和首屏评论做纯定性分析（无点赞数），在不需要量化时比 Actor 更省。

## 4. 已验证 Actor（2026-10 实测/商店数据，价格按 Free 档）

| 用途 | Actor | 价格 | 注意 |
|---|---|---|---|
| Reddit 帖子+评论（按 URL） | fatihtahta/reddit-scraper-search-fast | $1.49/千条 | 输入 `urls`、`scrapeComments`、`maxComments`（**每帖**上限）；有 score、num_comments、created_utc、is_deleted_or_removed |
| Reddit 评论多时更省 | automation-lab/reddit-scraper | 帖 $1.15/千、评论 $0.575/千 | 未实测，先 S1 冒烟 |
| TikTok 视频（关键词/话题） | apidojo/tiktok-scraper | $0.30/千条 | 输入 `keywords`、`maxItems`；免费档每次最多 10 条；字段 views/likes/comments/shares/bookmarks |
| TikTok 视频（更稳） | clockworks/tiktok-scraper | $3.70/千条 | 成功率 99% |
| TikTok 评论 | clockworks/tiktok-comments-scraper | $1.25/千条 | 输入 `postURLs`、`commentsPerPost`；有 diggCount、replyCommentTotal；会混广告评论 |
| YouTube 视频 | streamers/youtube-scraper | $4/千条 | `searchQueries`、`maxResults`、`dateFilter`；viewCount、likes、commentsCount、date |
| YouTube 评论 | streamers/youtube-comments-scraper | $2/千条 | `startUrls`、`maxComments`、`sortCommentsBy: TOP_COMMENTS`；最低上限 $0.5；voteCount、replyCount、相对时间 |
| App Store 评论 | thewolves/appstore-reviews-scraper | $0.1/千条 | `appIds`（数字 ID）、`country`、`maxItems`；score、title、text、version |
| Google Play 评论 | theagents/googleplay-reviews | $0.1/千条 | `appIds`（包名）、`sort`、`maxItems`；score、thumbsUp、text、version |
| X 推文 | apidojo/twitter-scraper-lite | 每次查询 $0.016 + $0.4/千条起 | `searchTerms`（支持高级搜索语法）、`sort`、`maxItems` |
| Trustpilot 评价 | memo23/trustpilot-scraper-ppe | $0.75/千条 + $0.05/次 | `startUrls`（域名）；最低上限 $0.45；rating、text、source、experiencedDate |
| Google Trends 曲线 | data_xplorer/google-trends-fast-scraper | $2/千条 | `mode: keyword`、`keyword`、`predefinedTimeframe`、`geo`；输出 timeline_data（内含 isPartial） |

价格和成功率会变，正式用前用 `find` 复核一次。

## 5. 数据留档与输出

- 每次 run 保存原始 JSON（会话临时目录）和**去掉用户名/头像**的精简版（项目共享目录，如 `research/<主题>/data/<阶段>/`）。每条记录带 `source`、`fetched_at`、`query`/URL。
- 每阶段一张小表：来源、请求条数、实际条数、相关率、剔除比例、花费、是否过闸、下一步。

## 6. 每次抓完必须交付一份 md 报告（不能只给数据）

每个阶段结束（S1 也要，篇幅可以短）都在 `research/<主题>/报告_<阶段>_<日期>.md` 写一份报告，交给用户时附上这份文件。报告给人看、帮助进一步思考，结构固定如下：

```markdown
# <主题> 数据抓取报告（<阶段>，<日期>）

## 一句话结论
这批数据能不能用、能回答什么问题、下一步建议（继续放量 / 换找法 / 停）。

## 1. 抓了什么（明细概况）
| 来源 | 找法（Tavily 查询 / 关键词 / URL） | Actor | 请求条数 | 实际条数 | 时间窗口 | 花费 |
- 数据都在哪：文件路径 + 每个文件一句话说明。
- 样本长什么样：每个来源 2–3 条代表性原文（截短，去用户名）。

## 2. 数据质量
| 检查项 | 结果 | 是否达标 |
（条数完整率、关键字段缺失率、相关率、重复率、已删除/广告/外链剔除比例、指标成熟度如帖子是否满 72 小时、单价偏差）
- 已知偏差：谁在说话（平台人群）、来源是否过于集中、时间段缺口。
- 不能用来下结论的部分，明确列出。

## 3. 初步发现（只写数据直接支撑的）
- 3–7 条，每条带数字或原话引用和来源；推断要标“推断”。
- Trends：曲线形状、峰值时间、季节性；注明是 0–100 相对值。

## 4. 数据明细（每个来源前五条）与字段含义
- 每个来源一张表，列出前五条记录的关键字段（正文截短到约 90 字，去用户名）。
- 字段含义表：文件 | 字段 | 含义（如 score=抓取时点赞数，isPartial=未完结周期，source=BasicLink 表示商家邀请）。
- 一句话说明适合做什么（痛点归纳、竞品提及统计、需求趋势）和不适合做什么（市场规模估算、跨请求比较 Trends 数值）。

## 5. 待思考的问题与下一步
- 这批数据引出的开放问题（3–5 个），供用户判断方向。
- 下一阶段计划：规模、预估花费、要改的找法或过滤规则。
```

S3 正式报告还要写明：来源分布（任一来源 ≤ 50%），且每个关键结论至少有两个独立来源支撑（如 Reddit 痛点 + Trends 上升）。

报告写完自查：每个数字都能在数据文件里找到；没有把点赞数当需求规模；花费与 `whoami` 前后差额一致。

## 7. 不要做

- 不要只交数据不交报告；不要跳过 S1/S2 直接大批量；不要不带 `maxTotalChargeUsd` 跑。
- 不要只看 HTTP 状态码或“run SUCCEEDED”判断成功，要看条数、字段和相关性。
- 不要用点赞数直接当需求规模；Reddit 帖子发布不足 72 小时的互动数不要用。不要把 TikTok 播放量当购买意愿。
- 不要绕过登录墙、签名或验证码；不要用个人账号 cookie；不要保存展示已删除内容；只留调研必需字段，用户名哈希或删除。
- 代抓数据仍受平台条款约束：调研内部分析可以，进产品或对外售卖前要拿授权。Reddit 量化数据如有官方 OAuth API 可用，优先用官方。

## 附：helper 脚本 `apify_stage.py`

```python
#!/usr/bin/env python3
"""Staged Apify helper (stdlib only).
Usage:
  apify_stage.py whoami
  apify_stage.py find "<keywords>"               # search Store, show price/success/users
  apify_stage.py schema <user~actor>             # print input schema of default build
  apify_stage.py run <user~actor> <input.json> <out.json> --max-usd 0.5
  apify_stage.py check <out.json> --expect N --fields a,b,c [--text-field title] [--must "kw1|kw2"]
Token: env APIFY_TOKEN, or none if a proxy injects Authorization for api.apify.com.
"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

API = "https://api.apify.com/v2"

def req(path, data=None, timeout=330):
    h = {"Content-Type": "application/json"}
    if os.environ.get("APIFY_TOKEN"):
        h["Authorization"] = "Bearer " + os.environ["APIFY_TOKEN"]
    r = urllib.request.Request(API + path, data=json.dumps(data).encode() if data is not None else None,
                               headers=h, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as f:
            return json.loads(f.read() or b"null")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        sys.exit(f"HTTP {e.code} on {path.split('?')[0]}: {body}")

def whoami():
    me = req("/users/me")["data"]; lim = req("/users/me/limits")["data"]
    print("user:", me.get("username"), "| plan:", (me.get("plan") or {}).get("id"))
    print("monthly usage USD:", round(lim["current"].get("monthlyUsageUsd", 0), 3),
          "/ cap", lim["limits"].get("maxMonthlyUsageUsd"))

def find(q):
    items = req("/store?" + urllib.parse.urlencode({"search": q, "limit": 10, "sortBy": "popularity"}))["data"]["items"]
    for a in items:
        s = a.get("stats") or {}; p = a.get("currentPricingInfo") or {}
        runs = s.get("publicActorRunStats30Days") or {}
        tot = runs.get("TOTAL") or 0; ok = runs.get("SUCCEEDED") or 0
        print(f'{a["username"]}~{a["name"]:<40} users={s.get("totalUsers")} '
              f'rating={a.get("actorReviewRating")} success30d={(ok/tot*100 if tot else 0):.1f}% '
              f'pricing={p.get("pricingModel")} modified={str(a.get("modifiedAt"))[:10]}')

def schema(actor):
    d = req(f"/acts/{actor}/builds/default")["data"]
    s = d.get("inputSchema") or (d.get("actorDefinition") or {}).get("input") or {}
    if isinstance(s, str): s = json.loads(s)
    for k, v in s.get("properties", {}).items():
        print(f'{k:<32} {v.get("type"):<8} default={str(v.get("default", v.get("prefill", "")))[:50]} '
              f'{("enum=" + str(v["enum"])[:70]) if "enum" in v else ""}')

def run(actor, inp, out, max_usd):
    """Start async, wait, then fetch items; prints cost and the run's status message."""
    t = time.time()
    r = req(f"/acts/{actor}/runs?maxTotalChargeUsd={max_usd}", json.load(open(inp)))["data"]
    while r["status"] in ("READY", "RUNNING"):
        r = req(f"/actor-runs/{r['id']}?waitForFinish=60")["data"]
    data = req(f"/datasets/{r['defaultDatasetId']}/items?clean=true&format=json")
    json.dump(data, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"{actor}: {r['status']} | {len(data)} items in {time.time()-t:.0f}s | "
          f"cost ${r.get('usageTotalUsd') or 0:.3f} | events {r.get('chargedEventCounts')} -> {out}")
    if r.get("statusMessage"):
        print("  status message:", r["statusMessage"][:200])

def check(out, expect, fields, text_field=None, must=None):
    d = json.load(open(out)); n = len(d)
    print(f"items={n} expected={expect} -> {'OK' if n >= 0.9*expect else 'PARTIAL (<90%)'}")
    for f in fields:
        miss = sum(1 for x in d if x.get(f) in (None, "", []))
        print(f"  field {f:<22} missing {miss}/{n}")
    ids = [x.get("id") or x.get("cid") for x in d]
    print("  duplicate ids:", n - len(set(ids)))
    if text_field:
        txt = [str(x.get(text_field) or "") for x in d]
        print("  deleted/removed:", sum(t in ("[deleted]", "[removed]") for t in txt))
        print("  with links:", sum("http" in t for t in txt))
        if must:
            rel = sum(bool(re.search(must, t, re.I)) for t in txt)
            print(f"  relevance (matches /{must}/): {rel}/{n} = {rel/max(n,1):.0%}")
    if d: print("  sample keys:", sorted(d[0].keys())[:25])

if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, dflt=None: a[a.index(k)+1] if k in a else dflt
    if a[0] == "whoami": whoami()
    elif a[0] == "find": find(a[1])
    elif a[0] == "schema": schema(a[1])
    elif a[0] == "run": run(a[1], a[2], a[3], opt("--max-usd", "0.5"))
    elif a[0] == "check":
        check(a[1], int(opt("--expect", "0")), [f for f in opt("--fields", "").split(",") if f],
              opt("--text-field"), opt("--must"))
```
