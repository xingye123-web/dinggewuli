"""Breeze Blue 配音。按句合成，相同的句子只合成一次。只有这里持有配音密钥，渲染容器拿到的只是音频。"""

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


def align_clauses(text, tokens, seconds):
    """用逐词时间戳算出每句字幕的开始时间。对不上的地方按字数比例估算。"""
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

    clauses = []
    latest = 0.0
    for start, end in split_clauses(text):
        known = next((times[i] for i in range(start, end) if times[i] is not None), None)
        moment = known if known is not None else seconds * start / max(len(text), 1)
        latest = max(latest, moment)
        clauses.append({"text": text[start:end], "start": round(latest, 3)})
    return clauses


def synthesize(text):
    """返回 {"text", "seconds", "clauses", "audio"}，audio 是 MP3 的 base64。"""
    digest = hashlib.sha256(f"{settings.BREEZE_VOICE}|{settings.BREEZE_SPEED}|{text}".encode("utf-8")).hexdigest()
    cache = settings.ARTIFACTS_DIR / "_speech" / f"{digest}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    response = _request(text)
    audio = base64.b64decode(response["audio_base64"])
    seconds = MP3(io.BytesIO(audio)).info.length
    result = {
        "text": text,
        "seconds": round(seconds, 3),
        "clauses": align_clauses(text, response.get("word_timestamps", []), seconds),
        "audio": response["audio_base64"],
    }
    cache.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    temporary.replace(cache)
    return result


def synthesize_all(lines, on_progress=None):
    """按顺序合成。Breeze 的免费套餐同时只能合成一句。"""
    results = []
    for index, text in enumerate(lines):
        results.append(synthesize(text))
        if on_progress:
            on_progress(index + 1, len(lines))
    return results
