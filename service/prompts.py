"""给 DeepSeek 的提示词。零件手册和示例直接读项目里的文件，和代码保持一致。"""

import json

from . import examples, settings

_RENDER = settings.ROOT / "render"

TRANSCRIBE = """你要把一张中国初中物理题的照片转成文字。只读题，不要解题。

输出 JSON：
{
  "problem_text": "题目完整原文，保留所有数字和单位，题号可以去掉",
  "figure": "题图里解题要用到的信息，比如动滑轮上承担物重的绳子段数、绳端朝哪拉、电路是串联还是并联、电表测哪里、物体的位置关系。没有图就写空字符串"
}
数滑轮组的绳子段数时，按这个方法：沿着绳子从头走到尾，把路径写出来（比如 从动滑轮框架向上，绕过定滑轮，向下绕过动滑轮，向上到绳端），再数其中有几段是直接拉着动滑轮或它的框架的。系在框架上的绳头算一段，绕过动滑轮后向上的绳子也算一段，所以绳端向上拉时，最后那段也要算。
看不清的地方如实写“看不清”，不要猜。"""

SOLVE = """你是中国初中物理老师，要独立解出这道题。

只能用初中课标内的知识：没有加速度、牛顿第二定律、动能定理、冲量这些内容。代入计算前先把单位统一成国际单位。
绝对值大于 10000 或小于 0.001 的数，在 explain 和 formula 里写成科学计数法，比如 1.5×10⁴ Pa、8×10⁻⁴ m³；answers 的 value 仍然写普通数字。

输出 JSON：
{
  "topic": "知识点，比如 滑轮组、浮力",
  "knowns": [{"name": "物重", "symbol": "G", "value": 240, "unit": "N"}],
  "steps": [{"title": "这一步求什么", "explain": "为什么这样做", "formula": "代入数值的算式"}],
  "answers": [{"label": "有用功", "value": 480, "unit": "J"}],
  "pitfall": "这道题最容易错在哪里"
}
answers 按题目的每一问列一项：value 只写数字；unit 用符号，比如 N、J、W、Pa、kg/m³；效率写成百分数的数值，value 写 80，unit 写 %。
题目缺条件、自相矛盾或者超出初中范围时，把 answers 写成空数组，并在 pitfall 说明原因。"""

AUTHOR_TASK = """下面是题目和已经核对过的解答。请写出这道题的讲解动画代码。

题目：
{problem}

题图信息：
{figure}

解答：
{solution}

要求：
- timeline.answer 的 label 必须和解答 answers 里的 label 逐字一致，单位也要一致。
- 旁白要按解答的步骤讲，并在合适的地方讲出易错点。整段旁白控制在 150 到 350 字。
- 题目里的物理过程要真正动起来，能动的装置都要动。
- 只输出一个 python 代码块，不要解释。
- 手册里没有这道题需要的专门零件时（比如杠杆、斜面、透镜），先用 Rod、Block、Readout 这些基础零件拼出来，
  再在代码最前面加注释，每缺一种写一行：`# 缺少零件: 零件名；用途；现在用什么代替`。这些需求会转给零件库的维护者。
- 只有基础零件也拼不出来时，才只输出一行：UNSUPPORTED: 原因。"""

REPAIR = """上一版代码没有通过检查，问题如下：

{problems}

请修改后输出完整的代码，仍然只输出一个 python 代码块。"""


def author_system(problem_text="", topic=""):
    """手册放在最前面，每次都一样，DeepSeek 能缓存；后面是按题型挑出的示例。"""
    catalog = (_RENDER / "CATALOG.md").read_text(encoding="utf-8")
    parts = [catalog, "\n# 示例（和这道题题型最接近的）\n"]
    for name in examples.pick(f"{topic}\n{problem_text}"):
        code = (_RENDER / "examples" / name).read_text(encoding="utf-8")
        parts.append(f"## {name}\n\n```python\n{code}\n```\n")
    return "\n".join(parts)


def author_task(problem_text, figure, solution):
    return AUTHOR_TASK.format(
        problem=problem_text,
        figure=figure or "无",
        solution=json.dumps(solution, ensure_ascii=False, indent=1),
    )
