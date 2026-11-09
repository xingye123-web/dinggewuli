"""从代码生成零件手册，交给模型。手册和代码同源，不会对不上。用法：python -m physkit.catalog"""

import inspect
import sys

import physkit
from physkit.timeline import Phase

# 这些方法由渲染流程调用，模型不需要知道
_INTERNAL = {"answer_values", "backdrop", "bind", "board_count_at", "bounds", "caption_at", "center", "compile",
             "draw", "edges", "export", "format_value", "frame", "frame_at", "lint", "objects", "problems",
             "regions", "unique_frames"}

_RULES = """# 物理题讲解动画代码规范

你要写一段 Python，把一道初中物理题变成带配音的讲解视频。外观由零件决定，你决定用哪些零件、放在哪、和哪个物理量绑定，以及怎么讲。

## 硬性要求

- 第一行写 `from physkit import *`，另外只能 `import math`。
- 顶层必须定义 `timeline = Timeline(...)` 和 `stage = Stage(timeline)`。
- 不能用 while、try、class、with，不能访问下划线开头的名字，也不能调用 open、eval、getattr 等内置函数，不能用 f.clock 和 f.index。
- 每一帧只能取决于 `f`，不能用随机数、时间或任何全局状态。
- 所有会变的数值都先用 `timeline.quantity` 声明，零件和文字再通过 `f.x` 读取，不要另外计算一遍。

## 物理

- 只用初中物理的概念和公式，不出现加速度、牛顿第二定律、动能定理等高中内容。
- 代入计算时单位要统一：题目给 cm、cm²、cm³、g 的，先声明换算成 m、m²、m³、kg 的量，板书里代入换算后的值。
- 动画的快慢由旁白决定，所以题目里的时间和距离一律用 `phase.progress(f)` 换算，比如 `T * lift.progress(f)`。

## 讲解

- 物体运动的阶段给 `min_seconds`，讲解时画面不动的阶段不给。
- 讲解要按解答的顺序覆盖每一问：说清用什么公式、为什么用这个距离或这个力，再代入。
- 旁白写成老师说话的口语，每句不超过 40 字。单位用中文（牛、米、焦、瓦、秒、帕），公式里的字母说成名称（“有用功”，不说“W有”）。
- 旁白和板书尽量用 `{id}` 引用物理量，不要手写算出来的结果。
- 每一步代入计算都要有一行 `phase.board(...)`，板书用符号和单位，比如 N、J。
- 题目所求的每一项都要用 `timeline.answer` 标记。过程结束后会变化的量（比如瞬时功率）要用 at 指定取值时刻。
- 随过程变化的量，digits 至少是 2，暂停时才读得准。画面上的读数和面板用相同的小数位数。
- 绝对值大于 10000 或小于 0.001 的数要用科学计数法。旁白和板书里的 {id} 会自动转换；画面上的读数用 sci(值, 小数位数) 生成，比如 Readout(lambda f: f"p = {sci(f.p, 0)} Pa", ...)；直接写在旁白或板书里的这类数，也要写成 1.5×10<sup>4</sup>、8×10<sup>-4</sup>（板书）或 1.5乘10的4次方、8乘10的负4次方（旁白）。

## 画面

- 题目是滑轮组（含单个定滑轮、动滑轮）时一律用 PulleyRig，不要自己摆 Pulley 和 Rope。
- 题目是杠杆时用 Lever，是斜面时用 Incline，物块用它们的 hang、block 方法生成，不要自己用 Rod 和 Block 拼。
- 力不是竖直或水平时，ForceArrow 的 direction 写角度，比如沿斜面向上写 incline.angle。

- 坐标：x 从 -7.11 到 7.11，y 从 -4 到 4，原点在中心。
- 实物放在左边：x 不超过 0.75，y 不低于 -3.3。
- 右上方由系统显示板书，底部由系统显示字幕，这两处不要放东西。Plot 自动放在右下方，不用给位置。
- 文字不能超出画面，不能互相重叠，不能压在容器壁或物块边框上，否则会被退回，错误信息会给出是哪个零件的文字、文字的坐标范围，以及至少要挪开多远，照着改。
- 零件的 text 和 Readout 和板书一样可以用 <sub>、<sup> 写下标上标，比如 text="R<sub>1</sub>"。

## 常见错误（以往被退回最多的，写完逐条对一遍）

- 会动的物体，要算它在开始和结束两个位置时是否都还在实物区内（x 不超过 0.75、y 不低于 -3.3），不只看开始。
- Ground、Road 的 y 不要低于 -3.1，下面还有阴影线。
- 文字放在容器外面或物块正中，离容器壁、物块边框至少 0.3；两段文字之间也要留空，尤其是会移动的标签（比如两车相遇时各自的标签）。
- 旁白和板书里的 `{id}` 只能是 `timeline.quantity` 或 `timeline.constant` 声明过的 id，不能是 Python 变量名。
- 零件的属性（`block.top`、`block.bottom`、PulleyRig 的位置等）是函数，做加减要写 `lambda f: block.top(f) + 0.3`，不能写 `block.top + 0.3`。
- 零件的 `show` 只能放 `timeline.quantity` 声明的量，常数不能放；有 `show` 的零件必须给 `name`。
- 必须调用一次 `timeline.show_clock(id, 名称)`。
- 随过程变化的量 digits 至少是 2。
"""


def _signature(obj):
    target = obj.__init__ if inspect.isclass(obj) else obj
    parameters = [p for p in inspect.signature(target).parameters.values() if p.name != "self"]
    return ", ".join(str(p) for p in parameters)


def _members(cls):
    lines = []
    for name, member in inspect.getmembers(cls, inspect.isfunction):
        if not name.startswith("_") and name not in _INTERNAL and member.__doc__:
            lines.append(f"- `{name}({_signature(member)})`：{inspect.getdoc(member)}")
    return lines


def _section(title, obj):
    lines = [f"## {title}", "", inspect.getdoc(obj) or ""]
    members = _members(obj) if inspect.isclass(obj) else []
    if members:
        lines += ["", *members]
    lines.append("")
    return lines


def catalog():
    lines = [_RULES, "# 零件手册", ""]
    for name in physkit.__all__:
        obj = getattr(physkit, name)
        if not isinstance(obj, str):
            lines += _section(f"{name}({_signature(obj)})", obj)
    lines += _section("Phase（由 timeline.phase 返回）", Phase)
    colors = [name for name in physkit.__all__ if isinstance(getattr(physkit, name), str)]
    lines.append(f"可用颜色常量：{'、'.join(colors)}。")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(catalog())
