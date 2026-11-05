"""用正式流程的检查跑一份场景代码，可选渲染成视频（不配音）。

用法（在项目根目录）：
    .venv/Scripts/python scripts/check_scene.py render/examples/lever.py
    .venv/Scripts/python scripts/check_scene.py render/examples/lever.py --render
结果放在 .dev/try/<文件名>/ 下。需要 Docker 和渲染镜像。
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
os.environ.setdefault("RENDER_RUNNER", "docker")
docker_bin = r"C:\Program Files\Docker\Docker\resources\bin"
if os.path.isdir(docker_bin) and docker_bin not in os.environ["PATH"]:
    os.environ["PATH"] += os.pathsep + docker_bin

from render.scene_check import check_code  # noqa: E402
from service import runner, settings  # noqa: E402


def main():
    path = Path(sys.argv[1])
    code = path.read_text(encoding="utf-8")
    out = ROOT / ".dev" / "try" / path.stem
    out.mkdir(parents=True, exist_ok=True)

    problems = [f"第 {p['line']} 行：{p['message']}" for p in check_code(code)]
    if problems:
        print("静态检查没通过：", *problems, sep="\n  ")
        return 1
    prepared = runner.run({"code": code, "mode": "prepare"}, out, settings.PREPARE_TIMEOUT)
    if not prepared.get("ok"):
        print(f"布局或时间线没通过（{prepared.get('stage')}）：", *prepared.get("errors", []), sep="\n  ")
        return 1
    print("检查通过。答案：", json.dumps(prepared["answers"], ensure_ascii=False))
    print(f"约 {prepared['seconds']:.0f} 秒，旁白 {sum(len(t) for t in prepared['narration'])} 字")
    if "--render" in sys.argv:
        rendered = runner.run({"code": code, "mode": "render", "clips": settings.RENDER_CLIPS}, out, settings.RENDER_TIMEOUT)
        if not rendered.get("ok"):
            print("渲染失败：", *rendered.get("errors", []), sep="\n  ")
            return 1
        print(f"视频：{out / 'video.mp4'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
