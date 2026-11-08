"""笔记本和服务器之间的通信。笔记本只发出请求，不需要公网 IP。

每次更新状态都把完整状态推给服务器。状态里出现 solution_ready 这类标记时，先把对应文件传上去，
这样网页看到标记时，文件一定已经在服务器上了。
"""

import json
import time
import urllib.error
import urllib.request

from . import settings, store

ARTIFACTS = {
    "solution_ready": "solution.json",
    "timeline_ready": "timeline.json",
    "video_ready": "video.mp4",
}
MAX_TRIES = 4
TIMEOUT_SECONDS = 120


class HubError(Exception):
    pass


def _request(method, path, data=None, content_type="application/json"):
    last_error = None
    for attempt in range(MAX_TRIES):
        request = urllib.request.Request(f"{settings.HUB_URL}{path}", data=data, method=method)
        request.add_header("Authorization", f"Bearer {settings.WORKER_TOKEN}")
        request.add_header("User-Agent", "dingge-worker/0.1")
        if data is not None:
            request.add_header("Content-Type", content_type)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                body = response.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            last_error = f"HTTP {error.code}：{error.read().decode('utf-8', 'replace')[:200]}"
            if error.code < 500 and error.code != 429:
                break
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            last_error = str(error)
        time.sleep(2 ** attempt)
    raise HubError(f"连不上服务器：{last_error}")


def _post_json(path, payload):
    return _request("POST", path, json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def claim():
    """领一个任务，没有任务时返回 None。"""
    return _post_json("/v1/worker/claim", {})


def queue_length():
    """服务器上排队的题有几道。"""
    return (_request("GET", "/v1/worker/queue") or {}).get("queued", 0)


def heartbeat(job_id=None):
    _post_json("/v1/worker/heartbeat", {"job_id": job_id})


def upload(job_id, name):
    data = (store.job_dir(job_id) / name).read_bytes()
    _request("PUT", f"/v1/worker/jobs/{job_id}/files/{name}", data, "application/octet-stream")


def push_status(job_id, status, changed):
    for flag, name in ARTIFACTS.items():
        if changed.get(flag):
            upload(job_id, name)
    if changed.get("steps_ready"):
        # 先传截图，最后传 steps.json，网页拿到清单时图片都已经在服务器上
        steps = json.loads((store.job_dir(job_id) / "steps.json").read_text(encoding="utf-8"))
        for step in steps:
            upload(job_id, step["image"])
        upload(job_id, "steps.json")
    public = {key: value for key, value in status.items() if key not in ("created_at", "lease_until")}
    _post_json(f"/v1/worker/jobs/{job_id}/status", public)
