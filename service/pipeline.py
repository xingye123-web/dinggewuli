"""从题目到讲解视频的完整流程：转写、解题、写代码、检查和修复、核对答案、配音、渲染。

模型写的代码只在渲染容器里运行，这里只负责调度。
"""

import json
import re
import time

from render.scene_check import check_code

from . import deepseek, narrate, part_requests, prompts, runner, settings, store
from .deepseek import DeepSeekError
from .narrate import NarrationError

_CODE_BLOCK = re.compile(r"```(?:python)?\s*\n(.*?)```", re.S)
_UNSUPPORTED = re.compile(r"^\s*UNSUPPORTED[:：]\s*(.+)", re.S)
ANSWER_TOLERANCE = 0.01  # 允许 1% 的取整误差


class PipelineStop(Exception):
    """流程到这里结束，stage 和 errors 会写进任务状态。"""

    def __init__(self, stage, errors):
        super().__init__(stage)
        self.stage = stage
        self.errors = errors


def compare_answers(expected, actual):
    """代码算出的结果和独立解答逐项比较。不一致时，两边至少有一边错了，不能发布。"""
    problems = []
    by_label = {item["label"]: item for item in actual}
    for answer in expected:
        found = by_label.get(answer["label"])
        if found is None:
            problems.append(f"没有用 timeline.answer 标记「{answer['label']}」，label 要逐字一致")
            continue
        if found["value"] is None:
            problems.append(f"「{answer['label']}」在取值时刻没有数值，检查 at 参数")
            continue
        if str(found["unit"]).replace(" ", "") != str(answer["unit"]).replace(" ", ""):
            problems.append(f"「{answer['label']}」的单位是 {found['unit']}，解答里是 {answer['unit']}，要一致")
            continue
        scale = max(abs(float(answer["value"])), 1e-9)
        if abs(float(found["value"]) - float(answer["value"])) / scale > ANSWER_TOLERANCE:
            problems.append(
                f"「{answer['label']}」代码算出 {found['value']} {found['unit']}，解答是 {answer['value']} {answer['unit']}。"
                "检查公式、取值时刻和单位换算"
            )
    return problems


class _Tracker:
    """记录用量和每一步的耗时，也用于技术文档里的评测数据。"""

    def __init__(self, job_id):
        self.job_id = job_id
        self.started = time.monotonic()
        self.stage_started = self.started
        self.stage_seconds = {}
        self.stage = None
        self.tokens = {"prompt": 0, "completion": 0, "cache_hit": 0}

    def enter(self, stage, **fields):
        now = time.monotonic()
        if self.stage:
            self.stage_seconds[self.stage] = round(now - self.stage_started, 1)
        self.stage = stage
        self.stage_started = now
        store.update_status(self.job_id, status=stage, stage_seconds=self.stage_seconds, tokens=self.tokens, **fields)

    def add_usage(self, usage):
        self.tokens["prompt"] += usage.get("prompt_tokens", 0)
        self.tokens["completion"] += usage.get("completion_tokens", 0)
        self.tokens["cache_hit"] += usage.get("prompt_cache_hit_tokens", 0)


