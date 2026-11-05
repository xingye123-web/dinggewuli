"""端到端冒烟测试：不经过模型，直接把示例代码和几种错误代码提交给运行中的服务。

示例会实际合成配音，相同的句子有缓存。
用法：python -m service.smoke_test
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = os.environ.get("API", "http://127.0.0.1:8000")
TOKEN = os.environ.get("RENDER_API_TOKEN", "")
EXAMPLES = Path(__file__).resolve().parent.parent / "render" / "examples"
POLL_SECONDS = 1
WAIT_SECONDS = 500

CASES = [("circuit", {"I": 0.2, "U1": 2, "P1": 0.4})]

failures = []


def check(label, passed, detail=""):
    print(f"{'通过' if passed else '失败'}  {label}{'  ' + str(detail) if detail else ''}")
    if not passed:
        failures.append(label)


def call(path, payload=None, token=TOKEN, headers=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(API + path, data=data, method="POST" if data else "GET")
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def call_json(path, payload=None, **kwargs):
    code, body, _ = call(path, payload, **kwargs)
    return code, json.loads(body)


def wait_for(job_id):
    started = time.monotonic()
    while time.monotonic() - started < WAIT_SECONDS:
        _, status = call_json(f"/v1/renders/{job_id}")
        if status["status"] in ("done", "failed"):
            return status, time.monotonic() - started
        time.sleep(POLL_SECONDS)
    raise TimeoutError(job_id)


def scene_code(body, prefix=""):
    """最小的合规代码，再拼上要测试的部分。"""
    return (
        prefix + "from physkit import *\n"
        "timeline = Timeline('测试题')\n"
        "main = timeline.phase('过程', min_seconds=2)\n"
        "main.say('这是一句测试旁白。')\n"
        "timeline.quantity('x', 'x', '位移', 'm', 2, lambda f: main.progress(f))\n"
        "timeline.show_clock('x', '位移')\n"
        "stage = Stage(timeline)\n" + body
    )


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if TOKEN:
        code, _ = call_json("/v1/renders", {"code": "x = 1"}, token="wrong")
        check("没有正确令牌时拒绝提交", code == 401, code)
        code, _ = call_json("/v1/problems", {"text": "题目"}, token="wrong")
        check("没有正确令牌时拒绝提交题目", code == 401, code)

    code, _ = call_json("/v1/problems", {"text": ""})
    check("题目文字和图片都没有时拒绝", code == 422, code)
    code, _ = call_json("/v1/problems", {"image_base64": "bm90IGFuIGltYWdl"})
    check("不是图片的内容被拒绝", code == 422, code)

    for label, source, needle in [
        ("拒绝导入 os", scene_code("", "import os\n"), "os"),
        ("拒绝从子模块绕过", scene_code("", "import physkit.parts\n"), "physkit"),
        ("拒绝 from physkit.parts 绕过", scene_code("", "from physkit.parts import os\n"), "physkit"),
        ("拒绝只导入部分名字", scene_code("", "from physkit import Timeline\n"), "physkit"),
        ("拒绝 open", scene_code("data = open('/etc/passwd').read()\n"), "open"),
        ("拒绝双下划线属性", scene_code("c = ().__class__\n"), "__class__"),
        ("拒绝 while", scene_code("while True:\n    pass\n"), "While"),
        ("拒绝字符串 format 绕过", scene_code("s = '{0.a}'.format(1)\n"), "format"),
        ("拒绝依赖动画时间的代码", scene_code("stage.add(Readout(lambda f: str(f.clock), 0, 0))\n"), "clock"),
    ]:
        code, body = call_json("/v1/renders", {"code": source})
        check(label, code == 422 and needle in json.dumps(body, ensure_ascii=False), code)

    code, _, _ = call("/v1/renders/not-a-valid-id")
    check("无效任务 id 返回 404", code == 404, code)
    code, _, _ = call("/v1/renders/..%2F..%2Fsecret/timeline.json")
    check("路径穿越返回 404", code == 404, code)

    for label, body, stage, needle in [
        ("布局：文字超出画面", "stage.add(Readout('超出画面的文字', -7.0, 0))\n", "layout", "超出画面"),
        ("布局：进入板书区", "stage.add(Block(2, 0, 1, 1))\n", "layout", "板书区"),
        ("布局：进入字幕区", "stage.add(Block(-3, -3.3, 1, 1))\n", "layout", "字幕区"),
        (
            "布局：文字互相重叠",
            "stage.add(Readout('第一段文字', -3, 0), Readout('第二段文字', -3, 0))\n",
            "layout",
            "重叠",
        ),
        ("布局：物块放不下文字", "stage.add(Block(-3, 0, 0.3, 0.3, text='放不下的长文字'))\n", "layout", "放不下"),
        (
            "布局：绳子是斜的",
            "a = Pulley(-4, 2)\nstage.add(a, Rope([(-5, 0), Over(a), (-2, 0)]))\n",
            "layout",
            "斜",
        ),
        ("运行错误：引用没声明的量", "stage.add(Readout(lambda f: str(f.nope), -3, 0))\n", "scene", "nope"),
        ("运行错误：show 引用没声明的量", "stage.add(Block(-3, 0, 1, 1, name='甲', show=['nope']))\n", "scene", "nope"),
    ]:
        _, submitted = call_json("/v1/renders", {"code": scene_code(body)})
        status, _ = wait_for(submitted["id"])
        passed = (
            status["status"] == "failed"
            and status.get("stage") == stage
            and needle in json.dumps(status.get("errors"), ensure_ascii=False)
        )
        check(label, passed, str((status.get("errors") or [""])[0])[:90])

    for name, expected in CASES:
        source = (EXAMPLES / f"{name}.py").read_text(encoding="utf-8")
        code, submitted = call_json("/v1/renders", {"code": source})
        status, total = wait_for(submitted["id"])
        check(f"{name} 渲染完成", status["status"] == "done", status.get("errors") or "")
        if status["status"] != "done":
            continue
        print(f"      视频 {total:.1f} 秒可用（提交时状态码 {code}）")

        _, timeline = call_json(f"/v1/renders/{submitted['id']}/timeline.json")
        answers = {a["id"]: a["value"] for a in timeline["answers"]}
        for key, value in expected.items():
            check(f"{name} 的 {key} = {value}", answers.get(key) == value, answers.get(key))
        check(f"{name} 帧数和状态一致", len(timeline["frames"][timeline["clock"]["id"]]) == status["frames"])

        code, chunk, _ = call(f"/v1/renders/{submitted['id']}/video.mp4", headers={"Range": "bytes=0-99"})
        check(f"{name} 视频支持拖动", code == 206 and len(chunk) == 100, code)

        code, again = call_json("/v1/renders", {"code": source})
        check(f"{name} 重复提交直接复用结果", code == 200 and again["status"] == "done", code)

    print(f"\n失败 {len(failures)} 项" + (f"：{failures}" if failures else ""))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
