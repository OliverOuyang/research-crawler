"""极简 HTTP 工具：只用标准库。支持按平台加载用户自己导出的 cookies.txt（Netscape 格式）。"""
from __future__ import annotations

import gzip
import http.cookiejar
import os
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

# cookies 目录：默认 media-downloader/cookies/，可用环境变量 MEDIADL_COOKIES_DIR 改
COOKIES_DIR = Path(os.environ.get("MEDIADL_COOKIES_DIR", Path(__file__).resolve().parent.parent / "cookies"))


# 代理：只给需要海外出口的平台用，抖音/小红书/B站/微博照常直连。
#   MEDIADL_PROXY=http://127.0.0.1:7890
#   MEDIADL_PROXY_PLATFORMS=tiktok,instagram,twitter,reddit   （默认值）
PROXY = os.environ.get("MEDIADL_PROXY", "").strip()
PROXY_PLATFORMS = {
    p.strip() for p in os.environ.get("MEDIADL_PROXY_PLATFORMS", "tiktok,instagram,twitter,reddit").split(",") if p.strip()
}


def proxy_for(provider: str) -> str | None:
    return PROXY if PROXY and provider in PROXY_PLATFORMS else None


def cookie_file(provider: str) -> Path | None:
    p = COOKIES_DIR / f"{provider}.txt"
    return p if p.is_file() else None


class Client:
    def __init__(self, provider: str = "", ua: str = MOBILE_UA, timeout: float = 20):
        self.ua = ua
        self.timeout = timeout
        self.jar = http.cookiejar.MozillaCookieJar()
        cf = cookie_file(provider) if provider else None
        if cf:
            self.jar.load(str(cf), ignore_discard=True, ignore_expires=True)
        handlers: list = [urllib.request.HTTPCookieProcessor(self.jar)]
        px = proxy_for(provider)
        if px:
            handlers.append(urllib.request.ProxyHandler({"http": px, "https": px}))
        self.opener = urllib.request.build_opener(*handlers)

    def _req(self, url: str, headers: dict | None = None, data: bytes | None = None):
        h = {"User-Agent": self.ua, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Accept-Encoding": "gzip, deflate"}
        h.update(headers or {})
        return urllib.request.Request(url, headers=h, data=data)

    def get(self, url: str, headers: dict | None = None, retries: int = 2) -> tuple[str, str]:
        """返回 (最终 URL, 文本)。会自动跟随重定向，所以短链在这里就被展开了。网络抖动时重试。"""
        for attempt in range(retries + 1):
            try:
                return self._get_once(url, headers)
            except urllib.error.HTTPError:
                raise
            except OSError:
                if attempt == retries:
                    raise
                time.sleep(1.5 * (attempt + 1))
        raise AssertionError("unreachable")

    def _get_once(self, url: str, headers: dict | None) -> tuple[str, str]:
        with self.opener.open(self._req(url, headers), timeout=self.timeout) as r:
            body = r.read()
            enc = (r.headers.get("Content-Encoding") or "").lower()
            if enc == "gzip":
                body = gzip.decompress(body)
            elif enc == "deflate":
                body = zlib.decompress(body)
            charset = r.headers.get_content_charset() or "utf-8"
            return r.geturl(), body.decode(charset, errors="replace")

    def resolve(self, url: str) -> str:
        """只跟随短链拿到落地地址。"""
        final, _ = self.get(url)
        return final

    def stream(self, url: str, headers: dict | None = None):
        h = {"Accept-Encoding": "identity"}
        h.update(headers or {})
        return self.opener.open(self._req(url, h), timeout=max(self.timeout, 60))
