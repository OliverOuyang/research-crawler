from __future__ import annotations

import json
import re
from typing import Any, Iterator


def find_json_assignment(html: str, var_names: list[str]) -> Any | None:
    """从 <script>window.X = {...}</script> 里取出对象。兼容 undefined（小红书会出现）。"""
    for name in var_names:
        m = re.search(r"window\.%s\s*=\s*" % re.escape(name), html)
        if not m:
            continue
        start = html.find("{", m.end() - 1)
        raw = _balanced(html, start)
        if raw is None:
            continue
        raw = re.sub(r"(?<=[:\[,])\s*undefined\s*(?=[,}\]])", "null", raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            continue
    return None


def _balanced(s: str, start: int) -> str | None:
    if start < 0 or start >= len(s) or s[start] != "{":
        return None
    depth, in_str, esc = 0, False, False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def walk(obj: Any) -> Iterator[dict]:
    """深度遍历所有 dict，用来在结构经常变的页面数据里按特征键找目标对象。"""
    stack = [obj]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            yield o
            stack.extend(o.values())
        elif isinstance(o, list):
            stack.extend(o)


def first(*vals):
    for v in vals:
        if v:
            return v
    return None


def https(u: str | None) -> str:
    if not u:
        return ""
    return "https:" + u if u.startswith("//") else u.replace("http://", "https://", 1)
