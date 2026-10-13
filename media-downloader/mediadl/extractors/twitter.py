"""X / Twitter：视频（最高码率 MP4）、GIF、单图/多图原图。

做法：走开源项目 FixTweet 的公开只读接口 api.fxtwitter.com，无需登录，图片和视频都能拿到；
接口不可用时由 core 退回 yt-dlp（yt-dlp 只认带视频的推文）。
"""
from __future__ import annotations

import json
import re

from ..http import DESKTOP_UA, Client
from ..models import ExtractError, MediaFile, MediaResult

_ID_RE = re.compile(r"/status(?:es)?/(\d+)")


def extract(url: str) -> MediaResult:
    m = _ID_RE.search(url)
    if not m:
        raise ExtractError(f"没认出推文 ID：{url}")
    tid = m.group(1)
    _, body = Client("twitter", ua=DESKTOP_UA).get(f"https://api.fxtwitter.com/status/{tid}")
    data = json.loads(body)
    tweet = data.get("tweet")
    if not tweet:
        raise ExtractError(f"推文不可见或不存在（{data.get('message', data.get('code'))}）")
    return parse_tweet(tweet, url)


def parse_tweet(t: dict, url: str = "") -> MediaResult:
    author = t.get("author") or {}
    res = MediaResult(
        provider="twitter",
        id=str(t.get("id", "")),
        url=t.get("url") or url,
        title=(t.get("text") or "")[:60],
        desc=t.get("text") or "",
        author=author.get("name") or author.get("screen_name") or "",
        watermark="removed",
        extractor="fxtwitter",
    )
    for m in (t.get("media") or {}).get("all") or []:
        typ = m.get("type")
        if typ == "photo":
            u = m.get("url", "")
            orig = re.sub(r"\?.*$", "", u) + "?name=orig" if "pbs.twimg.com" in u else u
            res.files.append(MediaFile(orig, "image", "jpg", m.get("width"), m.get("height"), [u]))
        elif typ in ("video", "gif"):
            variants = sorted(
                (f for f in m.get("formats") or m.get("variants") or [] if "mp4" in (f.get("container") or f.get("content_type") or "")),
                key=lambda f: f.get("bitrate") or 0,
                reverse=True,
            )
            urls = [m.get("url")] + [f.get("url") for f in variants]
            urls = [u for u in dict.fromkeys(urls) if u]
            if urls:
                res.files.append(MediaFile(urls[0], "video", "mp4", m.get("width"), m.get("height"), urls[1:]))
                if m.get("duration") and res.duration is None:
                    res.duration = float(m["duration"])
            if m.get("thumbnail_url"):
                res.files.append(MediaFile(m["thumbnail_url"], "cover", "jpg"))
    if not res.files:
        raise ExtractError("这条推文里没有图片或视频")
    return res
