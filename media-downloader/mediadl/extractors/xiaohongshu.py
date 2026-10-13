"""小红书：图文笔记（含 Live 图）、视频笔记。

做法：跟随 xhslink 短链拿到带 xsec_token 的笔记地址，读页面内嵌的 window.__INITIAL_STATE__。
图片用 token 拼 ci.xiaohongshu.com 原图地址（去掉 !nd_dft_wlteh 之类的压缩后缀），转 PNG 保存，
视频优先用 originVideoKey 拼原始文件，拿不到再用 h264/h265 流地址。
注意：直接用不带 xsec_token 的 explore 链接通常会被导到 404，请粘贴 App 里的分享链接或文案。
"""
from __future__ import annotations

import re

from ..http import DESKTOP_UA, Client
from ..models import ExtractError, MediaFile, MediaResult
from ._util import find_json_assignment, first, https, walk

_ID_RE = re.compile(r"/(?:explore|discovery/item|item|user/profile/[0-9a-f]+)/([0-9a-f]{24})")


def note_id(url: str) -> str | None:
    m = _ID_RE.search(url)
    return m.group(1) if m else None


def extract(url: str) -> MediaResult:
    client = Client("xiaohongshu", ua=DESKTOP_UA)
    final, html = client.get(url, headers={"Referer": "https://www.xiaohongshu.com/"})
    if "/404" in final or "/website-login" in final:
        raise ExtractError("小红书返回了 404/登录页：笔记不可见，或链接缺少 xsec_token（请用 App 分享链接），或需要在 cookies/xiaohongshu.txt 放登录态")
    nid = note_id(final) or note_id(url)
    state = find_json_assignment(html, ["__INITIAL_STATE__"])
    note = _find_note(state, nid)
    if not note:
        raise ExtractError("小红书页面里没找到笔记数据（可能触发了验证或页面结构变了）")
    return parse_note(note, final)


def _find_note(state, nid: str | None) -> dict | None:
    if not state:
        return None
    # 桌面版：note.noteDetailMap[id].note；移动版：noteData.data.noteData
    for d in walk(state):
        ndm = d.get("noteDetailMap")
        if isinstance(ndm, dict):
            entry = ndm.get(nid) if nid else None
            entry = entry or next((v for v in ndm.values() if isinstance(v, dict) and v.get("note")), None)
            if entry and entry.get("note"):
                return entry["note"]
    for d in walk(state):
        if ("imageList" in d or "video" in d) and ("noteId" in d or "id" in d) and ("desc" in d or "title" in d):
            return d
    return None


def image_token(u: str) -> str | None:
    """http://sns-webpic-qc.xhscdn.com/202410131200/abc123/1040g2sg31...!nd_dft_wlteh_webp_3 -> 1040g2sg31..."""
    u = u.split("?")[0].split("!")[0]
    parts = u.split("/")
    if len(parts) >= 6 and "xhscdn.com" in parts[2]:
        return "/".join(parts[5:])
    if len(parts) >= 4 and "xhscdn.com" in parts[2]:
        return "/".join(parts[3:])
    return None


def parse_note(note: dict, url: str = "") -> MediaResult:
    nid = note.get("noteId") or note.get("id") or ""
    user = note.get("user") or {}
    res = MediaResult(
        provider="xiaohongshu",
        id=nid,
        url=url or f"https://www.xiaohongshu.com/explore/{nid}",
        title=note.get("title") or (note.get("desc") or "")[:60],
        desc=note.get("desc") or "",
        author=user.get("nickname") or user.get("nickName") or "",
        referer="https://www.xiaohongshu.com/",
        extractor="xhs-initial-state",
    )
    video = note.get("video") or {}
    if note.get("type") == "video" or video.get("media"):
        streams = ((video.get("media") or {}).get("stream") or {})
        cands: list[str] = []
        key = (video.get("consumer") or {}).get("originVideoKey")
        if key:
            cands.append(f"https://sns-video-bd.xhscdn.com/{key}")
        for codec in ("h264", "h265", "av1"):
            for s in streams.get(codec) or []:
                cands += [https(s.get("masterUrl"))] + [https(b) for b in s.get("backupUrls") or []]
        cands = [c for c in dict.fromkeys(cands) if c]
        if not cands:
            raise ExtractError("小红书视频笔记里没有可用的视频地址")
        cap = video.get("capa") or {}
        res.files.append(MediaFile(cands[0], "video", "mp4", backup_urls=cands[1:]))
        if cap.get("duration"):
            res.duration = float(cap["duration"])
        res.watermark = "removed" if key else "attempted"
    for img in note.get("imageList") or []:
        raw = first(
            img.get("urlDefault"),
            img.get("url"),
            next((i.get("url") for i in img.get("infoList") or [] if i.get("imageScene") == "WB_DFT"), None),
        )
        if not raw:
            continue
        tok = image_token(raw)
        # 原图默认是 HEIC，加 imageView2 转成 PNG（无损、兼容性好）；原始 HEIC 和页面图作备用源
        backups = [f"https://ci.xiaohongshu.com/{tok}", https(raw)] if tok else [https(raw)]
        primary = f"https://ci.xiaohongshu.com/{tok}?imageView2/format/png" if tok else backups.pop(0)
        kind = "image" if not res.videos else "cover"
        res.files.append(MediaFile(primary, kind, "png" if tok else "jpg", img.get("width"), img.get("height"), backups))
        if img.get("livePhoto"):
            for s in ((img.get("stream") or {}).get("h264") or []):
                if s.get("masterUrl"):
                    res.files.append(MediaFile(https(s["masterUrl"]), "live", "mp4"))
                    break
    if not res.videos:
        res.watermark = "removed" if res.images else "unknown"
    if not res.files:
        raise ExtractError("小红书笔记里没有图片或视频")
    return res
