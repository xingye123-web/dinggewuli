"""Breeze Blue 配音。整段旁白一次合成，再按逐字时间戳切回每一句。

实测一次合成整段比逐句合成快一倍多（11 句：20 秒对 44 秒）。只有这里持有配音密钥，渲染容器拿到的只是音频。
"""

import base64
import hashlib
import io
import http.client
import json
import re
import time
import urllib.error
import urllib.request

from mutagen.mp3 import MP3

from render.speech_text import split_clauses

from . import settings

RETRY_CODES = {429, 500, 502, 503, 504}
MAX_TRIES = 4
TIMEOUT_SECONDS = 120
_MAX_TOKEN_GAP = 6  # 时间戳的词和文字对不上时，最多往后找这么多字


class NarrationError(Exception):
    pass


# ---------- 数字读法 ----------
# 阿拉伯数字交给配音引擎自己读不可靠（有时逐位读、有时一带而过），送去合成前先写成中文读法，
# 比如 240 读成二百四十、2.5 读成二点五。字幕和板书仍显示阿拉伯数字。

_DIGITS = "零一二三四五六七八九"
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _four(value):
    """0 < value < 10000 的读法，比如 1100 → 一千一百，1005 → 一千零五。"""
    text, need_zero = "", False
    for power, unit in ((3, "千"), (2, "百"), (1, "十"), (0, "")):
        digit = value // 10**power % 10
        if digit == 0:
            need_zero = bool(text)
            continue
        if need_zero:
            text += "零"
            need_zero = False
        text += _DIGITS[digit] + unit
    return text


