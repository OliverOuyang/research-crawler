# market-research-crawler

市场调研数据采集的方法、实测结论和小工具。给其他项目复用：先读文档定方案，再用脚本采集。

## 文档（docs/）

| 文档 | 内容 |
|---|---|
| [市场数据采集方法论](docs/市场数据采集方法论.md) | 五步流程、数据源地图、工具选择、效率要点 |
| [改进路径与标准](docs/改进路径与标准.md) | 对已有工作的改进：新数据源、Trends 拼接方法、LLM 编码一致性、新增质量标准 F–I |
| [爬取实测与数据原则](docs/爬取实测与数据原则.md) | Reddit / Google Trends / TikTok 实测、踩坑、“不要做”原则、质量标准 A–E |
| [抓取平台选型与组合](docs/抓取平台选型与组合.md) | Apify 抓取器和平替的价格、成功率、成本估算 |
| [tavily实测](docs/tavily实测.md) | Tavily 能补和补不上的缺口 |

## 脚本（scripts/，只用 Python 标准库）

```bash
cp config/.env.example .env      # 本机运行时填 key；.env 不会被提交
python scripts/check_apis.py     # 检查 Tavily、MiniMax 是否可用（不打印 key）
python scripts/tavily_search.py "关键词" --depth basic --max 8 --domain reddit.com
```

搜索结果按日期存到 `data/raw/tavily/`（已被 .gitignore 排除）。

## 密钥
所有 key 只放在 `.env` 或云环境的网络密钥里，`.gitignore` 已排除 `.env`、`*.key`、`*secret*`、`*credential*`。不要把 key 写进代码、文档或提交信息。
