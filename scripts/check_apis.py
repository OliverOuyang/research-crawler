"""检查 Tavily 和 MiniMax 是否可用，只打印状态，不打印 key。"""
import json
import os
import urllib.request

from _env import load_env


def call(url, body=None, key_env=None):
    headers = {"Content-Type": "application/json"}
    key = os.environ.get(key_env or "")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data, headers)
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def main():
    load_env()
    try:
        u = call("https://api.tavily.com/usage", key_env="TAVILY_API_KEY")["account"]
        print(f"Tavily 可用：{u['current_plan']}，本月已用 {u['plan_usage']}/{u['plan_limit']}")
    except Exception as e:
        print(f"Tavily 不可用：{e}")
    try:
        r = call("https://api.minimaxi.com/v1/text/chatcompletion_v2",
                 {"model": "MiniMax-M2", "messages": [{"role": "user", "content": "回复 ok"}], "max_tokens": 50},
                 key_env="MINIMAX_API_KEY")
        ok = "choices" in r
        print("MiniMax 可用" if ok else f"MiniMax 返回异常：{r.get('base_resp')}")
    except Exception as e:
        print(f"MiniMax 不可用：{e}")


if __name__ == "__main__":
    main()