def integer_words(value):
    if value == 0:
        return "零"
    groups = [(value // 10**8, "亿"), (value // 10**4 % 10**4, "万"), (value % 10**4, "")]
    text, started, gap = "", False, False
    for number, unit in groups:
        if number == 0:
            gap = started
            continue
        if started and (gap or number < 1000):
            text += "零"
        text += _four(number) + unit
        started, gap = True, False
    # 10 到 19 读成十、十五，不读一十
    return text[1:] if text.startswith("一十") else text


def number_words(token, followed_by="", preceded_by=""):
    """一个数字串的读法。年份、0 开头的编号逐位读；量词前的 2 读「两」，序号和标号里的 2 读「二」。"""
    if "." not in token and (followed_by.startswith("年") and len(token) == 4 or len(token) > 1 and token[0] == "0"):
        return "".join(_DIGITS[int(d)] for d in token)
    whole, _, fraction = token.partition(".")
    words = integer_words(int(whole))
    is_label = preceded_by in "第接点" and preceded_by != "" or preceded_by.isascii() and preceded_by.isalpha()
    if not fraction and not is_label:
        if whole == "2" and followed_by and "一" <= followed_by <= "鿿":
            words = "两"
        elif words[:2] in ("二千", "二万", "二亿"):
            words = "两" + words[1:]
    if fraction:
        words += "点" + "".join(_DIGITS[int(d)] for d in fraction)
    return words


def spoken_digits(text):
    """把文字里的数字换成中文读法，返回 (换过的文字, 每个字对应原文的第几个字)。"""
    out, origin, cursor = [], [], 0
    for match in _NUMBER.finditer(text):
        for index in range(cursor, match.start()):
            out.append(text[index])
            origin.append(index)
        words = number_words(match.group(), text[match.end():match.end() + 1], text[match.start() - 1:match.start()])
        for k, char in enumerate(words):
            out.append(char)
            # 读法里的字按比例对回原来的数字，时间戳才能对上
            origin.append(match.start() + min(k * len(match.group()) // len(words), len(match.group()) - 1))
        cursor = match.end()
    for index in range(cursor, len(text)):
        out.append(text[index])
        origin.append(index)
    return "".join(out), origin


def _request(text):
    url = f"{settings.BREEZE_URL}/v1/text-to-speech/{settings.BREEZE_VOICE}/with-timestamps?output_format=mp3"
    payload = {"text": text, "language_code": "zh", "voice_settings": {"speed": settings.BREEZE_SPEED}}
    body = json.dumps(payload).encode("utf-8")
    last_error = None
    for attempt in range(MAX_TRIES):
        request = urllib.request.Request(url, data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header("xi-api-key", settings.BREEZE_API_KEY)
        request.add_header("User-Agent", "physics-narration/0.1")
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            last_error = f"HTTP {error.code}：{error.read().decode('utf-8', 'replace')[:200]}"
            if error.code not in RETRY_CODES:
                break
        # 回复只传了一半（IncompleteRead）或连接被重置时也再试
        except (OSError, http.client.HTTPException, ValueError) as error:
            last_error = f"{type(error).__name__}: {error}"
        time.sleep(2 ** attempt * 2)
    raise NarrationError(f"配音失败：{last_error}")


def _char_times(text, tokens):
    """把逐词时间戳摊到每个字上，对不上的字是 None。"""
    times = [None] * len(text)
    pointer = 0
    for token in tokens:
        word = token.get("word", "").strip()
        if not word:
            continue
        position = text.find(word, pointer)
        if position < 0 or position - pointer > _MAX_TOKEN_GAP:
            continue
        span = (token["end"] - token["start"]) / len(word)
        for offset in range(len(word)):
            times[position + offset] = token["start"] + span * offset
        pointer = position + len(word)
    return times


def _first_known(times, start, end):
    return next((times[i] for i in range(start, end) if times[i] is not None), None)


def synthesize_all(lines, on_progress=None):
    """整段合成，返回 {"audio": MP3 的 base64, "lines": [{"text", "seconds", "clauses", "from", "to"}]}。

    from、to 是这一句在整段音频里的起止秒数，seconds 含句后的自然停顿。相同的旁白只合成一次。
    """
    # 每句结尾补上句号，句子之间才会停顿，也不会把两句读成一句
    spoken = [line if line[-1:] in "。！？；，,.!?;" else line + "。" for line in lines]
    joined = "".join(spoken)
    digest = hashlib.sha256(f"{settings.BREEZE_VOICE}|{settings.BREEZE_SPEED}|words1|{joined}".encode("utf-8")).hexdigest()
    cache = settings.ARTIFACTS_DIR / "_speech" / f"{digest}.json"
    if cache.exists():
        result = json.loads(cache.read_text(encoding="utf-8"))
    else:
        said, origin = spoken_digits(joined)
        response = _request(said)
        audio = base64.b64decode(response["audio_base64"])
        length = MP3(io.BytesIO(audio)).info.length
        # 时间戳是按换成中文读法后的文字给的，对回原文：原文每个字取它对应的读法里最早的那个时刻
        said_times = _char_times(said, response.get("word_timestamps", []))
        times = [None] * len(joined)
        for moment, index in zip(said_times, origin):
            if moment is not None and (times[index] is None or moment < times[index]):
                times[index] = moment

        offsets = []
        cursor = 0
        for text in spoken:
            offsets.append(cursor)
            cursor += len(text)
        starts = []
        for index, text in enumerate(spoken):
            known = _first_known(times, offsets[index], offsets[index] + len(text))
            moment = known if known is not None else length * offsets[index] / max(len(joined), 1)
            starts.append(max(moment, starts[-1] if starts else 0.0))
        starts[0] = 0.0

        entries = []
        for index, line in enumerate(lines):
            begin = starts[index]
            end = starts[index + 1] if index + 1 < len(lines) else length
            clauses = []
            latest = 0.0
            for a, b in split_clauses(line):
                known = _first_known(times, offsets[index] + a, offsets[index] + b)
                moment = (known - begin) if known is not None else (end - begin) * a / max(len(line), 1)
                latest = max(latest, moment)
                clauses.append({"text": line[a:b], "start": round(latest, 3)})
            entries.append({"text": line, "seconds": round(end - begin, 3), "clauses": clauses,
                            "from": round(begin, 3), "to": round(end, 3)})
        result = {"audio": response["audio_base64"], "lines": entries}
        cache.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        temporary.replace(cache)
    if on_progress:
        on_progress(len(lines), len(lines))
    return result
