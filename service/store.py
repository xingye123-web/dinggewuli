"""任务的文件存储。每个任务一个目录，状态存在 status.json，API 和 Worker 通过它交流。"""

import hashlib
import json
import os
import re
import tempfile
import time
from pathlib import Path

from . import settings

_JOB_ID = re.compile(r"^[0-9a-f]{32}$")


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
    """把失败的任务恢复成排队状态，清掉上次的进度。"""
    temporary = job_dir(job_id) / "status.json.tmp"
    temporary.write_text(json.dumps({"id": job_id, "status": "queued", "created_at": time.time()}), encoding="utf-8")
    os.replace(temporary, job_dir(job_id) / "status.json")


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


def update_status(job_id, **fields):
    """先写临时文件再替换，读的一方不会看到写了一半的内容。"""
    directory = job_dir(job_id)
    current = read_status(job_id) or {"id": job_id}
    current.update(fields, updated_at=time.time())
    descriptor, temporary = tempfile.mkstemp(dir=directory, suffix=".tmp")
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(current, handle, ensure_ascii=False)
    for attempt in range(5):
        try:
            os.replace(temporary, directory / "status.json")
            break
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05)
    return current
