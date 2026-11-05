"""验证渲染容器的隔离是否真的生效。需要 Docker 和构建好的渲染镜像。

这里绕过静态检查，直接在容器里运行攻击代码，测的是隔离本身。
用法：python -m service.isolation_test
"""

import subprocess
import sys
import uuid

from . import runner, settings

CASES = [
    (
        "不能联网",
        "import socket\nsocket.create_connection(('1.1.1.1', 53), 3)\nprint('REACHED')",
    ),
    (
        "不能写程序目录",
        "open('/app/hacked', 'w').write('x')\nprint('REACHED')",
    ),
    (
        "不能写系统目录",
        "open('/etc/hacked', 'w').write('x')\nprint('REACHED')",
    ),
    (
        "工作目录不能执行程序",
        "import os, subprocess\n"
        "open('/work/run.sh', 'w').write('#!/bin/sh\\necho hi\\n')\n"
        "os.chmod('/work/run.sh', 0o755)\n"
        "subprocess.run(['/work/run.sh'], check=True)\nprint('REACHED')",
    ),
    (
        "拿不到 Docker 控制权",
        "import os\nassert not os.path.exists('/var/run/docker.sock')\nprint('SAFE')",
    ),
    (
        "不是 root",
        "import os\nassert os.getuid() == 1000\nprint('SAFE')",
    ),
    (
        "没有任何特权",
        "line = [l for l in open('/proc/self/status') if l.startswith('CapEff')][0]\n"
        "assert int(line.split()[1], 16) == 0\nprint('SAFE')",
    ),
    (
        "内存超限会被终止",
        "blocks = []\nwhile True:\n    blocks.append(bytearray(100 * 1024 * 1024))",
    ),
    (
        "不能无限创建进程",
        "import subprocess\nchildren = []\n"
        f"for i in range({int(settings.RENDER_PIDS) + 50}):\n"
        "    children.append(subprocess.Popen(['sleep', '30']))\nprint('REACHED')",
    ),
]

TIMEOUT_SECONDS = 120


def run_case(code):
    name = f"isolation-{uuid.uuid4().hex[:12]}"
    command = runner.docker_command(name)
    image = command.pop()
    command += ["--entrypoint", "python", image, "-c", code]
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


def main():
    failed = 0
    for label, code in CASES:
        result = run_case(code)
        output = result.stdout.strip()
        # 攻击代码跑到底会打印 REACHED。检查类代码打印 SAFE 才算通过
        if "SAFE" in code:
            passed = output == "SAFE"
        else:
            passed = "REACHED" not in output and result.returncode != 0
        print(f"{'通过' if passed else '失败'}  {label}（退出码 {result.returncode}）")
        if not passed:
            failed += 1
            print(f"      {output[:200]} {result.stderr.strip()[-200:]}")
    print(f"\n失败 {failed} 项")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
