"""服务器上的接口：网页提交题目、查询状态、取结果；笔记本领任务、报进度、传结果。

服务器不调用模型，也不运行生成的代码，这些都在笔记本上完成。
"""

import base64
import json
import os
import secrets
import tempfile
import time

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from render.scene_check import MAX_BYTES, check_code

from . import settings, store

# 零件库或流程升级后，同样的输入要重新生成
PIPELINE_VERSION = "0.4.0"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGES = 4  # 题目文字和题图常常不在一页上，允许分几张拍
MAX_TEXT_CHARS = 3000
_IMAGE_TYPES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"RIFF", "image/webp"),
)
_WORKER_FILE = "_worker.json"
# 笔记本能上传的文件，网页只会读其中几个
_UPLOADS = {"solution.json", "timeline.json", "video.mp4", "transcript.json", "narration.json", "scene.py"}
# 笔记本推送状态时不能改的字段
_SERVER_FIELDS = {"id", "created_at", "lease_until"}

app = FastAPI(title="定格物理")


def require_token(authorization: str = Header(default="")):
    """提交任务要有令牌，否则任何人都能消耗模型额度。网页的服务端持有它，浏览器拿不到。"""
    if settings.API_TOKEN and not secrets.compare_digest(authorization, f"Bearer {settings.API_TOKEN}"):
        raise HTTPException(status_code=401, detail="令牌无效")


def require_worker(authorization: str = Header(default="")):
    """只有笔记本能领任务和上传结果。没配置令牌时一律拒绝。"""
    if not settings.WORKER_TOKEN or not secrets.compare_digest(authorization, f"Bearer {settings.WORKER_TOKEN}"):
        raise HTTPException(status_code=401, detail="令牌无效")


class ProblemRequest(BaseModel):
    text: str = Field(default="", max_length=MAX_TEXT_CHARS)
    image_base64: str = Field(default="", max_length=MAX_IMAGE_BYTES * 2)  # 旧版网页只传一张
    images_base64: list[str] = Field(default_factory=list, max_length=MAX_IMAGES)
    invite: str = Field(default="", max_length=100)


class ConfirmRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    figure: str = Field(default="", max_length=MAX_TEXT_CHARS)


class RenderRequest(BaseModel):
    code: str = Field(max_length=MAX_BYTES)
    # 预置例题时一起交题目原文和写好的文字解析，讲解页和普通题目显示得一样
    problem_text: str = Field(default="", max_length=3000)
    solution: dict | None = None


MAX_SOLUTION_CHARS = 20000


def _public(status):
    return {key: value for key, value in status.items() if key not in ("created_at", "lease_until")}


def _job_status(job_id):
    try:
        return store.read_status(job_id)
    except ValueError:
        return None


def _image_data_url(encoded):
    try:
        data = base64.b64decode(encoded, validate=True)
    except ValueError:
        raise HTTPException(status_code=422, detail="图片不是合法的 base64") from None
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=422, detail="图片不能超过 8 MB")
    for magic, mime in _IMAGE_TYPES:
        if data.startswith(magic):
            return f"data:{mime};base64,{encoded}"
    raise HTTPException(status_code=422, detail="只支持 PNG、JPEG 和 WebP 图片")


def _worker_seen():
    try:
        return json.loads((settings.ARTIFACTS_DIR / _WORKER_FILE).read_text(encoding="utf-8")).get("last_seen", 0)
    except (OSError, ValueError):
        return 0


def _mark_worker_seen():
    settings.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    (settings.ARTIFACTS_DIR / _WORKER_FILE).write_text(json.dumps({"last_seen": time.time()}), encoding="utf-8")


def _check_quota(invite):
    if settings.INVITE_CODES and not any(secrets.compare_digest(invite, code) for code in settings.INVITE_CODES):
        raise HTTPException(status_code=403, detail="邀请码不对")
    if store.jobs_created_since(24 * 3600) >= settings.MAX_JOBS_PER_DAY:
        raise HTTPException(status_code=429, detail="今天的生成次数已经用完，请明天再来")


