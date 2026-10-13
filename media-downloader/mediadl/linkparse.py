"""从整段分享文案里抠出链接并判断平台。

平台判断规则取自 dyxhsdownloader.com 前端（REA 静态分析定位到的 Bc / $c 两个函数），
保证本地版认得的链接范围和网站一致。
"""
from __future__ import annotations

import re

# 先粗抓所有 http(s) 链接，再去掉尾部中文标点等杂质
_URL_RE = re.compile(r"https?://[^\s　一-鿿，。！？、；：“”‘’（）【】《》]+", re.I)
_TRAILING = ".,;:!?)]}>'\"`"

_REDDIT_RE = re.compile(
    r"https?://(?:(?:www|old|new|m|np|sh)\.)?reddit\.com/(?:r/[a-z0-9_]+/(?:comments/[a-z0-9]+(?:[/?#]|$)"
    r"|s/[a-z0-9_-]+(?:[/?#]|$))|s/[a-z0-9_-]+(?:[/?#]|$)|(?:comments|gallery)/[a-z0-9]+(?:[/?#]|$))"
)
_REDDIT_SHORT_RE = re.compile(r"https?://(?:www\.)?redd\.it/[a-z0-9]+(?:[/?#]|$)")

PROVIDERS = {
    "douyin": "抖音",
    "xiaohongshu": "小红书",
    "bilibili": "B站",
    "weibo": "微博",
    "tiktok": "TikTok",
    "instagram": "Instagram",
    "twitter": "X / Twitter",
    "reddit": "Reddit",
}


def detect_provider(url: str) -> str | None:
    t = (url or "").lower()
    if not t:
        return None
    if re.search(r"(douyin\.com|v\.douyin|iesdouyin)", t):
        return "douyin"
    if re.search(r"(xiaohongshu\.com|xhslink\.com|xhs\.com)", t):
        return "xiaohongshu"
    if re.search(r"(kuaishou\.com|kwai\.com|chenzhongtech\.com)", t):
        return "kuaishou"
    if re.search(r"(bilibili\.com|b23\.tv|bili2233\.cn)", t):
        return "bilibili"
    if re.search(r"(weibo\.com|weibo\.cn)", t) or re.search(r"(?:^|[^\w.])t\.cn/", t):
        return "weibo"
    if re.search(r"(tiktok\.com|vm\.tiktok|vt\.tiktok)", t):
        return "tiktok"
    if re.search(r"(instagram\.com|instagr\.am)", t):
        return "instagram"
    if re.search(r"(?:^|[/.])(?:x\.com|twitter\.com)(?:[/:?#]|$)", t):
        return "twitter"
    if _REDDIT_RE.search(t) or _REDDIT_SHORT_RE.search(t):
        return "reddit"
    return None


def extract_urls(text: str) -> list[str]:
    """返回文案里所有受支持平台的链接，去重并保持顺序。"""
    seen: dict[str, None] = {}
    for m in _URL_RE.finditer(text or ""):
        u = m.group(0).rstrip(_TRAILING)
        if u and detect_provider(u) and u not in seen:
            seen[u] = None
    return list(seen)
