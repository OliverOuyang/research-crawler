"""离线测试：不联网，验证链接识别和各平台页面数据的解析逻辑。运行：python -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mediadl.extractors import douyin, kuaishou, xiaohongshu  # noqa: E402
from mediadl.extractors._util import find_json_assignment  # noqa: E402
from mediadl.linkparse import detect_provider, extract_urls  # noqa: E402


class LinkParse(unittest.TestCase):
    def test_share_text(self):
        text = "7.94 复制打开抖音，看看【某某的作品】好看 https://v.douyin.com/iRNBho6u/ ZMw:/ 01/12 m@q.Ex"
        self.assertEqual(extract_urls(text), ["https://v.douyin.com/iRNBho6u/"])

    def test_multi_and_dedupe(self):
        text = (
            "http://xhslink.com/a/AbCdEf，复制本条信息，打开【小红书】App查看精彩内容！"
            "https://b23.tv/BV1xx https://b23.tv/BV1xx https://example.com/x"
        )
        self.assertEqual(extract_urls(text), ["http://xhslink.com/a/AbCdEf", "https://b23.tv/BV1xx"])

    def test_providers(self):
        cases = {
            "https://www.douyin.com/video/7300000000000000000": "douyin",
            "https://www.xiaohongshu.com/explore/6411cf99000000001300b6d9": "xiaohongshu",
            "https://v.kuaishou.com/abc": "kuaishou",
            "https://www.bilibili.com/video/BV1GJ411x7h7": "bilibili",
            "https://m.weibo.cn/status/123": "weibo",
            "https://vm.tiktok.com/ZM123/": "tiktok",
            "https://www.instagram.com/reel/abc/": "instagram",
            "https://x.com/user/status/1": "twitter",
            "https://www.reddit.com/r/videos/comments/abc123/title/": "reddit",
            "https://redd.it/abc123": "reddit",
            "https://www.reddit.com/r/videos/": None,
            "https://box.com/": None,
        }
        for u, p in cases.items():
            self.assertEqual(detect_provider(u), p, u)


class Util(unittest.TestCase):
    def test_json_with_undefined(self):
        html = '<script>window.__INITIAL_STATE__={"a":undefined,"b":[1,undefined],"s":"x}y"}</script>'
        self.assertEqual(find_json_assignment(html, ["__INITIAL_STATE__"]), {"a": None, "b": [1, None], "s": "x}y"})


class Douyin(unittest.TestCase):
    def test_ids(self):
        self.assertEqual(douyin.aweme_id("https://www.douyin.com/video/7300000000000000001"), "7300000000000000001")
        self.assertEqual(douyin.aweme_id("https://www.iesdouyin.com/share/note/7300000000000000002/?x=1"), "7300000000000000002")
        self.assertEqual(douyin.aweme_id("https://www.douyin.com/discover?modal_id=7300000000000000003"), "7300000000000000003")

    def test_video(self):
        item = {
            "aweme_id": "7300000000000000001",
            "desc": "测试视频",
            "author": {"nickname": "作者A"},
            "video": {
                "play_addr": {"uri": "v0200fg10000abc", "url_list": ["https://aweme.snssdk.com/aweme/v1/playwm/?video_id=v0200fg10000abc"]},
                "cover": {"url_list": ["https://p3.douyinpic.com/cover.jpeg"]},
                "duration": 15300, "width": 1080, "height": 1920,
            },
            "music": {"play_url": {"url_list": ["https://sf.douyinstatic.com/m.mp3"]}},
        }
        r = douyin.parse_item(item)
        self.assertEqual(r.watermark, "removed")
        self.assertIn("ratio=1080p", r.videos[0].url)
        self.assertTrue(all("playwm" not in u for u in r.videos[0].backup_urls))
        self.assertAlmostEqual(r.duration, 15.3)
        self.assertEqual([f.kind for f in r.files], ["video", "cover", "audio"])

    def test_images_with_live(self):
        item = {
            "aweme_id": "1", "desc": "图集", "author": {"nickname": "B"},
            "images": [
                {"url_list": ["https://p3.douyinpic.com/a.webp", "https://p9.douyinpic.com/a.jpeg"], "width": 1080, "height": 1440},
                {"url_list": ["https://p3.douyinpic.com/b.jpeg"], "video": {"play_addr": {"url_list": ["https://v.douyin.com/playwm/live.mp4"]}}},
            ],
        }
        r = douyin.parse_item(item)
        self.assertEqual([f.kind for f in r.files], ["image", "image", "live"])
        self.assertEqual(r.files[0].ext, "webp")
        self.assertEqual(r.files[2].url, "https://v.douyin.com/play/live.mp4")

    def test_find_item_in_router_data(self):
        html = '<script>window._ROUTER_DATA = {"loaderData":{"video_(id)/page":{"videoInfoRes":{"item_list":[{"aweme_id":"9","video":{}}]}}}}</script>'
        data = find_json_assignment(html, ["_ROUTER_DATA"])
        self.assertEqual(douyin._find_item(data, "9")["aweme_id"], "9")


class Xiaohongshu(unittest.TestCase):
    def test_token(self):
        u = "http://sns-webpic-qc.xhscdn.com/202410131200/0a1b2c/1040g2sg31abcdef!nd_dft_wlteh_webp_3"
        self.assertEqual(xiaohongshu.image_token(u), "1040g2sg31abcdef")

    def test_image_note(self):
        state = {"note": {"noteDetailMap": {"6411cf99000000001300b6d9": {"note": {
            "noteId": "6411cf99000000001300b6d9", "type": "normal", "title": "标题", "desc": "正文",
            "user": {"nickname": "小红"},
            "imageList": [
                {"urlDefault": "http://sns-webpic-qc.xhscdn.com/202410131200/0a1b2c/1040g2sgA!nd_dft_wlteh_webp_3", "width": 1, "height": 2},
                {"urlDefault": "http://sns-webpic-qc.xhscdn.com/202410131200/0a1b2c/1040g2sgB!nd_dft_wlteh_webp_3", "livePhoto": True,
                 "stream": {"h264": [{"masterUrl": "http://sns-video-bd.xhscdn.com/live.mp4"}]}},
            ],
        }}}}}
        note = xiaohongshu._find_note(state, "6411cf99000000001300b6d9")
        r = xiaohongshu.parse_note(note)
        self.assertEqual([f.kind for f in r.files], ["image", "image", "live"])
        self.assertEqual(r.files[0].url, "https://ci.xiaohongshu.com/1040g2sgA?imageView2/format/png")
        self.assertEqual(r.files[0].backup_urls[0], "https://ci.xiaohongshu.com/1040g2sgA")
        self.assertEqual(r.author, "小红")
        self.assertEqual(r.watermark, "removed")

    def test_video_note(self):
        note = {"noteId": "x", "type": "video", "title": "v", "user": {"nickname": "u"},
                "video": {"consumer": {"originVideoKey": "pre_post/abc"}, "capa": {"duration": 12},
                          "media": {"stream": {"h264": [{"masterUrl": "http://sns-video-bd.xhscdn.com/s.mp4", "backupUrls": ["http://b/s.mp4"]}]}}},
                "imageList": [{"urlDefault": "http://sns-webpic-qc.xhscdn.com/1/2/coverTok!x"}]}
        r = xiaohongshu.parse_note(note)
        self.assertEqual(r.videos[0].url, "https://sns-video-bd.xhscdn.com/pre_post/abc")
        self.assertEqual(r.videos[0].backup_urls, ["https://sns-video-bd.xhscdn.com/s.mp4", "https://b/s.mp4"])
        self.assertEqual([f.kind for f in r.files], ["video", "cover"])


class Kuaishou(unittest.TestCase):
    def test_video(self):
        state = {"x": {"photo": {"photoId": "3x", "caption": "快手", "userName": "老铁",
                                  "mainMvUrls": [{"url": "https://txmov2.a.kwimgs.com/a.mp4"}], "duration": 9000,
                                  "coverUrls": [{"url": "https://p1.a.yximgs.com/c.jpg"}]}}}
        r = kuaishou.parse_photo(kuaishou._find_photo(state))
        self.assertEqual(r.videos[0].url, "https://txmov2.a.kwimgs.com/a.mp4")
        self.assertEqual(r.duration, 9)
        self.assertEqual([f.kind for f in r.files], ["video", "cover"])

    def test_atlas(self):
        p = {"photoId": "1", "caption": "", "atlas": {"cdn": ["p2.a.yximgs.com"], "list": ["/a.jpg", "/b.jpg"], "music": "/m.m4a"}}
        r = kuaishou.parse_photo(p)
        self.assertEqual([f.url for f in r.images], ["https://p2.a.yximgs.com/a.jpg", "https://p2.a.yximgs.com/b.jpg"])


if __name__ == "__main__":
    unittest.main()
