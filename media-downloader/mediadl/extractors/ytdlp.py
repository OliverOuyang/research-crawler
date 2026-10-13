"""B站、微博、TikTok、Instagram、X/Twitter、Reddit 交给 yt-dlp（成熟、持续维护）。

也作为抖音解析失败时的兜底。需要登录态的内容，把浏览器导出的 cookies.txt 放到 cookies/{平台}.txt。
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from ..http import cookie_file, proxy_for
from ..models import ExtractError, MediaFile, MediaResult


def _ydl_opts(provider: str, extra: dict | None = None) -> dict:
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "skip_download": True}
    cf = cookie_file(provider)
    if cf:
        opts["cookiefile"] = str(cf)
    px = proxy_for(provider)
    if px:
        opts["proxy"] = px
    # 没激活虚拟环境时 PATH 里可能没有 ffmpeg：也找一下解释器旁边的（VPS 上是 venv 里的软链）
    ff = os.environ.get("MEDIADL_FFMPEG") or str(Path(sys.executable).with_name("ffmpeg"))
    if not shutil.which("ffmpeg") and os.path.exists(ff):
        opts["ffmpeg_location"] = ff
    opts.update(extra or {})
    return opts


def extract(url: str, provider: str) -> MediaResult:
    try:
        import yt_dlp
    except ImportError as e:
        raise ExtractError("这个平台依赖 yt-dlp：请先 pip install -r requirements.txt") from e
    try:
        with yt_dlp.YoutubeDL(_ydl_opts(provider)) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:  # yt-dlp 的异常类型很多，统一转成用户可读的提示
        raise ExtractError(f"yt-dlp 解析失败：{str(e).splitlines()[0][:300]}") from e
    return from_info(info, provider, url)


def from_info(info: dict, provider: str, url: str = "") -> MediaResult:
    entries = info.get("entries")
    infos = [e for e in entries if e] if entries else [info]
    head = infos[0]
    res = MediaResult(
        provider=provider,
        id=str(info.get("id") or head.get("id") or ""),
        url=info.get("webpage_url") or url,
        title=info.get("title") or head.get("title") or "",
        desc=info.get("description") or "",
        author=info.get("uploader") or info.get("channel") or head.get("uploader") or "",
        duration=head.get("duration"),
        watermark="removed" if provider in ("tiktok", "douyin") else "unknown",
        extractor="yt-dlp",
    )
    for it in infos:
        vcodec = it.get("vcodec")
        if it.get("ext") in ("jpg", "jpeg", "png", "webp") or (vcodec == "none" and it.get("acodec") == "none"):
            res.files.append(MediaFile(it.get("url", ""), "image", it.get("ext") or "jpg"))
            continue
        # 下载时让 yt-dlp 自己选最佳格式并合并音视频；这里只给一个能预览的地址
        best = it.get("url") or next(
            (f.get("url") for f in reversed(it.get("formats") or []) if f.get("vcodec") not in (None, "none")), ""
        )
        res.files.append(
            MediaFile(best or it.get("webpage_url", ""), "video", "mp4", it.get("width"), it.get("height"))
        )
    if head.get("thumbnail"):
        res.files.append(MediaFile(head["thumbnail"], "cover", "jpg"))
    return res


def download(url: str, provider: str, outdir: str) -> list[str]:
    """用 yt-dlp 直接下载到 outdir，返回新增的文件。B 站 DASH 音视频合并需要本机有 ffmpeg。"""
    import yt_dlp

    os.makedirs(outdir, exist_ok=True)
    before = set(os.listdir(outdir))
    opts = _ydl_opts(
        provider,
        {
            "skip_download": False,
            "outtmpl": f"{outdir}/%(id)s_%(title).60B.%(ext)s",
            "format": "bv*+ba/b",
            "merge_output_format": "mp4",
        },
    )
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:
        raise ExtractError(f"yt-dlp 下载失败：{str(e).splitlines()[0][:300]}") from e
    new = sorted(set(os.listdir(outdir)) - before)
    return [os.path.join(outdir, n) for n in new if not n.endswith((".part", ".ytdl"))]
