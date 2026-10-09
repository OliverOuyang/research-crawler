"""Tavily 搜索，结果存到 data/raw/tavily/<日期>/。

用法：python scripts/tavily_search.py "关键词" [--depth basic|advanced] [--max 8] [--domain reddit.com]
云端会话由代理注入 key；本机需在 .env 里设置 TAVILY_API_KEY。
"""
import argparse
import datetime as dt
import json
import os
import re
import urllib.request
from pathlib import Path

from _env import load_env

ROOT = Path(__file__).resolve().parent.parent


def search(query, depth="basic", max_results=8, domains=None):
    body = {"query": query, "search_depth": depth, "max_results": max_results, "include_answer": "advanced"}
    if domains:
        body["include_domains"] = domains
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("TAVILY_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request("https://api.tavily.com/search", json.dumps(body).encode(), headers)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def main():
    load_env()
    p = argparse.ArgumentParser()
    p.add_argument("query")
    p.add_argument("--depth", default="basic", choices=["basic", "advanced"])
    p.add_argument("--max", type=int, default=8)
    p.add_argument("--domain", action="append")
    a = p.parse_args()
    res = search(a.query, a.depth, a.max, a.domain)
    now = dt.datetime.now(dt.timezone.utc)
    out = ROOT / "data/raw/tavily" / now.strftime("%Y-%m-%d")
    out.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"\W+", "-", a.query)[:60].strip("-")
    f = out / f"{now.strftime('%H%M%S')}-{slug}.json"
    f.write_text(json.dumps({"query": a.query, "fetched_at": now.isoformat(), "params": vars(a), "response": res}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(res.get("answer") or "")
    for r in res.get("results", []):
        print(f"- {r['title']} | {r['url']}")
    print(f"\n已保存：{f.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
