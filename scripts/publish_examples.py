"""把首页例题提交到线上生成。代码是 render/examples 里的示例，解析在 render/examples/showcase.json。

例题走「直接交代码」的接口，不调用 DeepSeek，只配音和渲染。同一份代码只会生成一次，重复提交拿到的是同一个任务号。
提交线上时，令牌在服务器上读取，不经过本机。

用法（在项目根目录）：
    python scripts/publish_examples.py           提交到线上，打印每道例题的任务号
    python scripts/publish_examples.py --local   提交到本机 127.0.0.1:8000，令牌用 .dev/token.txt
任务号填进 web/lib/examples.ts。
"""

import ast
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "render" / "examples"
SERVER = "ubuntu@43.132.151.127"
KEY = Path.home() / ".ssh" / "dingge_server"
REMOTE = (
    "T=$(sudo grep ^RENDER_API_TOKEN= /etc/dingge/api.env | cut -d= -f2-); "
    'curl -s -X POST http://127.0.0.1:8000/v1/renders -H "Authorization: Bearer $T" '
    '-H "Content-Type: application/json" --data-binary @-'
)


def problem_text(code):
    """示例代码里 Timeline 的第一个参数就是题目原文。"""
    for node in ast.walk(ast.parse(code)):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Timeline":
            return ast.literal_eval(node.args[0])
    raise ValueError("没有找到 Timeline(...)")


def post_remote(payload):
    result = subprocess.run(
        ["ssh", "-i", str(KEY), "-o", "BatchMode=yes", SERVER, REMOTE],
        input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout.decode("utf-8"))


def post_local(payload):
    token = (ROOT / ".dev" / "token.txt").read_text(encoding="utf-8").strip()
    request = urllib.request.Request(
        "http://127.0.0.1:8000/v1/renders",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    post = post_local if "--local" in sys.argv else post_remote
    showcase = json.loads((EXAMPLES / "showcase.json").read_text(encoding="utf-8"))
    for example in showcase["examples"]:
        code = (EXAMPLES / example["file"]).read_text(encoding="utf-8")
        payload = {"code": code, "problem_text": problem_text(code), "solution": example["solution"]}
        job = post(payload)
        if "id" not in job:
            print(f"{example['file']}  提交失败：{job}")
            continue
        print(f"{example['file']}  {job['id']}  {job.get('status')}")


if __name__ == "__main__":
    main()
