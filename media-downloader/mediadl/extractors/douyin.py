"""抖音：视频、图集（含 Live 动图）、背景音乐。

做法：把任何抖音链接归一成作品 ID，请求公开分享页 iesdouyin.com/share/{video|note}/{id}/，
从页面内嵌的 window._ROUTER_DATA 里读作品数据。无水印视频用 play 接口代替 playwm。
不需要登录；如果分享页对你的网络不返回数据，会退回 yt-dlp（那时可能需要 cookies/douyin.txt）。
"""
from __future__ import annotations

import re

from ..http import MOBILE_UA, Client
from ..models import ExtractError, MediaFile, MediaResult
from ._util import find_json_assignment, https, walk

_ID_PATTERNS = [
    r"/(?:video|note|slides)/(\d{15,21})",
    r"/share/(?:video|note|slides)/(\d{15,21})",
    r"[?&](?:modal_id|aweme_id|item_ids|vid)=(\d{15,21})",
]


def aweme_id(url: str) -> str | None:
    for p in _ID_PATTERNS:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def extract(url: str) -> MediaResult:
    client = Client("douyin", ua=MOBILE_UA)
    aid = aweme_id(url)
    if not aid:
        url = client.resolve(url)  # v.douyin.com 短链
        aid = aweme_id(url)
    if not aid:
        raise ExtractError(f"没认出抖音作品 ID：{url}")

    item = None
    # 分享页偶发不带作品数据（VPS 上实测约 1/6），换种类型并整体重试一轮
    for kind in ("video", "note", "video", "note"):
        page = f"https://www.iesdouyin.com/share/{kind}/{aid}/"
        _, html = client.get(page, headers={"Referer": "https://www.douyin.com/"})
        data = find_json_assignment(html, ["_ROUTER_DATA"])
        item = _find_item(data, aid)
        if item:
            break
    if not item:
        raise ExtractError("抖音分享页没有返回作品数据（作品可能已删除/私密，或当前网络被风控）")
    return parse_item(item, url)


def _find_item(data, aid: str) -> dict | None:
    if not data:
        return None
    for d in walk(data):
        items = d.get("item_list")
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict) and str(it.get("aweme_id", aid)) == aid:
                    return it
    return None


def parse_item(item: dict, url: str = "") -> MediaResult:
    aid = str(item.get("aweme_id", ""))
    author = (item.get("author") or {}).get("nickname", "")
    desc = item.get("desc", "") or ""
    res = MediaResult(
        provider="douyin",
        id=aid,
        url=url or f"https://www.douyin.com/video/{aid}",
        title=desc[:60],
        desc=desc,
        author=author,
        referer="https://www.douyin.com/",
        extractor="douyin-share-page",
    )
    video = item.get("video") or {}
    images = item.get("images") or []

    if images:  # 图集
        res.watermark = "removed"
        for img in images:
            urls = [https(u) for u in (img.get("url_list") or []) if u]
            if urls:
                res.files.append(
                    MediaFile(urls[0], "image", _img_ext(urls[0]), img.get("width"), img.get("height"), urls[1:])
                )
            live = (img.get("video") or {}).get("play_addr") or {}
            lurls = [_nowm(https(u)) for u in (live.get("url_list") or []) if u]
            if lurls:
                res.files.append(MediaFile(lurls[0], "live", "mp4", backup_urls=lurls[1:]))
    else:
        play = video.get("play_addr") or {}
        uri = play.get("uri") or ""
        urls = [_nowm(https(u)) for u in (play.get("url_list") or []) if u]
        if uri and not uri.startswith("http"):
            # 官方播放接口，ratio 取最高；放在第一位，分享页给的地址作备用源
            urls.insert(0, f"https://aweme.snssdk.com/aweme/v1/play/?video_id={uri}&ratio=1080p&line=0")
        if not urls:
            raise ExtractError("抖音作品里没有可用的视频地址")
        res.files.append(MediaFile(urls[0], "video", "mp4", video.get("width"), video.get("height"), urls[1:]))
        res.watermark = "removed"
        dur = video.get("duration") or item.get("duration")
        if dur:
            res.duration = dur / 1000 if dur > 1000 else float(dur)

    cover = ((video.get("origin_cover") or video.get("cover") or {}).get("url_list") or [None])[0]
    if cover:
        res.files.append(MediaFile(https(cover), "cover", _img_ext(cover)))
    music = ((item.get("music") or {}).get("play_url") or {}).get("url_list") or []
    if music:
        res.files.append(MediaFile(https(music[0]), "audio", "mp3"))
    return res


def _nowm(u: str) -> str:
    return u.replace("/playwm/", "/play/")


def _img_ext(u: str) -> str:
    for e in ("webp", "jpeg", "jpg", "png", "heic"):
        if e in u.lower():
            return "jpg" if e == "jpeg" else e
    return "jpg"
