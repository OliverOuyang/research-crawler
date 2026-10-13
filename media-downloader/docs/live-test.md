# 实测记录（2026-10-13，Oliver 的 Mac，国内网络，未放任何 cookies）

用 `live_check` 脚本对每个平台各取一条公开链接，跑“解析 → 下载 → ffprobe 检查”。

| 平台 | 结果 | 解析器 | 产出 | 备注 |
|---|---|---|---|---|
| 抖音（视频） | ✅ | 分享页 | 1080×1920 MP4，6.1 MB，带音轨 | 抽帧检查无抖音水印 |
| 小红书（图文 4 张） | ✅ | 笔记页 | 4 张 PNG 原图（1320×2868）+ ZIP | 抽查无水印 |
| 小红书（视频） | ✅ | 笔记页 | 720×960 MP4，36 MB | 该笔记没有 originVideoKey，标为“尽力去除” |
| 快手 | ❌ 需 cookies | 分享页 + GraphQL | — | 未登录访问一律返回滑块验证（400002），已给出明确提示 |
| B站 | ✅ | yt-dlp | 1920×1080 MP4，21 MB（音视频已合并） | 需要 ffmpeg |
| 微博 | ✅ | yt-dlp | 1920×1080 MP4，113 MB | |
| X / Twitter | ✅ | FixTweet | 728×720 MP4 | |
| Reddit（视频） | ✅ | yt-dlp | 352×640 MP4，带音轨 | |
| TikTok | ❌ 网络 | yt-dlp | — | “Your IP address is blocked”：国内 IP 被 TikTok 拒绝，开代理后再试 |
| Instagram | ❌ 需 cookies | yt-dlp | — | Instagram 对未登录返回空数据，放 `cookies/instagram.txt` |

本地网页（`python -m mediadl serve`）在 Mac 上也跑通：整段文案里抠出抖音链接、忽略无关链接、下载封面并通过 `/files/` 取回。

云端容器里另测了：抖音可解析下载（偶发连接被重置）、X 视频、Reddit/B站解析；离线单测 13 条全过。

## 代理

`urllib` 和 yt-dlp 都会读环境变量里的代理，TikTok / Instagram / X 在国内需要时：

```bash
export HTTPS_PROXY=http://127.0.0.1:7890   # 换成你自己的代理端口
.venv/bin/python -m mediadl serve
```

## VPS（2026-10-13，Hostinger 美国机房，未放 cookies）

| 平台 | 结果 | 备注 |
|---|---|---|
| TikTok | ✅ | 需要 `curl-cffi`（已写进 requirements），直连和走 7890 代理都能下 |
| X / Twitter | ✅ | |
| 抖音 | ✅ 大多数 | 6 次里 5 次成功，已加自动重试 |
| 小红书 | ❌ 需 cookies | 美国 IP 访问笔记页会被跳到登录页 |
| Instagram | ❌ 需 cookies | 未登录返回空数据 |
| 快手 | 已移除 | |
