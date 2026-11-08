"""DeepSeek 接口。负责看图转写、解题和写场景代码。"""

import json
import time
import urllib.error
import urllib.request

from . import settings

RETRY_CODES = {429, 500, 502, 503, 504}
MAX_TRIES = 4
TIMEOUT_SECONDS = 600
MAX_TOKENS = 100000  # 含思考过程，太小会只有思考没有正文。实测难题写代码一次就可能超过 4 万


class DeepSeekError(Exception):
    pass


def chat(messages, model, json_mode=False, effort=""):
    """返回 (正文, 用量)。"""
    payload = {"model": model, "messages": messages, "max_tokens": MAX_TOKENS}
    if effort:
        payload["reasoning_effort"] = effort  # low、high、max，空表示用模型默认
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    body = json.dumps(payload).encode("utf-8")
    last_error = None
    for attempt in range(MAX_TRIES):
        request = urllib.request.Request(f"{settings.DEEPSEEK_URL}/chat/completions", data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {settings.DEEPSEEK_API_KEY}")
        request.add_header("User-Agent", "physics-explainer/0.1")
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                parsed = json.loads(response.read())
            choice = parsed["choices"][0]
            content = choice["message"].get("content") or ""
            if not content.strip():
                raise DeepSeekError(f"模型没有返回正文，结束原因 {choice.get('finish_reason')}")
            return content, parsed.get("usage", {})
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:300]
            last_error = f"HTTP {error.code}：{detail}"
            if error.code not in RETRY_CODES:
                break
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, DeepSeekError) as error:
            last_error = str(error)
        time.sleep(2 ** attempt * 2)
    raise DeepSeekError(f"调用 {model} 失败：{last_error}")


def chat_json(messages, model, effort=""):
    content, usage = chat(messages, model, json_mode=True, effort=effort)
    try:
        return json.loads(content), usage
    except ValueError as error:
        raise DeepSeekError(f"模型返回的不是合法 JSON：{error}") from None