@app.get("/healthz")
def healthz():
    """worker_online 表示笔记本最近来领过任务，网页据此提示现在能不能生成新题。"""
    return {"ok": True, "worker_online": time.time() - _worker_seen() < settings.WORKER_ONLINE_SECONDS}


@app.post("/v1/problems", status_code=202, dependencies=[Depends(require_token)])
def submit_problem(request: ProblemRequest, response: Response):
    """提交一道题（文字或图片），生成带配音的讲解视频。"""
    text = request.text.strip()
    encoded = [item for item in request.images_base64 if item] or ([request.image_base64] if request.image_base64 else [])
    if not text and not encoded:
        raise HTTPException(status_code=422, detail="题目文字和图片至少要有一个")
    if any(len(item) > MAX_IMAGE_BYTES * 2 for item in encoded):
        raise HTTPException(status_code=422, detail="图片不能超过 8 MB")
    images = [_image_data_url(item) for item in encoded]

    # 只有一张图时和旧版的任务号一样，做过的题不会重做
    job_id = store.job_id_for(PIPELINE_VERSION, settings.SOLVE_MODEL, settings.AUTHOR_MODEL, text, *(encoded or [""]))
    existing = _job_status(job_id)
    if existing and existing.get("status") != "failed":
        # 做过的题直接给结果，不占用次数
        response.status_code = 200
        return _public(existing)
    _check_quota(request.invite)
    if existing:
        # 失败的题再次提交时重新生成，否则会一直拿到上次的失败结果
        store.reset(job_id)
    else:
        problem = {"text": text, "image": images[0] if images else "", "images": images}
        store.create(job_id, {"problem.json": json.dumps(problem, ensure_ascii=False)})
        if images:
            store.update_status(job_id, image_count=len(images))
    return _public(store.read_status(job_id))


@app.post("/v1/problems/{job_id}/confirm", status_code=202, dependencies=[Depends(require_token)])
def confirm_problem(job_id: str, request: ConfirmRequest):
    """用户核对过读图结果后，按确认的内容继续解题。"""
    found = _job_status(job_id)
    if found is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if found.get("status") != "awaiting_confirmation":
        raise HTTPException(status_code=409, detail="这道题不在等待确认的状态")
    path = store.job_dir(job_id) / "problem.json"
    problem = json.loads(path.read_text(encoding="utf-8"))
    problem.update(text=request.text.strip(), figure=request.figure.strip(), confirmed=True)
    path.write_text(json.dumps(problem, ensure_ascii=False), encoding="utf-8")
    store.reset(job_id)
    return _public(store.read_status(job_id))


@app.post("/v1/renders", status_code=202, dependencies=[Depends(require_token)])
def submit_code(request: RenderRequest, response: Response):
    """提交写好的场景代码，用于预置的例题和调试。"""
    # 明显不合规的代码在这里就拒绝，不占用队列
    problems = check_code(request.code)
    if problems:
        return JSONResponse(status_code=422, content={"stage": "check", "errors": problems})

    files = {"scene.py": request.code}
    if request.solution is not None:
        solution = json.dumps(request.solution, ensure_ascii=False, indent=1)
        if len(solution) > MAX_SOLUTION_CHARS:
            raise HTTPException(status_code=422, detail="文字解析太长")
        files["solution.json"] = solution

    job_id = store.job_id_for(PIPELINE_VERSION, request.code)
    if store.create(job_id, files):
        if request.problem_text.strip() or request.solution is not None:
            store.update_status(
                job_id, problem_text=request.problem_text.strip(), solution_ready=request.solution is not None
            )
    else:
        response.status_code = 200
    return _public(store.read_status(job_id))


@app.get("/v1/renders/{job_id}")
def status(job_id: str):
    found = _job_status(job_id)
    if found is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _public(found)


