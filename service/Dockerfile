# API 和 Worker 共用的镜像。这里不装 Manim，生成的代码也不在这里运行。
FROM python:3.12-slim-bookworm

# Worker 要用 docker 命令启动渲染容器
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY service/requirements.txt service/requirements.txt
RUN pip install --no-cache-dir -r service/requirements.txt

COPY service service
COPY render/__init__.py render/scene_check.py render/speech_text.py render/CATALOG.md render/
COPY render/examples render/examples
