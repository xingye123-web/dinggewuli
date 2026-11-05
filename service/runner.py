"""启动渲染进程，交换请求和结果。

容器和宿主机之间不共享目录：请求走标准输入，结果以 tar 从标准输出返回。
结果来自运行过不可信代码的容器，所以同样按不可信处理：只接受固定文件名的普通文件。
"""

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import uuid
from pathlib import Path

from . import settings

ALLOWED_FILES = {"result.json", "timeline.json", "video.mp4"}
_CHUNK = 1024 * 1024
_LOCAL_ENV = {"PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "TEMP", "TMP", "USERPROFILE",
              "APPDATA", "LOCALAPPDATA", "HOMEDRIVE", "HOMEPATH", "NUMBER_OF_PROCESSORS", "PROCESSOR_ARCHITECTURE"}


class RunnerError(Exception):
    pass


def docker_command(name):
    """每个参数都是一层限制。模型写的代码只在这个容器里运行。"""
    return [
        "docker", "run", "-i", "--rm", "--name", name,
        "--network", "none",
        "--read-only",
        "--tmpfs", f"/work:rw,nosuid,nodev,noexec,size={settings.RENDER_TMPFS},mode=1777",
        "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=64m,mode=1777",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--pids-limit", settings.RENDER_PIDS,
        "--memory", settings.RENDER_MEMORY,
        "--memory-swap", settings.RENDER_MEMORY,
        "--cpus", settings.RENDER_CPUS,
        "--user", "1000:1000",
        settings.RENDERER_IMAGE,
    ]


def _command(name):
    if settings.RUNNER == "docker":
        return docker_command(name)
    if settings.RUNNER == "local" and settings.ALLOW_UNSANDBOXED:
        return [sys.executable, str(settings.ROOT / "render" / "entrypoint.py")]
    raise RunnerError("RENDER_RUNNER=local 没有隔离，必须同时设置 ALLOW_UNSANDBOXED_RENDER=1")


def _environment():
    """本地模式下只传必需的环境变量，模型写的代码不能碰到 Worker 持有的密钥。容器不继承这些变量。"""
    if settings.RUNNER == "docker":
        return None
    return {key: value for key, value in os.environ.items() if key.upper() in _LOCAL_ENV or key.startswith("PHYSKIT_")}


def _stop(process, name):
    if settings.RUNNER == "docker":
        subprocess.run(["docker", "kill", name], capture_output=True)
    process.kill()


def run(request, destination, timeout, on_progress=None):
    """运行一次，把结果文件放进 destination，返回 result.json 的内容。"""
    name = f"render-{uuid.uuid4().hex[:12]}"
    process = subprocess.Popen(
        _command(name),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_environment(),
    )
    log = []
    overflow = threading.Event()

    with tempfile.TemporaryFile() as archive:
        def read_output():
            total = 0
            while chunk := process.stdout.read(_CHUNK):
                total += len(chunk)
                if total > settings.MAX_OUTPUT_BYTES:
                    overflow.set()
                    _stop(process, name)
                    return
                archive.write(chunk)

        def read_progress():
            for raw in process.stderr:
                line = raw.decode("utf-8", "replace").strip()
                log.append(line)
                del log[:-40]
                if on_progress and line.startswith("{"):
                    try:
                        on_progress(json.loads(line))
                    except ValueError:
                        pass

        def write_request():
            try:
                process.stdin.write(json.dumps(request).encode("utf-8"))
                process.stdin.close()
            except OSError:
                pass  # 进程已经退出，退出码会说明原因

        threads = [threading.Thread(target=t, daemon=True) for t in (read_output, read_progress, write_request)]
        for thread in threads:
            thread.start()
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _stop(process, name)
            process.wait()
            raise RunnerError(f"渲染超过 {timeout} 秒，已终止") from None
        for thread in threads:
            thread.join(timeout=10)

        if overflow.is_set():
            raise RunnerError(f"输出超过 {settings.MAX_OUTPUT_BYTES} 字节，已终止")
        if code != 0:
            # 137 通常表示内存超限被杀
            raise RunnerError(f"渲染进程异常退出，退出码 {code}：{' | '.join(log[-3:])[:500]}")
        archive.seek(0)
        return _extract(archive, Path(destination))


def _extract(archive, destination):
    found = set()
    try:
        with tarfile.open(fileobj=archive, mode="r:") as tar:
            for member in tar:
                if not member.isreg() or member.name not in ALLOWED_FILES or member.name in found:
                    continue
                source = tar.extractfile(member)
                temporary = destination / f".{member.name}.part"
                with open(temporary, "wb") as output:
                    shutil.copyfileobj(source, output, _CHUNK)
                temporary.replace(destination / member.name)
                found.add(member.name)
    except tarfile.TarError as error:
        raise RunnerError(f"渲染结果无法解析：{error}") from None
    if "result.json" not in found:
        raise RunnerError("渲染结果缺少 result.json")
    return json.loads((destination / "result.json").read_text(encoding="utf-8"))
