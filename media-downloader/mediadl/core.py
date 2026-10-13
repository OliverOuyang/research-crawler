"""对外的两个动作：parse（解析链接）和 download（保存到本地，可打包 ZIP）。CLI 和本地网页都调这里。"""
from __future__ import annotations

import os
import re
import zipfile
from pathlib import Path

from .extractors import douyin, reddit, twitter, xiaohongshu, ytdlp
from .http import DESKTOP_UA, MOBILE_UA, Client
from .linkparse import detect_provider, extract_urls
from .models import ExtractError, MediaFile, MediaResult

DEFAULT_OUT = Path(os.environ.get("MEDIADL_OUT") or Path(__file__).resolve().parent.parent / "downloads")

# 识别得出但不做的平台
UNSUPPORTED = {"kuaishou": "快手暂不支持：未登录访问一律要滑块验证，本工具不做"}

# 每个平台的解析顺序：先自研解析，失败再交给 yt-dlp
_CHAINS = {
    "douyin": [douyin.extract, "yt-dlp"],
    "xiaohongshu": [xiaohongshu.extract],
    "twitter": [twitter.extract, "yt-dlp"],
    "reddit": [reddit.extract, "yt-dlp"],
}


def parse(url: str) -> MediaResult:
    provider = detect_provider(url)
    if not provider:
        raise ExtractError(f"不支持的链接：{url}")
    if provider in UNSUPPORTED:
        raise ExtractError(UNSUPPORTED[provider])
    errors = []
    for step in _CHAINS.get(provider, ["yt-dlp"]):
        try:
            if step == "yt-dlp":
                return ytdlp.extract(url, provider)
            return step(url)
        except reddit.IsVideo:
            continue
        except ExtractError as e:
            errors.append(str(e))
        except (OSError, ValueError, KeyError, IndexError) as e:  # 网络错误、页面结构变化
            errors.append(f"{type(e).__name__}: {e}")
    raise ExtractError("；".join(errors) or "解析失败")


def parse_text(text: str) -> list[str]:
    """整段分享文案 -> 链接列表（网站同样支持一次粘多条，逐条解析）。"""
    return extract_urls(text)


def _safe(s: str, n: int = 40) -> str:
    s = re.sub(r"[\\/:*?\"<>|\s#@]+", "_", s or "").strip("_.")
    return s[:n] or "untitled"


def download(
    res: MediaResult,
    outdir: str | Path = DEFAULT_OUT,
    kinds: tuple[str, ...] = ("video", "image", "live"),
    make_zip: bool = False,
    errors: list[str] | None = None,
) -> list[Path]:
    """把解析结果里指定类型的文件存到 outdir/{平台}/{作者_标题_id}/。

    单个文件失败不影响其它文件；失败原因追加到 errors（传了的话），全部失败才抛异常。
    """
    errors = [] if errors is None else errors
    folder = Path(outdir) / res.provider / _safe(f"{res.author}_{res.title}_{res.id}", 90)
    folder.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    if res.extractor == "yt-dlp" and "video" in kinds and res.videos:
        try:
            saved += [Path(p) for p in ytdlp.download(res.url, res.provider, str(folder))]
        except ExtractError as e:
            errors.append(str(e))
        kinds = tuple(k for k in kinds if k != "video")

    client = Client(res.provider, ua=MOBILE_UA if res.provider == "douyin" else DESKTOP_UA)
    counters: dict[str, int] = {}
    for f in res.files:
        if f.kind not in kinds:
            continue
        counters[f.kind] = counters.get(f.kind, 0) + 1
        name = f"{f.kind}_{counters[f.kind]:02d}"
        try:
            saved.append(_fetch(client, f, folder / name, res.referer))
        except ExtractError as e:
            errors.append(f"{name}：{e}")
    if not saved and errors:
        raise ExtractError("；".join(errors))

    if make_zip and len(saved) > 1:
        zpath = folder.with_suffix(".zip")
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
            for p in saved:
                z.write(p, p.name)
        saved.append(zpath)
    return saved


_CT_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/heic": "heic", "video/mp4": "mp4",
           "audio/mpeg": "mp3", "audio/mp4": "m4a", "image/gif": "gif"}


def _fetch(client: Client, f: MediaFile, stem: Path, referer: str) -> Path:
    errors = []
    for u in [f.url, *f.backup_urls]:
        if not u:
            continue
        try:
            with client.stream(u, headers={"Referer": referer} if referer else None) as r:
                ct = (r.headers.get("Content-Type") or "").split(";")[0].strip()
                if ct.startswith("text/html"):
                    raise OSError(f"返回的是网页而不是媒体文件（{ct}）")
                ext = _CT_EXT.get(ct) or f.ext or "bin"
                path = stem.with_suffix("." + ext)
                with open(path, "wb") as out:
                    while chunk := r.read(1 << 16):
                        out.write(chunk)
            if path.stat().st_size == 0:
                raise OSError("下载到 0 字节")
            return path
        except OSError as e:
            errors.append(f"{u[:80]}…: {e}")
    raise ExtractError("所有下载源都失败了：" + " | ".join(errors))
