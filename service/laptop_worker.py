"""在笔记本上运行：定时向服务器领任务，跑完整流程，再把结果传回去。

模型和配音的密钥只在笔记本上，服务器拿不到。模型写的代码只在 Docker 隔离容器里运行。
用法：python -m service.laptop_worker
"""

import json
import sys
import threading
import time
import traceback

from . import hub, pipeline, settings, store

POLL_SECONDS = 5
HEARTBEAT_SECONDS = 20


def _keep_alive(job_id, stop):
    """处理任务期间定时报平安，服务器据此延长租约。"""
    while not stop.wait(HEARTBEAT_SECONDS):
        try:
            hub.heartbeat(job_id)
        except hub.HubError:
            pass  # 下一次再试，租约有余量


def _prepare_local(job):
    """把服务器上的题目放到本地工作目录，本地状态和服务器保持一致。"""
    job_id = job["id"]
    directory = store.job_dir(job_id)
    directory.mkdir(parents=True, exist_ok=True)
    if job.get("problem") is not None:
        (directory / "problem.json").write_text(json.dumps(job["problem"], ensure_ascii=False), encoding="utf-8")
    if job.get("code") is not None:
        (directory / "scene.py").write_text(job["code"], encoding="utf-8")
    if job.get("solution") is not None:
        (directory / "solution.json").write_text(json.dumps(job["solution"], ensure_ascii=False, indent=1), encoding="utf-8")
    store.write_status(job_id, job["status"])


def run_one(job):
    job_id = job["id"]
    _prepare_local(job)
    stop = threading.Event()
    keeper = threading.Thread(target=_keep_alive, args=(job_id, stop), daemon=True)
    keeper.start()
    try:
        if job.get("code") is not None:
            pipeline.run_code(job_id)
        else:
            pipeline.run_problem(job_id)
    except hub.HubError as error:
        print(f"任务 {job_id} 中途和服务器断开：{error}。服务器会在租约到期后重新派发", flush=True)
    except Exception:
        traceback.print_exc()
        try:
            store.update_status(job_id, status="failed", stage="worker", errors=["生成程序出错，请重新提交"])
        except hub.HubError:
            pass
    finally:
        stop.set()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if not settings.HUB_URL or not settings.WORKER_TOKEN:
        sys.exit("要设置 HUB_URL 和 WORKER_TOKEN")
    if settings.RUNNER != "docker":
        print("警告：没有用 Docker 隔离，模型写的代码会直接在这台电脑上运行", flush=True)
    print(f"开始向 {settings.HUB_URL} 领任务", flush=True)
    while True:
        try:
            job = hub.claim()
        except hub.HubError as error:
            print(error, flush=True)
            time.sleep(POLL_SECONDS * 3)
            continue
        if not job:
            time.sleep(POLL_SECONDS)
            continue
        print(f"领到任务 {job['id']}", flush=True)
        started = time.monotonic()
        run_one(job)
        print(f"任务 {job['id']} 结束，用时 {time.monotonic() - started:.0f} 秒", flush=True)


if __name__ == "__main__":
    main()
