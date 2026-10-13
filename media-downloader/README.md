# media-downloader：本地版无水印下载器

对标 [dyxhsdownloader.com](https://dyxhsdownloader.com/#supports) 的功能（快手除外），但解析和下载都在你自己电脑上完成。
只用于下载你有权保存的**公开**内容（个人收藏、调研素材）。不绕过登录、付费、验证码或加密；需要登录态的内容，用你自己导出的 cookies。

## 支持什么

| 平台 | 内容 | 解析方式 | 2026-10-13 本机实测（[详情](docs/实测记录.md)） |
|---|---|---|---|
| 抖音 | 视频（无水印 1080p）、图集、Live 动图、封面、背景音乐 | 自研：公开分享页 `_ROUTER_DATA`，`playwm→play`；失败退回 yt-dlp | ✅ |
| 小红书 | 图文笔记原图（转 PNG）、Live 图、视频笔记 | 自研：笔记页 `__INITIAL_STATE__`，按 token 拼原图 | ✅ |
| X / Twitter | 视频（最高码率）、GIF、单图多图原图 | FixTweet 公开接口 `api.fxtwitter.com`，退回 yt-dlp | ✅ |
| Reddit | 单图、多图、Reddit 托管视频 | 图片走 `.json`，视频走 yt-dlp（合并音轨） | ✅ 视频 |
| B站 / 微博 / TikTok / Instagram | 视频 | yt-dlp | B站、微博 ✅；TikTok 要代理；Instagram 要 cookies |

和网站一样支持：粘贴整段分享文案自动抠链接、一次多条、短链跟随、备用源、全选/勾选下载、打包 ZIP、封面和背景音频单独下、最近解析记录。

## 安装（Mac）

需要 Python 3.10+（yt-dlp 的要求）和 ffmpeg（B 站等音视频分离的平台合并用）。

```bash
cd media-downloader
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # 或 uv venv && uv pip install -r requirements.txt
brew install ffmpeg   # 已装可跳过
```

## 用法

**本地网页**（最像那个网站）：

```bash
.venv/bin/python -m mediadl serve          # 打开 http://127.0.0.1:8765
```

**命令行**：

```bash
.venv/bin/python -m mediadl "7.94 复制打开抖音，看看… https://v.douyin.com/xxxx/"   # 解析并下载
.venv/bin/python -m mediadl "链接" --info                       # 只看解析结果 JSON
.venv/bin/python -m mediadl "链接" --kinds video,cover,audio    # 选类型：video,image,live,cover,audio
.venv/bin/python -m mediadl "链接1 链接2" --zip                 # 多文件额外打包
```

文件存到 `downloads/{平台}/{作者_标题_ID}/`（已被 .gitignore 排除；可用环境变量 `MEDIADL_OUT` 改位置）。

**在别的 Python 里调用**：

```python
from mediadl import parse, download
r = parse("https://www.douyin.com/video/6961737553342991651")
print(r.author, r.title, [f.kind for f in r.files])
download(r, "./downloads", kinds=("video",))
```

## 需要代理时

TikTok、Instagram、X、Reddit 可以单独走代理，其它平台照常直连（抖音、小红书走海外代理反而容易失败）：

```bash
export MEDIADL_PROXY=http://127.0.0.1:7890                        # 你的代理
export MEDIADL_PROXY_PLATFORMS=tiktok,instagram,twitter,reddit    # 默认就是这几个，可改
```

## 需要登录态时

把自己浏览器导出的 cookies.txt 放到 `cookies/{平台}.txt`，详见 [cookies/README.md](cookies/README.md)。

## 怎么来的

用 GitHub 上的 [REA（morluto/rea）](https://github.com/morluto/rea) 静态分析了网站前端，结论是：网站前端只把链接 POST 给自己的 `/api/parse`（带 Cloudflare Turnstile 验证），真正的解析都在它服务端，前端里拿不到。所以本地版没有去调用或模仿它的接口，而是按它的功能清单、链接识别规则和结果字段，用公开页面数据 + 成熟开源项目在本机重新实现。分析过程见 [docs/REA逆向分析.md](docs/REA逆向分析.md)。

## 测试

```bash
python3 -m unittest discover -s tests     # 离线单测，不联网
```

## 已知限制

- 平台页面结构和风控会变，自研解析失效时先看报错提示，必要时更新解析规则或放 cookies。
- 小红书 explore 链接必须带 `xsec_token`（App 分享链接和整段文案都带），否则会被导到 404。
- 快手不做：未登录访问一律要滑块验证，本工具不过验证码（粘快手链接会直接提示不支持）。
- 部分视频笔记（小红书拿不到 `originVideoKey` 时）只能“尽力去水印”，页面会标注。
