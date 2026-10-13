"""命令行用法：

    python -m mediadl "整段分享文案或链接"             # 解析并下载视频/图片/Live 图
    python -m mediadl "链接" --info                    # 只解析，打印 JSON
    python -m mediadl "链接" --kinds video,cover,audio  # 选择下载哪些（video/image/live/cover/audio）
    python -m mediadl "链接" --zip                     # 额外打包成 ZIP
    python -m mediadl serve                            # 启动本地网页 http://127.0.0.1:8765
"""
from __future__ import annotations

import argparse
import json
import sys

from .core import DEFAULT_OUT, download, parse, parse_text
from .models import ExtractError


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "serve":
        from .server import serve

        ap = argparse.ArgumentParser(prog="mediadl serve")
        ap.add_argument("--host", default="127.0.0.1")
        ap.add_argument("--port", type=int, default=8765)
        a = ap.parse_args(argv[1:])
        serve(a.host, a.port)
        return 0

    ap = argparse.ArgumentParser(prog="mediadl", description="本地解析下载抖音/小红书/快手/B站/微博/TikTok/Instagram/X/Reddit 公开内容")
    ap.add_argument("text", help="链接或整段分享文案；可以包含多条链接")
    ap.add_argument("--info", action="store_true", help="只解析不下载，输出 JSON")
    ap.add_argument("--kinds", default="video,image,live", help="要下载的类型，逗号分隔：video,image,live,cover,audio")
    ap.add_argument("--zip", action="store_true", help="多个文件时额外打包 ZIP")
    ap.add_argument("-o", "--out", default=str(DEFAULT_OUT), help="保存目录")
    a = ap.parse_args(argv)

    urls = parse_text(a.text)
    if not urls:
        print("没找到受支持平台的链接（抖音/小红书/快手/B站/微博/TikTok/Instagram/X/Reddit）", file=sys.stderr)
        return 2
    code = 0
    for u in urls:
        try:
            res = parse(u)
        except ExtractError as e:
            print(f"✗ {u}\n  {e}", file=sys.stderr)
            code = 1
            continue
        if a.info:
            print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
            continue
        print(f"✓ [{res.provider}] {res.author} · {res.title}  （{len(res.files)} 个媒体，水印：{res.watermark}）")
        errs: list[str] = []
        try:
            for p in download(res, a.out, tuple(k.strip() for k in a.kinds.split(",") if k.strip()), a.zip, errs):
                print(f"  → {p}")
            for e in errs:
                print(f"  部分失败：{e}", file=sys.stderr)
                code = 1
        except ExtractError as e:
            print(f"  下载失败：{e}", file=sys.stderr)
            code = 1
    return code


if __name__ == "__main__":
    raise SystemExit(main())