def _read_problem(job_id, problem, tracker):
    tracker.enter("reading")
    prompt = [{"type": "text", "text": prompts.TRANSCRIBE}]
    if problem.get("text"):
        prompt.append({"type": "text", "text": f"用户补充的文字：{problem['text']}"})
    images = problem.get("images") or [problem["image"]]
    if len(images) > 1:
        prompt.append({"type": "text", "text": f"下面 {len(images)} 张照片是同一道题，按顺序合起来转写成一道题。"})
    for image in images:
        prompt.append({"type": "image_url", "image_url": {"url": image}})
    result, usage = deepseek.chat_json([{"role": "user", "content": prompt}], settings.VISION_MODEL)
    tracker.add_usage(usage)
    (store.job_dir(job_id) / "transcript.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    if not result.get("problem_text"):
        raise PipelineStop("reading", ["没有从图片里读出题目"])
    return result["problem_text"], result.get("figure", "")


def _solve(job_id, text, figure, tracker):
    tracker.enter("solving")
    content = f"题目：{text}\n\n题图信息：{figure or '无'}"
    solution, usage = deepseek.chat_json(
        [{"role": "system", "content": prompts.SOLVE}, {"role": "user", "content": content}],
        settings.SOLVE_MODEL,
        effort=settings.SOLVE_EFFORT,
    )
    tracker.add_usage(usage)
    (store.job_dir(job_id) / "solution.json").write_text(json.dumps(solution, ensure_ascii=False, indent=1), encoding="utf-8")
    # 文字解析先给用户看，不必等视频
    store.update_status(job_id, solution_ready=True)
    if not solution.get("answers"):
        raise PipelineStop("solving", [f"这道题没有得出答案：{solution.get('pitfall', '原因未知')}"])
    return solution


def _author(job_id, text, figure, solution, tracker):
    """写代码，不通过就把问题交回给模型修改。"""
    directory = store.job_dir(job_id)
    messages = [
        {"role": "system", "content": prompts.author_system(text, solution.get("topic", ""))},
        {"role": "user", "content": prompts.author_task(text, figure, solution)},
    ]
    history = []
    for attempt in range(1, settings.MAX_AUTHOR_ATTEMPTS + 1):
        tracker.enter("authoring", attempt=attempt)
        reply, usage = deepseek.chat(messages, settings.AUTHOR_MODEL, effort=settings.AUTHOR_EFFORT)
        tracker.add_usage(usage)

        unsupported = _UNSUPPORTED.match(reply)
        if unsupported:
            reason = unsupported.group(1).strip()
            part_requests.record(job_id, text, solution.get("topic", ""), unsupported=reason, attempts=attempt)
            raise PipelineStop("unsupported", [reason])
        match = _CODE_BLOCK.search(reply)
        code = match.group(1) if match else reply
        (directory / f"attempt{attempt}.py").write_text(code, encoding="utf-8")

        tracker.enter("checking", attempt=attempt)
        problems = [f"第 {p['line']} 行：{p['message']}" for p in check_code(code)]
        prepared = None
        if not problems:
            prepared = runner.run({"code": code, "mode": "prepare"}, directory, settings.PREPARE_TIMEOUT)
            if prepared.get("ok"):
                problems = compare_answers(solution["answers"], prepared["answers"])
            else:
                problems = [str(e) for e in prepared.get("errors", [])]
        history.append({"attempt": attempt, "problems": problems})
        store.update_status(job_id, attempts=history)
        if not problems:
            (directory / "scene.py").write_text(code, encoding="utf-8")
            waiting = part_requests.record(job_id, text, solution.get("topic", ""), code=code, attempts=attempt)
            if waiting:
                print(f"零件库有 {waiting} 种零件待做，见 .dev/requests/待处理.md", flush=True)
            return code, prepared

        messages.append({"role": "assistant", "content": reply})
        messages.append({"role": "user", "content": prompts.REPAIR.format(problems="\n".join(problems))})
    raise PipelineStop("authoring", problems)


def _narrate_and_render(job_id, code, prepared, tracker):
    directory = store.job_dir(job_id)
    tracker.enter("narrating", narration_total=len(prepared["narration"]))
    voice = narrate.synthesize_all(
        prepared["narration"],
        lambda done, total: store.update_status(job_id, narration_done=done),
    )
    speech = [{"text": line["text"], "seconds": line["seconds"], "clauses": line["clauses"]} for line in voice["lines"]]

    # 配音后时长才确定，要按实际时长重新算一遍时间线并再查一次布局
    final = runner.run({"code": code, "mode": "prepare", "speech": speech}, directory, settings.PREPARE_TIMEOUT)
    if not final.get("ok"):
        raise PipelineStop(final.get("stage", "layout"), final.get("errors", []))
    (directory / "narration.json").write_text(json.dumps(speech, ensure_ascii=False, indent=1), encoding="utf-8")

    tracker.enter("rendering", timeline_ready=True, frames=final["frames"], seconds=final["seconds"])
    rendered = runner.run(
        {
            "code": code,
            "mode": "render",
            "clips": settings.RENDER_CLIPS,
            "speech": speech,
            "audio": [voice["audio"]],
            "segments": [[line["from"], line["to"]] for line in voice["lines"]],
        },
        directory,
        settings.RENDER_TIMEOUT,
        lambda event: store.update_status(job_id, progress=event),
    )
    if not rendered.get("ok"):
        raise PipelineStop(rendered.get("stage", "render"), rendered.get("errors", []))
    tracker.enter("done", progress=None, video_ready=True)
    store.update_status(
        job_id,
        total_seconds=round(time.monotonic() - tracker.started, 1),
        unique_frames=rendered.get("unique_frames"),
        render_seconds=rendered.get("render_seconds"),
    )


def _guarded(job_id, work):
    try:
        work()
    except PipelineStop as stop:
        store.update_status(job_id, status="failed", stage=stop.stage, errors=stop.errors)
    except DeepSeekError as error:
        store.update_status(job_id, status="failed", stage="model", errors=[str(error)])
    except NarrationError as error:
        store.update_status(job_id, status="failed", stage="narration", errors=[str(error)])
    except runner.RunnerError as error:
        store.update_status(job_id, status="failed", stage="runner", errors=[str(error)])


def run_problem(job_id):
    """从题目开始的完整流程。"""
    problem = json.loads((store.job_dir(job_id) / "problem.json").read_text(encoding="utf-8"))

    def work():
        tracker = _Tracker(job_id)
        if (problem.get("images") or problem.get("image")) and not problem.get("confirmed"):
            # 读图可能读错，比如绳子段数。读错了后面全错，而且答案核对查不出来，所以先让用户确认
            text, figure = _read_problem(job_id, problem, tracker)
            tracker.enter("awaiting_confirmation", problem_text=text, figure=figure)
            return
        text, figure = problem["text"], problem.get("figure", "")
        store.update_status(job_id, problem_text=text, figure=figure)
        solution = _solve(job_id, text, figure, tracker)
        code, prepared = _author(job_id, text, figure, solution, tracker)
        _narrate_and_render(job_id, code, prepared, tracker)

    _guarded(job_id, work)


def run_code(job_id):
    """代码已经写好时，从检查开始。用于预置的例题和调试。"""
    code = (store.job_dir(job_id) / "scene.py").read_text(encoding="utf-8")

    def work():
        tracker = _Tracker(job_id)
        tracker.enter("checking")
        prepared = runner.run({"code": code, "mode": "prepare"}, store.job_dir(job_id), settings.PREPARE_TIMEOUT)
        if not prepared.get("ok"):
            raise PipelineStop(prepared.get("stage"), prepared.get("errors"))
        _narrate_and_render(job_id, code, prepared, tracker)

    _guarded(job_id, work)
