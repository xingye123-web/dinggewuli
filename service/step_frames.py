"""给文字解析的每一步配一张视频截图。

解答的每一步有一条算式（比如 "W有 = Gh = 240 N × 2 m = 480 J"），视频的板书里也有对应的一行。
按等号左边的量把两边对上，取这行板书所在阶段快结束时的画面：动画已经走完，板书也写出来了。
对不上的步骤不配图。截图失败只是少了配图，不影响出视频，所以这里不抛异常。
"""

import json
import re
import shutil
import subprocess
import traceback
from pathlib import Path

MAX_STEPS = 12
WIDTH = 640
BEFORE_END = 0.3  # 取阶段结束前这么多秒的画面，避开下一阶段刚开始的切换
_TAG = re.compile(r"</?(?:sub|sup)>")
_SUBSCRIPT = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def _ffmpeg():
    found = shutil.which("ffmpeg")
    if found:
        return found
    winget = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe"
    return str(winget) if winget.exists() else None


def _left_side(formula):
    """算式等号左边的量，去掉下标标签和空格，比如 "W<sub>有</sub> = Gh" 得到 "W有"。"""
    if "=" not in formula:
        return ""
    return re.sub(r"\s+", "", _TAG.sub("", formula.split("=", 1)[0])).translate(_SUBSCRIPT)


def _step_sides(step):
    """一步里可能有几条算式，用中文逗号或分号隔开，每条都取等号左边。"""
    clauses = re.split(r"[，；;]", step.get("formula") or "")
    return [side for side in (_left_side(clause) for clause in clauses) if side]


def _same_symbol(a, b):
    """一个是另一个加了下标：开头的字母相同，多出来的部分是汉字或数字下标。"""
    short, long = sorted((a, b), key=len)
    return long.startswith(short) and len(short) <= 2 and all(not c.isascii() or c.isdigit() for c in long[len(short):])


def match_steps(solution, formulas):
    """返回 [(步骤序号, 截图时刻)]。按顺序往后找，同一行板书只配一步。"""
    sides = [_left_side(formula["expr"]) for formula in formulas]
    used = set()
    matches = []
    cursor = 0
    for number, step in enumerate((solution.get("steps") or [])[:MAX_STEPS], start=1):
        wanted = _step_sides(step)
        order = list(range(cursor, len(formulas))) + list(range(cursor))
        hit = next((i for i in order if i not in used and sides[i] and sides[i] in wanted), None)
        if hit is None:
            # 只差下标的也算，比如解答写 ρ、板书写 ρ物
            hit = next((i for i in order if i not in used and sides[i]
                        and any(_same_symbol(sides[i], side) for side in wanted)), None)
        if hit is None:
            continue
        used.add(hit)
        cursor = hit + 1
        formula = formulas[hit]
        moment = max(formula.get("t_end", formula["t"]) - BEFORE_END, formula["t"])
        matches.append((number, round(moment, 2)))
    return matches


def build(directory):
    """在任务目录里生成 step1.jpg…和 steps.json，返回 steps.json 的内容；没有配图时返回 None。"""
    try:
        directory = Path(directory)
        solution = json.loads((directory / "solution.json").read_text(encoding="utf-8"))
        timeline = json.loads((directory / "timeline.json").read_text(encoding="utf-8"))
        ffmpeg = _ffmpeg()
        if not ffmpeg or "t" not in (timeline.get("formulas") or [{}])[0]:
            return None
        steps = []
        for number, moment in match_steps(solution, timeline["formulas"]):
            name = f"step{number}.jpg"
            subprocess.run(
                [ffmpeg, "-y", "-v", "error", "-ss", f"{moment:.2f}", "-i", str(directory / "video.mp4"),
                 "-frames:v", "1", "-vf", f"scale={WIDTH}:-2", "-q:v", "4", str(directory / name)],
                check=True, capture_output=True, timeout=60,
            )
            steps.append({"step": number, "t": moment, "image": name})
        if not steps:
            return None
        (directory / "steps.json").write_text(json.dumps(steps, ensure_ascii=False), encoding="utf-8")
        return steps
    except Exception:  # noqa: BLE001  少了配图不影响出视频
        traceback.print_exc()
        return None
