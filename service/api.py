"""渲染 API：只负责收任务和查状态，真正的工作在队列后面的 Worker 里。"""

import base64
import json
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from render.scene_check import MAX_BYTES, check_code

from . import settings, store
from .tasks import problem_job, render_job

# 零件库或流程升级后，同样的输入要重新生成
PIPELINE_VERSION = "0.4.0"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 3000
_IMAGE_TYPES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"RIFF", "image/webp"),
)

app = FastAPI(title="定格物理")
if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "Range"],
        expose_headers=["Content-Range", "Accept-Ranges"],
    )


def require_token(authorization: str = Header(default="")):
    """提交任务要有令牌，否则任何人都能消耗模型额度、让服务器运行代码。"""
    if settings.API_TOKEN and not secrets.compare_digest(authorization, f"Bearer {settings.API_TOKEN}"):
        raise HTTPException(status_code=401, detail="令牌无效")


class ProblemRequest(BaseModel):
    text: str = Field(default="", max_length=MAX_TEXT_CHARS)
    image_base64: str = Field(default="", max_length=MAX_IMAGE_BYTES * 2)


class ConfirmRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_CHARS)
    figure: str = Field(default="", max_length=MAX_TEXT_CHARS)


class RenderRequest(BaseModel):
    code: str = Field(max_length=MAX_BYTES)


def _public(status):
    return {key: value for key, value in status.items() if key != "created_at"}


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


def _enqueue(job_id, task, response):
    try:
        task.delay(job_id)
    except Exception:
        store.update_status(job_id, status="failed", stage="queue", errors=["任务队列不可用"])
        raise HTTPException(status_code=503, detail="任务队列不可用") from None
    return _public(store.read_status(job_id))


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/v1/problems", status_code=202, dependencies=[Depends(require_token)])
def submit_problem(request: ProblemRequest, response: Response):
    """提交一道题（文字或图片），生成带配音的讲解视频。"""
    text = request.text.strip()
    if not text and not request.image_base64:
        raise HTTPException(status_code=422, detail="题目文字和图片至少要有一个")
    image = _image_data_url(request.image_base64) if request.image_base64 else ""

    job_id = store.job_id_for(PIPELINE_VERSION, settings.SOLVE_MODEL, settings.AUTHOR_MODEL, text, request.image_base64)
    problem = json.dumps({"text": text, "image": image}, ensure_ascii=False)
    if not store.create(job_id, {"problem.json": problem}):
        existing = store.read_status(job_id)
        if existing.get("status") != "failed":
            response.status_code = 200
            return _public(existing)
        # 失败的题再次提交时重新生成，否则会一直拿到上次的失败结果
        store.reset(job_id)
    return _enqueue(job_id, problem_job, response)


@app.post("/v1/problems/{job_id}/confirm", status_code=202, dependencies=[Depends(require_token)])
def confirm_problem(job_id: str, request: ConfirmRequest, response: Response):
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
    return _enqueue(job_id, problem_job, response)


@app.post("/v1/renders", status_code=202, dependencies=[Depends(require_token)])
def submit_code(request: RenderRequest, response: Response):
    """提交写好的场景代码，用于预置的例题和调试。"""
    # 明显不合规的代码在这里就拒绝，不占用队列
    problems = check_code(request.code)
    if problems:
        return JSONResponse(status_code=422, content={"stage": "check", "errors": problems})

    job_id = store.job_id_for(PIPELINE_VERSION, request.code)
    if not store.create(job_id, {"scene.py": request.code}):
        response.status_code = 200
        return _public(store.read_status(job_id))
    return _enqueue(job_id, render_job, response)


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
    """用户上传的题目图片，核对读图结果时对照着看。"""
    if _job_status(job_id) is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    path = store.job_dir(job_id) / "problem.json"
    image = json.loads(path.read_text(encoding="utf-8")).get("image", "") if path.exists() else ""
    if not image:
        raise HTTPException(status_code=404, detail="这道题没有图片")
    header, encoded = image.split(",", 1)
    return Response(content=base64.b64decode(encoded), media_type=header.removeprefix("data:").split(";")[0])


@app.get("/v1/renders/{job_id}/video.mp4")
def video(job_id: str):
    return _artifact(job_id, "video.mp4", "video/mp4", "video_ready")
