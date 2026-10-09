# Tavily 实测（2026-10-09，云端容器）

- 套餐：Researcher（免费档），每月 1000 credits，测试前已用 0。本次共 5 次调用（/usage ×2、/search advanced ×3、/extract advanced ×1，4 个 URL），按 Tavily 计费规则约用 8 credits；/usage 计数有延迟，测完时仍显示 0。
- 测试主题：笔记类 App 的用户抱怨（Reddit）、护肤测评（TikTok）、AI 笔记 App 的 Trends。原始返回在会话临时目录，未入库。

## 结果

| 测试 | 结果 |
|---|---|
| /search reddit.com（advanced, include_raw_content） | 10 条全是相关帖子（r/PKMS、r/NoteTaking、r/androidapps 等），每条有 1–2 句摘要；**raw_content 全部为空** |
| /extract 3 个 Reddit 帖子 | 3/3 成功，每帖 22–34KB Markdown。正文完整；评论分别拿到约 10、24、25 条（首屏），“more replies” 折叠部分拿不到 |
| Reddit 抽取的字段 | 有作者名、评论 permalink（含评论 ID）、相对时间（“2y ago”“4y ago”）、[deleted] 标记、AutoModerator 评论；**没有点赞数、评论总数、精确时间戳**；页面里夹杂广告块和侧栏推荐 |
| /search tiktok.com | 10 条：8 条视频 URL + 话题页，只有标题和一句描述，raw_content 为空；2 条 TikTok Shop 商品页有完整正文（7–17KB） |
| /extract TikTok 视频 | **失败**：“Failed to fetch url” |
| /search Google Trends 类查询 | 返回的是博客、行业报告、Google 官方博客文章，**没有任何 Trends 曲线或数值** |

## 对三个缺口的结论

1. **Reddit 403：部分补上。** 能拿到帖子正文和首屏评论文本，适合做痛点原话收集。但没有点赞数和精确时间，评论不完整，过不了质量标准 B（指标成熟度）和 A（条数完整性）。要量化仍需官方 OAuth API。
2. **TikTok 空数据：没补上。** 视频页抽取失败，只有搜索摘要和 Shop 商品页可用。
3. **Trends 429：没补上。** Tavily 是网页搜索，不提供 Trends 数据，只能找到引用 Trends 的二手文章。

## 合规提醒
Tavily 是代抓第三方页面，Reddit 内容的使用条款不因此改变（见《爬取实测与数据原则》第四节第 2、5 条）。
