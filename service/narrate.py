"""Breeze Blue 配音。整段旁白一次合成，再按逐字时间戳切回每一句。

实测一次合成整段比逐句合成快一倍多（11 句：20 秒对 44 秒）。只有这里持有配音密钥，渲染容器拿到的只是音频。
"""

import base64
import hashlib
import io
import json
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
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            last_error = str(error)
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
    digest = hashlib.sha256(f"{settings.BREEZE_VOICE}|{settings.BREEZE_SPEED}|{joined}".encode("utf-8")).hexdigest()
    cache = settings.ARTIFACTS_DIR / "_speech" / f"{digest}.json"
    if cache.exists():
        result = json.loads(cache.read_text(encoding="utf-8"))
    else:
        response = _request(joined)
        audio = base64.b64decode(response["audio_base64"])
        length = MP3(io.BytesIO(audio)).info.length
        times = _char_times(joined, response.get("word_timestamps", []))

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
