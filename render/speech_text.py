"""旁白文字的切分。渲染容器和 Worker 都要用，所以不依赖第三方库。"""

import re

_BREAK = re.compile(r"[，。；？！：,;?!:]")
MAX_CLAUSE_CHARS = 30


def _chunks(start, end, text):
    """过长的小句按字数再切开，避开数字中间。"""
    while end - start > MAX_CLAUSE_CHARS:
        cut = start + MAX_CLAUSE_CHARS
        while cut > start + 1 and (text[cut - 1].isdigit() or text[cut - 1] == "."):
            cut -= 1
        yield start, cut
        start = cut
    if end > start:
        yield start, end


def split_clauses(text):
    """按标点切成一句句字幕，返回 [(起始下标, 结束下标)]，结束下标不含标点。"""
    ranges = []
    start = 0
    for match in _BREAK.finditer(text):
        if match.start() > start:
            ranges.extend(_chunks(start, match.start(), text))
        start = match.end()
    if start < len(text):
        ranges.extend(_chunks(start, len(text), text))
    return ranges
