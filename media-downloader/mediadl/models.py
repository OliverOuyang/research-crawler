"""解析结果的统一结构。字段参照 dyxhsdownloader.com 结果页展示的信息（作者、描述、时长、分辨率、水印状态等）。"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class MediaFile:
    url: str
    kind: str  # video | image | live | audio | cover
    ext: str = ""
    width: int | None = None
    height: int | None = None
    backup_urls: list[str] = field(default_factory=list)  # 对应网站的“备用源”


@dataclass
class MediaResult:
    provider: str  # douyin / xiaohongshu / bilibili / weibo / tiktok / instagram / twitter / reddit
    id: str
    url: str  # 解析后的落地链接（短链跟随之后）
    title: str = ""
    desc: str = ""
    author: str = ""
    duration: float | None = None  # 秒
    # removed：确定拿到无水印源；attempted：尽力去水印；present：带水印；unknown：未知
    watermark: str = "unknown"
    files: list[MediaFile] = field(default_factory=list)
    referer: str = ""  # 部分 CDN 下载时需要带的 Referer
    extractor: str = ""  # 实际用了哪个解析器

    @property
    def videos(self) -> list[MediaFile]:
        return [f for f in self.files if f.kind == "video"]

    @property
    def images(self) -> list[MediaFile]:
        return [f for f in self.files if f.kind == "image"]

    def to_dict(self) -> dict:
        return asdict(self)


class ExtractError(Exception):
    """解析失败。message 写给用户看，尽量说清楚是链接问题、需要登录，还是被风控。"""
