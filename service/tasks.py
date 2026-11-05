"""Celery 任务。Worker 调用模型和配音接口，但不运行生成的代码，代码只在隔离容器里跑。"""

from celery import Celery

from . import pipeline, settings

app = Celery("render", broker=settings.BROKER_URL)
app.conf.update(
    task_ignore_result=True,  # 状态写在 status.json，不需要结果后端
    task_acks_late=True,  # Worker 崩溃时任务回到队列
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # 渲染很重，一次只取一个
    broker_connection_retry_on_startup=True,
    task_time_limit=3600,
)


@app.task(name="problem_job")
def problem_job(job_id):
    pipeline.run_problem(job_id)


@app.task(name="render_job")
def render_job(job_id):
    pipeline.run_code(job_id)
