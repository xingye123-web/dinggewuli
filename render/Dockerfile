# 渲染镜像：官方 Manim 镜像加上中文字体、FFmpeg 和零件库。版本和本地开发环境一致。
FROM manimcommunity/manim:v0.22.1

# 官方镜像用 PyAV 写视频，不带 ffmpeg 命令，拼接和校验视频需要自己装
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-noto-cjk ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.py scene_check.py speech_text.py /app/
COPY physkit /app/physkit

ENV PHYSKIT_FONT="Noto Sans CJK SC" \
    PHYSKIT_WORK_ROOT=/work \
    HOME=/work \
    PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1

# 运行时文件系统是只读的，字体缓存要在构建时生成，并确认中文字体真的存在
RUN fc-cache -f && fc-list | grep -q "Noto Sans CJK SC"
RUN chmod -R a+rX /app

WORKDIR /work
USER 1000:1000
ENTRYPOINT ["python", "/app/entrypoint.py"]