def _artifact(job_id, name, media_type, flag):
    found = _job_status(job_id)
    if found is None or not found.get(flag):
        raise HTTPException(status_code=404, detail="结果还没有生成")
    return FileResponse(store.job_dir(job_id) / name, media_type=media_type)


@app.get("/v1/renders/{job_id}/timeline.json")
def timeline(job_id: str):
    return _artifact(job_id, "timeline.json", "application/json", "timeline_ready")


@app.get("/v1/renders/{job_id}/solution.json")
def solution(job_id: str):
    return _artifact(job_id, "solution.json", "application/json", "solution_ready")


@app.get("/v1/renders/{job_id}/image")
def problem_image(job_id: str):
    return problem_image_at(job_id, 0)


@app.get("/v1/renders/{job_id}/images/{index}")
def problem_image_at(job_id: str, index: int):
    """用户上传的题目图片，核对读图结果时对照着看。index 从 0 开始。"""
    if _job_status(job_id) is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    path = store.job_dir(job_id) / "problem.json"
    problem = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    images = problem.get("images") or ([problem["image"]] if problem.get("image") else [])
    if not 0 <= index < len(images):
        raise HTTPException(status_code=404, detail="这道题没有这张图片")
    image = images[index]
    header, encoded = image.split(",", 1)
    return Response(content=base64.b64decode(encoded), media_type=header.removeprefix("data:").split(";")[0])


@app.get("/v1/renders/{job_id}/video.mp4")
def video(job_id: str):
    return _artifact(job_id, "video.mp4", "video/mp4", "video_ready")


@app.post("/v1/worker/heartbeat", dependencies=[Depends(require_worker)])
async def worker_heartbeat(request: Request):
    _mark_worker_seen()
    body = await request.json()
    job_id = body.get("job_id") if isinstance(body, dict) else None
    if job_id and _job_status(job_id):
        store.extend_lease(job_id)
    return {"ok": True}


@app.post("/v1/worker/claim", dependencies=[Depends(require_worker)])
def worker_claim():
    """把最早排队的任务交给笔记本，连同题目或代码一起。"""
    _mark_worker_seen()
    status = store.claim_next()
    if status is None:
        return None
    directory = store.job_dir(status["id"])
    problem = directory / "problem.json"
    code = directory / "scene.py"
    return {
        "id": status["id"],
        "status": status,
        "problem": json.loads(problem.read_text(encoding="utf-8")) if problem.exists() else None,
        "code": code.read_text(encoding="utf-8") if code.exists() and not problem.exists() else None,
    }


@app.post("/v1/worker/jobs/{job_id}/status", dependencies=[Depends(require_worker)])
async def worker_status(job_id: str, request: Request):
    found = _job_status(job_id)
    if found is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="状态要是一个对象")
    found.update({key: value for key, value in body.items() if key not in _SERVER_FIELDS})
    found["lease_until"] = time.time() + settings.LEASE_SECONDS
    store.write_status(job_id, found)
    _mark_worker_seen()
    return {"ok": True}


@app.put("/v1/worker/jobs/{job_id}/files/{name}", dependencies=[Depends(require_worker)])
async def worker_upload(job_id: str, name: str, request: Request):
    if name not in _UPLOADS:
        raise HTTPException(status_code=422, detail="不接受这个文件")
    if _job_status(job_id) is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    directory = store.job_dir(job_id)
    descriptor, temporary = tempfile.mkstemp(dir=directory, suffix=".upload")
    size = 0
    with os.fdopen(descriptor, "wb") as handle:
        async for chunk in request.stream():
            size += len(chunk)
            if size > settings.MAX_UPLOAD_BYTES:
                break
            handle.write(chunk)
    if size > settings.MAX_UPLOAD_BYTES:
        os.unlink(temporary)
        raise HTTPException(status_code=413, detail="文件太大")
    os.replace(temporary, directory / name)
    return {"ok": True, "bytes": size}
