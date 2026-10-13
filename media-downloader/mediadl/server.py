"""本地网页版：python -m mediadl serve，然后浏览器打开 http://127.0.0.1:8765

只用标准库。默认只监听本机。图片预览走 /api/preview 代理（很多 CDN 防盗链），
代理只放行最近一次解析结果里出现过的地址，不会变成开放代理。
"""
from __future__ import annotations

import json
import mimetypes
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .core import DEFAULT_OUT, download, parse, parse_text
from .http import DESKTOP_UA, MOBILE_UA, Client
from .linkparse import PROVIDERS
from .models import ExtractError, MediaResult

STATIC = Path(__file__).resolve().parent / "static"
OUT = Path(DEFAULT_OUT)

_lock = threading.Lock()
_results: dict[str, MediaResult] = {}  # 原始链接 -> 解析结果
_allowed: dict[str, tuple[str, str]] = {}  # 媒体地址 -> (referer, 平台)（预览代理白名单）


def _remember(src: str, res: MediaResult) -> None:
    with _lock:
        _results[src] = res
        for f in res.files:
            for u in [f.url, *f.backup_urls]:
                _allowed[u] = (res.referer or "", res.provider)


class Handler(BaseHTTPRequestHandler):
    server_version = "mediadl"

    def log_message(self, fmt, *args):  # 安静一点
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path in ("/", "/index.html"):
            return self._file(STATIC / "index.html")
        if u.path == "/api/providers":
            return self._json(PROVIDERS)
        if u.path == "/api/preview":
            return self._preview(urllib.parse.parse_qs(u.query).get("u", [""])[0])
        if u.path.startswith("/files/"):
            rel = urllib.parse.unquote(u.path[len("/files/") :])
            p = (OUT / rel).resolve()
            if OUT.resolve() in p.parents and p.is_file():
                return self._file(p, attachment=True)
        self.send_error(404)

    def do_POST(self):
        try:
            if self.path == "/api/parse":
                return self._parse(self._body())
            if self.path == "/api/download":
                return self._download(self._body())
        except ExtractError as e:
            return self._json({"error": str(e)}, 400)
        except Exception as e:  # 本地工具，直接把错误给到页面
            return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
        self.send_error(404)

    def _parse(self, body: dict):
        urls = parse_text(body.get("text", ""))
        if not urls:
            return self._json({"error": "没找到受支持平台的链接（抖音/小红书/B站/微博/TikTok/Instagram/X/Reddit）"}, 400)
        out = []
        for src in urls:
            try:
                res = parse(src)
                _remember(src, res)
                out.append({"source": src, "result": res.to_dict()})
            except ExtractError as e:
                out.append({"source": src, "error": str(e)})
        return self._json({"items": out})

    def _download(self, body: dict):
        src = body.get("source", "")
        with _lock:
            res = _results.get(src)
        if res is None:  # 服务重启过或没解析过：重新解析
            res = parse(src)
            _remember(src, res)
        kinds = tuple(body.get("kinds") or ("video", "image", "live"))
        only = body.get("only")  # 只下载某一个文件：传它在 files 里的下标
        if only is not None:
            f = res.files[int(only)]
            res = MediaResult(**{**res.__dict__, "files": [f]})
            kinds = (f.kind,)
        errs: list[str] = []
        paths = download(res, OUT, kinds, bool(body.get("zip")), errs)
        return self._json(
            {"errors": errs, "files": [{"name": p.name, "href": "/files/" + urllib.parse.quote(str(p.relative_to(OUT))), "path": str(p)} for p in paths]}
        )

    def _preview(self, url: str):
        with _lock:
            entry = _allowed.get(url)
        if entry is None:
            return self.send_error(403, "only URLs from a recent parse can be previewed")
        ref, provider = entry
        ua = MOBILE_UA if provider == "douyin" else DESKTOP_UA
        try:
            with Client(provider, ua=ua).stream(url, headers={"Referer": ref} if ref else None) as r:
                self.send_response(200)
                self.send_header("Content-Type", r.headers.get("Content-Type") or "application/octet-stream")
                if r.headers.get("Content-Length"):
                    self.send_header("Content-Length", r.headers["Content-Length"])
                self.send_header("Cache-Control", "max-age=300")
                self.end_headers()
                while chunk := r.read(1 << 16):
                    self.wfile.write(chunk)
        except OSError as e:
            if not self.wfile.closed:
                try:
                    self.send_error(502, str(e)[:200])
                except OSError:
                    pass

    def _file(self, p: Path, attachment: bool = False):
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(p.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        if attachment:
            self.send_header("Content-Disposition", "attachment; filename*=UTF-8''" + urllib.parse.quote(p.name))
        self.end_headers()
        self.wfile.write(data)


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"本地下载器已启动：http://{host}:{port}   文件保存在 {OUT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
