"""VS Codeの設定で使われるJSONC（コメントと末尾のカンマを許すJSON）を読む。"""
from __future__ import annotations

import json
import re


def _strip_comments(text: str) -> str:
    out, i, n, in_str, esc = [], 0, len(text), False, False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def loads(text: str):
    body = _strip_comments(text.lstrip("\ufeff"))
    body = re.sub(r",(\s*[}\]])", r"\1", body)
    return json.loads(body)
