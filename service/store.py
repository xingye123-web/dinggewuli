"""任务的文件存储。每个任务一个目录，状态存在 status.json。

服务器上它是唯一的存储；笔记本上它是本地工作目录，每次更新状态都同步给服务器（见 hub.py）。
"""

import hashlib
import json
import os
import re
import tempfile
import threading
import time
from pathlib import Path

from . import settings

_JOB_ID = re.compile(r"^[0-9a-f]{32}$")
# 这些状态表示笔记本正在处理。超过租约没报平安，说明笔记本断线了，任务退回队列
ACTIVE = {"claimed", "reading", "solving", "authoring", "checking", "narrating", "rendering", "encoding"}
_claim_lock = threading.Lock()


def job_id_for(*parts):
    """相同内容得到相同的 id，做过的题不会重复生成。"""
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:32]


def job_dir(job_id):
    if not _JOB_ID.match(job_id):
        raise ValueError("无效的任务 id")
    return Path(settings.ARTIFACTS_DIR) / job_id


def create(job_id, files):
    """新建任务并写入文件。已经存在时返回 False。"""
    directory = job_dir(job_id)
    directory.mkdir(parents=True, exist_ok=True)
    status_path = directory / "status.json"
    try:
        descriptor = os.open(status_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    for name, content in files.items():
        (directory / name).write_text(content, encoding="utf-8")
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump({"id": job_id, "status": "queued", "created_at": time.time()}, handle)
    return True


def reset(job_id):
    """把任务恢复成排队状态，清掉上次的进度。"""
    created = (read_status(job_id) or {}).get("created_at", time.time())
    write_status(job_id, {"id": job_id, "status": "queued", "created_at": created})


def read_status(job_id):
    path = job_dir(job_id) / "status.json"
    for _ in range(5):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (ValueError, PermissionError):
            time.sleep(0.05)  # Windows 下替换文件的瞬间可能读不到
    return None


def write_status(job_id, status):
    """先写临时文件再替换，读的一方不会看到写了一半的内容。"""
    directory = job_dir(job_id)
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=directory, suffix=".tmp")
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(status, handle, ensure_ascii=False)
    for attempt in range(5):
        try:
            os.replace(temporary, directory / "status.json")
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05)


def update_status(job_id, **fields):
    current = read_status(job_id) or {"id": job_id}
    current.update(fields, updated_at=time.time())
    write_status(job_id, current)
    if settings.HUB_URL:
        from . import hub

        hub.push_status(job_id, current, fields)
    return current


def _all_statuses():
    root = Path(settings.ARTIFACTS_DIR)
    if not root.exists():
        return []
    found = []
    for path in root.glob("*/status.json"):
        status = read_status(path.parent.name) if _JOB_ID.match(path.parent.name) else None
        if status:
            found.append(status)
    return found


def jobs_created_since(seconds):
    cutoff = time.time() - seconds
    return sum(1 for status in _all_statuses() if status.get("created_at", 0) >= cutoff)


def claim_next():
    """把最早排队的任务交给笔记本。断线的笔记本留下的任务也会被重新领走。"""
    now = time.time()
    with _claim_lock:
        candidates = [
            status
            for status in _all_statuses()
            if status.get("status") == "queued"
            or (status.get("status") in ACTIVE and status.get("lease_until", 0) < now)
        ]
        if not candidates:
            return None
        chosen = min(candidates, key=lambda status: status.get("created_at", 0))
        chosen.update(status="claimed", lease_until=now + settings.LEASE_SECONDS, updated_at=now)
        write_status(chosen["id"], chosen)
        return chosen


def extend_lease(job_id):
    status = read_status(job_id)
    if status and status.get("status") in ACTIVE:
        status["lease_until"] = time.time() + settings.LEASE_SECONDS
        write_status(job_id, status)
