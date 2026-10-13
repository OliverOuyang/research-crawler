"""Reddit：单图、多图（gallery）帖子走公开的 .json 接口；Reddit 托管视频交给 yt-dlp（它会合并音轨）。"""
from __future__ import annotations

import html
import json
import urllib.parse

from ..http import Client
from ..models import ExtractError, MediaFile, MediaResult

_UA = "mediadl/0.1 (personal downloader)"


class IsVideo(Exception):
    """帖子是视频，交给 yt-dlp。"""


def extract(url: str) -> MediaResult:
    client = Client("reddit", ua=_UA)
    final = client.resolve(url) if "/s/" in url or "redd.it" in url else url
    p = urllib.parse.urlparse(final)
    api = urllib.parse.urlunparse(("https", "www.reddit.com", p.path.rstrip("/") + "/.json", "", "raw_json=1", ""))
    _, body = client.get(api)
    data = json.loads(body)
    post = data[0]["data"]["children"][0]["data"]
    return parse_post(post, final)


def parse_post(post: dict, url: str = "") -> MediaResult:
    if post.get("is_video") or (post.get("secure_media") or {}).get("reddit_video"):
        raise IsVideo()
    res = MediaResult(
        provider="reddit",
        id=post.get("id", ""),
        url=url or "https://www.reddit.com" + post.get("permalink", ""),
        title=post.get("title", ""),
        desc=post.get("selftext", ""),
        author=post.get("author", ""),
        watermark="removed",
        extractor="reddit-json",
    )
    meta = post.get("media_metadata") or {}
    if post.get("is_gallery") and meta:
        order = [i["media_id"] for i in (post.get("gallery_data") or {}).get("items", [])] or list(meta)
        for mid in order:
            m = meta.get(mid) or {}
            s = m.get("s") or {}
            u = html.unescape(s.get("u") or s.get("gif") or s.get("mp4") or "")
            if u:
                kind = "video" if s.get("mp4") and not s.get("u") else "image"
                res.files.append(MediaFile(u, kind, "mp4" if kind == "video" else "jpg", s.get("x"), s.get("y")))
    elif post.get("post_hint") == "image" or str(post.get("url", "")).startswith("https://i.redd.it/"):
        res.files.append(MediaFile(post["url"], "image", post["url"].rsplit(".", 1)[-1][:4] or "jpg"))
    if not res.files:
        raise ExtractError("这个 Reddit 帖子里没有 Reddit 托管的图片或视频（外链内容不支持）")
    return res
