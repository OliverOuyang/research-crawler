"""快手：短视频、图集。

做法：跟随 v.kuaishou.com 短链拿到作品 ID，先看分享页内嵌的 INIT_STATE / __APOLLO_STATE__
（老版本页面直接带作品数据），没有再调网页版 www.kuaishou.com/graphql 的 visionVideoDetail。
2026-10 实测：快手对未登录访问一律弹滑块验证（result=400002）。本工具不绕过验证码，
需要你在自己浏览器里打开快手网页版、通过验证（或登录），再把 cookies 导出到 cookies/kuaishou.txt。
"""
from __future__ import annotations

import gzip
import json
import re

from ..http import DESKTOP_UA, MOBILE_UA, Client
from ..models import ExtractError, MediaFile, MediaResult
from ._util import find_json_assignment, first, https, walk


_GQL = (
    "query visionVideoDetail($photoId: String, $type: String, $page: String, $webPageArea: String) {"
    " visionVideoDetail(photoId: $photoId, type: $type, page: $page, webPageArea: $webPageArea) {"
    " status type author { id name } photo { id duration caption coverUrl photoUrl photoH265Url } } }"
)


def extract(url: str) -> MediaResult:
    client = Client("kuaishou", ua=MOBILE_UA)
    final, html = client.get(url, headers={"Referer": "https://www.kuaishou.com/"})
    state = find_json_assignment(html, ["INIT_STATE", "__APOLLO_STATE__", "__INITIAL_STATE__"])
    photo = _find_photo(state)
    if photo:
        return parse_photo(photo, final)
    pid = _id_from(final) or _id_from(url)
    if not pid:
        raise ExtractError(f"没认出快手作品 ID：{final}")
    return _graphql(pid, final)


def _graphql(pid: str, url: str) -> MediaResult:
    client = Client("kuaishou", ua=DESKTOP_UA)
    page = f"https://www.kuaishou.com/short-video/{pid}"
    client.get(page)  # 先拿 did 等基础 cookie
    body = json.dumps({"operationName": "visionVideoDetail", "variables": {"photoId": pid, "page": "detail"}, "query": _GQL})
    req = client._req("https://www.kuaishou.com/graphql", {"Content-Type": "application/json", "Origin": "https://www.kuaishou.com", "Referer": page}, body.encode())
    with client.opener.open(req, timeout=client.timeout) as r:
        raw = r.read()
    data = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw).get("data") or {}
    if data.get("result") == 400002 or "captcha" in str(data.get("url", "")):
        raise ExtractError(
            "快手要求滑块验证。请在自己的浏览器打开 www.kuaishou.com 通过验证（或登录），"
            "再把 cookies 导出到 cookies/kuaishou.txt 后重试"
        )
    detail = data.get("visionVideoDetail") or {}
    photo = detail.get("photo")
    if not photo:
        raise ExtractError(f"快手没有返回作品数据（status={detail.get('status')}）")
    photo = {**photo, "userName": (detail.get("author") or {}).get("name"), "photoId": pid}
    if photo.get("photoH265Url"):
        photo["mainMvUrls"] = [photo["photoUrl"], photo["photoH265Url"]]
    return parse_photo(photo, url or page)


def _find_photo(state) -> dict | None:
    if not state:
        return None
    for d in walk(state):
        if d.get("mainMvUrls") or d.get("photoUrl") or (d.get("atlas") and d.get("caption") is not None):
            return d
    return None


def parse_photo(p: dict, url: str = "") -> MediaResult:
    pid = str(first(p.get("photoId"), p.get("id"), _id_from(url)) or "")
    res = MediaResult(
        provider="kuaishou",
        id=pid,
        url=url,
        title=(p.get("caption") or "")[:60],
        desc=p.get("caption") or "",
        author=first(p.get("userName"), (p.get("author") or {}).get("name"), "") or "",
        referer="https://www.kuaishou.com/",
        extractor="kuaishou-share-page",
    )
    atlas = p.get("atlas") or (p.get("ext_params") or {}).get("atlas")
    if isinstance(atlas, dict) and atlas.get("list"):
        cdn = (atlas.get("cdn") or atlas.get("cdnList") or ["p2.a.yximgs.com"])[0]
        cdn = cdn.get("cdn") if isinstance(cdn, dict) else cdn
        for path in atlas["list"]:
            res.files.append(MediaFile(f"https://{cdn}{path}", "image", "jpg"))
        music = atlas.get("music")
        if music:
            res.files.append(MediaFile(f"https://{cdn}{music}", "audio", "m4a"))
    else:
        urls = [https(u.get("url") if isinstance(u, dict) else u) for u in p.get("mainMvUrls") or []]
        if p.get("photoUrl"):
            urls.append(https(p["photoUrl"]))
        urls = [u for u in dict.fromkeys(urls) if u]
        if not urls:
            raise ExtractError("快手作品里没有可用的视频地址")
        res.files.append(MediaFile(urls[0], "video", "mp4", p.get("width"), p.get("height"), urls[1:]))
        if p.get("duration"):
            res.duration = p["duration"] / 1000
    res.watermark = "removed"
    cover = first(*[c.get("url") if isinstance(c, dict) else c for c in p.get("coverUrls") or []], p.get("coverUrl"))
    if cover:
        res.files.append(MediaFile(https(cover), "cover", "jpg"))
    return res


def _id_from(url: str) -> str | None:
    m = re.search(r"/(?:short-video|photo|fw/photo)/([\w-]+)", url or "")
    return m.group(1) if m else None
