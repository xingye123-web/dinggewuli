"""收集零件库缺的东西，留给 Claude 以后补。

DeepSeek 碰到手册里没有的零件时，会先用基础零件拼出来，并在代码开头写
`# 缺少零件: 零件名；用途；现在用什么代替`。这里把这些注释和 UNSUPPORTED 的原因记下来，
汇总成 待处理.md。还没有示例的题型第一次做成功时，把代码存成示例候选，等 Claude 审核，
不会自动放进示例库。

记录里有评委提交的题目，所以放在 .dev 下面，不进仓库。
记录失败不能影响出视频，所以这里的函数都不抛异常。
"""

import json
import os
import re
import time
import traceback
from collections import defaultdict
from pathlib import Path

from . import examples, settings

DIR = Path(os.environ.get("PART_REQUESTS_DIR", settings.ROOT / ".dev" / "requests"))
SUMMARY = DIR / "待处理.md"
HANDLED = DIR / "已处理.json"  # Claude 做完零件后把关键词写进来，比如 "杠杆"，名字含这个词的需求就不再列
CANDIDATES = DIR / "candidates"
CANDIDATES_PER_CATEGORY = 3

_NOTE = re.compile(r"^\s*#\s*缺少零件\s*[:：]\s*(.+)$", re.M)


def parse(code):
    """从代码注释里取出缺的零件：[{name, use, substitute}]。"""
    found = []
    for line in _NOTE.findall(code or ""):
        fields = [field.strip() for field in re.split(r"[；;]", line, maxsplit=2)]
        fields += [""] * (3 - len(fields))
        # 模型有时会写「缺少零件: 无（……）」，这种不算需求
        if fields[0] and not re.match(r"^(无|没有|不缺|none)", fields[0], re.I):
            found.append({"name": fields[0], "use": fields[1], "substitute": fields[2]})
    return found


def _handled():
    try:
        return set(json.loads(HANDLED.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def record(job_id, text, topic, code=None, unsupported=None, attempts=0):
    """一道题写完代码（或者放弃）后调用。返回待处理的零件种数，出错时返回 None。"""
    try:
        parts = parse(code)
        category = examples.main_category(f"{topic}\n{text}")
        if parts or unsupported:
            DIR.mkdir(parents=True, exist_ok=True)
            entry = {
                "job": job_id,
                "time": time.strftime("%Y-%m-%d %H:%M"),
                "category": category,
                "topic": topic,
                "problem": text,
                "parts": parts,
                "unsupported": unsupported,
                "attempts": attempts,
                "code_file": f"{job_id}.py" if code else None,
            }
            (DIR / f"{job_id}.json").write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8")
            if code:
                (DIR / f"{job_id}.py").write_text(code, encoding="utf-8")
        if code and not unsupported and not (category and examples.has_example(category)):
            _save_candidate(job_id, category or "未分类", code, attempts)
        return summarize()
    except Exception:  # noqa: BLE001 记录失败不能影响出视频
        traceback.print_exc()
        return None


def _save_candidate(job_id, category, code, attempts):
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    if len(list(CANDIDATES.glob(f"{category}_*.py"))) >= CANDIDATES_PER_CATEGORY:
        return
    header = f"# 示例候选，题型：{category}，任务 {job_id}，第 {attempts} 次通过检查。审核后才能放进 render/examples\n"
    (CANDIDATES / f"{category}_{job_id}.py").write_text(header + code, encoding="utf-8")


def summarize():
    """重新生成 待处理.md，返回还没处理的零件种数。"""
    if not DIR.exists():
        return 0
    handled = _handled()
    by_part = defaultdict(list)
    unsupported = []
    for path in sorted(DIR.glob("*.json")):
        if path == HANDLED:
            continue
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        for part in entry.get("parts", []):
            # 已处理.json 里写关键词，零件名里含有任何一个就算做完了（模型每次起的名字不完全一样）
            if not any(keyword in part["name"] for keyword in handled):
                by_part[part["name"]].append((entry, part))
        if entry.get("unsupported"):
            unsupported.append(entry)

    lines = [
        "# 零件库待处理",
        "",
        "由 service/part_requests.py 自动生成，不要手改。做完一种零件后，把关键词加进 已处理.json。",
        "",
        f"## 缺少的零件（{len(by_part)} 种，按出现次数排）",
        "",
    ]
    for name, items in sorted(by_part.items(), key=lambda item: -len(item[1])):
        lines.append(f"### {name}（{len(items)} 次）")
        for entry, part in items[:5]:
            lines.append(f"- {entry['time']} [{entry.get('category') or '未分类'}] 用途：{part['use'] or '未写'}；"
                         f"代替：{part['substitute'] or '未写'}；代码：{entry.get('code_file') or '无'}")
            lines.append(f"  题目：{entry['problem'][:120]}")
        lines.append("")
    lines += [f"## 拒绝出题（UNSUPPORTED，{len(unsupported)} 次）", ""]
    for entry in unsupported[-20:]:
        lines.append(f"- {entry['time']} [{entry.get('category') or '未分类'}] {entry['unsupported']}")
        lines.append(f"  题目：{entry['problem'][:120]}")
    candidates = sorted(CANDIDATES.glob("*.py")) if CANDIDATES.exists() else []
    lines += ["", f"## 示例候选（{len(candidates)} 个，在 candidates/ 下）", ""]
    lines += [f"- {path.name}" for path in candidates]
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(by_part)
