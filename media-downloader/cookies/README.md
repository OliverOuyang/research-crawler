# cookies 放这里（不会被提交）

大多数公开内容不需要登录。只有遇到下面情况时，才把**你自己浏览器**里的 cookies 导出成 Netscape 格式（`cookies.txt`），按平台命名放进来：

| 文件名 | 什么时候需要 |
|---|---|
| `kuaishou.txt` | 快手：未登录访问会弹滑块验证（2026-10 实测必需） |
| `douyin.txt` | 抖音分享页不返回数据、退到 yt-dlp 时 |
| `xiaohongshu.txt` | 小红书提示 404/登录页时 |
| `weibo.txt` / `instagram.txt` / `tiktok.txt` / `bilibili.txt` … | yt-dlp 提示需要登录或 cookies 时 |

导出方法：Chrome 装 “Get cookies.txt LOCALLY” 扩展，在对应网站页面点导出；或用 `yt-dlp --cookies-from-browser chrome --cookies cookies/douyin.txt --skip-download <任意该站链接>`。

cookies 等于你的登录凭证，只放本机，不要发给别人或提交到仓库。
