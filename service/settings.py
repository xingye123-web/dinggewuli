"""服务配置，全部来自环境变量。"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _secret(name):
    """密钥只从环境变量读。Windows 开发机上，变量设置前启动的进程读不到，再查一次用户环境变量。"""
    value = os.environ.get(name, "")
    if value or os.name != "nt":
        return value
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return ""


ARTIFACTS_DIR = Path(os.environ.get("ARTIFACTS_DIR", "/data/artifacts"))
# 为空表示不校验，只允许本地开发这样用
API_TOKEN = os.environ.get("RENDER_API_TOKEN", "")
ALLOWED_ORIGINS = [o for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o]

# docker：每次渲染启动一个隔离容器。local：直接在本机运行，没有隔离，只用于开发
RUNNER = os.environ.get("RENDER_RUNNER", "docker")
ALLOW_UNSANDBOXED = os.environ.get("ALLOW_UNSANDBOXED_RENDER") == "1"
RENDERER_IMAGE = os.environ.get("RENDERER_IMAGE", "physics-renderer:0.1")
RENDER_CLIPS = int(os.environ.get("RENDER_CLIPS", "4"))
RENDER_CPUS = os.environ.get("RENDER_CPUS", "4")
RENDER_MEMORY = os.environ.get("RENDER_MEMORY", "4g")
RENDER_TMPFS = os.environ.get("RENDER_TMPFS", "4g")
RENDER_PIDS = os.environ.get("RENDER_PIDS", "256")
PREPARE_TIMEOUT = int(os.environ.get("PREPARE_TIMEOUT", "150"))
RENDER_TIMEOUT = int(os.environ.get("RENDER_TIMEOUT", "900"))
MAX_OUTPUT_BYTES = int(os.environ.get("MAX_OUTPUT_BYTES", str(300 * 1024 * 1024)))

# 这两个密钥专门用于这个项目，只有 Worker 需要，绝不传给渲染容器
DEEPSEEK_API_KEY = _secret("CHUANZHI_DEEPSEEK_API_KEY")
BREEZE_API_KEY = _secret("CHUANZHI_BREEZE_API_KEY")
DEEPSEEK_URL = os.environ.get("DEEPSEEK_URL", "https://api.deepseek.com")
# 只有 flash 能看图，所以图片题先由它转写。解题和写代码用不同的模型，答案核对才算两个独立来源
VISION_MODEL = os.environ.get("DEEPSEEK_VISION_MODEL", "deepseek-flash")
SOLVE_MODEL = os.environ.get("DEEPSEEK_SOLVE_MODEL", "deepseek-v4-pro")
AUTHOR_MODEL = os.environ.get("DEEPSEEK_AUTHOR_MODEL", "deepseek-flash")
# 实测 low 比默认的 high 快约三分之一，重写次数也没增加（7 道题：52 秒对 80 秒）
AUTHOR_EFFORT = os.environ.get("DEEPSEEK_AUTHOR_EFFORT", "low")
MAX_AUTHOR_ATTEMPTS = int(os.environ.get("MAX_AUTHOR_ATTEMPTS", "4"))
BREEZE_URL = os.environ.get("BREEZE_URL", "https://api.breeze.blue")
BREEZE_VOICE = os.environ.get("BREEZE_VOICE", "voc_xb3zjqcmwp44")  # 晨曦讲解员
BREEZE_SPEED = float(os.environ.get("BREEZE_SPEED", "0.95"))

# 服务器和笔记本的分工：服务器只收题、存结果、放视频；笔记本主动来领任务，模型和配音都在笔记本上调用
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "")  # 笔记本领任务、传结果用的令牌，服务器和笔记本要一致
INVITE_CODES = [c for c in os.environ.get("INVITE_CODES", "").split(",") if c]  # 为空表示不要邀请码
MAX_JOBS_PER_DAY = int(os.environ.get("MAX_JOBS_PER_DAY", "30"))
LEASE_SECONDS = int(os.environ.get("LEASE_SECONDS", "120"))  # 笔记本这么久没报平安，任务就退回队列
WORKER_ONLINE_SECONDS = int(os.environ.get("WORKER_ONLINE_SECONDS", "45"))
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(200 * 1024 * 1024)))
HUB_URL = os.environ.get("HUB_URL", "")  # 只在笔记本上设置，指向服务器
