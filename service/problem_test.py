"""用真实题目跑完整流程，会实际消耗模型和配音额度。

用法：python -m service.problem_test 题目名 [题目名 ...]，不写题目名就跑全部。
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = os.environ.get("API", "http://127.0.0.1:8000")
TOKEN = os.environ.get("RENDER_API_TOKEN", "")
WAIT_SECONDS = 1800
SAMPLES = Path(__file__).resolve().parent / "test_problems"

# 期望答案由人核对过，用来判断模型的解答和动画是否真的对
PROBLEMS = {
    "text_pulley_n2": {
        "title": "文字题：滑轮组，向下拉",
        "text": "工人用如图所示的滑轮组把重 400 N 的货物在 15 s 内匀速提升 3 m，绳端向下的拉力为 250 N，"
        "动滑轮上有 2 段绳子承担重物。不计绳重和摩擦。求：(1) 拉力做的总功；(2) 拉力的功率；(3) 滑轮组的机械效率；(4) 动滑轮的重力。",
        "expect": [1500, 100, 80, 100],
    },
    "photo_pulley_n3": {
        "title": "图片题：滑轮组，看图数绳子",
        "image": "problem_photo.png",
        "expect": [2250, 112.5, 80],
    },
    "text_buoyancy": {
        "title": "文字题：物块浸入水中",
        "text": "用弹簧测力计挂着一个重 6 N 的长方体物块，物块底面积 25 cm²，高 8 cm。让物块从下表面刚接触水面开始缓慢下降，"
        "直到恰好完全浸没。水足够深，水面高度变化忽略不计，g 取 10 N/kg。求：(1) 物块受到的最大浮力；(2) 恰好完全浸没时测力计的示数；"
        "(3) 恰好完全浸没时物块下表面受到水的压强。",
        "expect": [2, 4, 800],
    },
    "text_single_pulley": {
        "title": "新组合：单个动滑轮",
        "text": "用一个动滑轮把重 180 N 的物体在 5 s 内匀速提升 1 m，绳端向上的拉力为 100 N。不计绳重和摩擦。"
        "求：(1) 有用功；(2) 拉力做的功；(3) 动滑轮的机械效率。",
        "expect": [180, 200, 90],
    },
    "text_circuit": {
        "title": "文字题：动态电路",
        "text": "如图，电阻 R1 = 20 Ω 与滑动变阻器串联在 12 V 电源上，电压表测 R1 两端的电压。滑片移动，使滑动变阻器接入电路的电阻从 0 变为 40 Ω。"
        "求滑动变阻器接入 40 Ω 时：(1) 电路中的电流；(2) 电压表的示数；(3) 滑动变阻器的电功率。",
        "expect": [0.2, 4, 1.6],
    },
    "text_motion": {
        "title": "文字题：两车相遇",
        "text": "甲乙两车相距 600 m，同时相向匀速行驶，甲车速度 10 m/s，乙车速度 20 m/s。求：(1) 两车经过多长时间相遇；(2) 相遇时甲车行驶的路程。",
        "expect": [20, 200],
    },
    "text_lever": {
        "title": "零件不够的题：杠杆",
        "text": "如图，轻质杠杆在水平位置平衡，动力臂长 0.6 m，阻力臂长 0.2 m，阻力为 30 N。求动力的大小。这是一个杠杆平衡问题，画面要能看出杠杆和支点。",
        "expect": [10],
    },
}


def call(path, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(API + path, data=data, method="POST" if data else "GET")
    request.add_header("Content-Type", "application/json")
    if TOKEN:
        request.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def run(name, spec):
    payload = {"text": spec.get("text", "")}
    if spec.get("image"):
        payload["image_base64"] = base64.b64encode((SAMPLES / spec["image"]).read_bytes()).decode()
    code, submitted = call("/v1/problems", payload)
    print(f"\n=== {name}（{spec['title']}）提交 {code}，任务 {submitted.get('id')}")
    job_id = submitted["id"]
    started = time.monotonic()
    previous = None
    status = submitted
    while time.monotonic() - started < WAIT_SECONDS:
        _, status = call(f"/v1/renders/{job_id}")
        marker = (status["status"], status.get("attempt"))
        if marker != previous:
            print(f"  {time.monotonic() - started:6.1f}s  {status['status']}" + (f" 第 {status['attempt']} 次" if status.get("attempt") else ""))
            previous = marker
        if status["status"] in ("done", "failed"):
            break
        if status["status"] == "awaiting_confirmation":
            # 测试里直接接受读到的内容，就像用户没做修改
            call(f"/v1/problems/{job_id}/confirm", {"text": status["problem_text"], "figure": status.get("figure", "")})
        time.sleep(2)

    for attempt in status.get("attempts") or []:
        if attempt["problems"]:
            print(f"  第 {attempt['attempt']} 次的问题：{str(attempt['problems'])[:300]}")
    if status["status"] == "failed":
        print(f"  失败：{status.get('stage')} {str(status.get('errors'))[:500]}")
        return {"name": name, "ok": spec["expect"] is None and status.get("stage") == "unsupported", "stage": status.get("stage")}

    _, timeline = call(f"/v1/renders/{job_id}/timeline.json")
    values = [answer["value"] for answer in timeline["answers"]]
    print("  答案：", [(a["label"], a["value"], a["unit"]) for a in timeline["answers"]])
    correct = spec["expect"] is not None and len(values) >= len(spec["expect"]) and all(
        any(abs(v - e) <= abs(e) * 0.01 for v in values) for e in spec["expect"]
    )
    print(f"  期望 {spec['expect']}，{'符合' if correct else '不符合'}")
    print(
        f"  视频 {status.get('seconds', 0):.0f} 秒，{status.get('frames')} 帧（不同画面 {status.get('unique_frames')}），"
        f"总耗时 {status.get('total_seconds')} 秒，尝试 {len(status.get('attempts') or [])} 次"
    )
    print("  各步耗时：", status.get("stage_seconds"))
    print("  用量：", status.get("tokens"))
    return {"name": name, "id": job_id, "title": spec["title"], "ok": correct}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    names = sys.argv[1:] or list(PROBLEMS)
    results = [run(name, PROBLEMS[name]) for name in names]
    print("\n=== 汇总")
    for result in results:
        print(f"  {'通过' if result['ok'] else '失败'}  {result['name']}  {result.get('stage', '')}")
    demos = SAMPLES.parent.parent / "spike" / "player" / "demo-jobs.json"
    existing = json.loads(demos.read_text(encoding="utf-8")) if demos.exists() else []
    known = {item["id"]: item for item in existing}
    for result in results:
        if result.get("id") and result["ok"]:
            known[result["id"]] = {"id": result["id"], "title": result["title"]}
    demos.write_text(json.dumps(list(known.values()), ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
