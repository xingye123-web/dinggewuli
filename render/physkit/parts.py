"""固定零件。外观和画法写死在这里，模型只决定用哪些零件、放在哪、和哪个物理量绑定。

位置、长度、文字等参数都可以写成数值，或写成 lambda f: ... 让它随帧变化。
"""

import os

import numpy as np
from manim import Arc, Arrow, Axes, Circle, Dot, Line, Rectangle, Text, VGroup, VMobject

FONT = os.environ.get("PHYSKIT_FONT", "Noto Sans SC")
ROPE = "#E8C547"
OBJECT = "#5DA9E9"
STEEL = "#AEB8C4"
ACCENT = "#FF7A59"
INK = "#E6EBF0"
WATER = "#3FA7D6"

_COLLINEAR = 1e-6


def _val(param, f):
    return param(f) if callable(param) else param


def _point(x, y):
    return np.array([x, y, 0.0])


def _text(content, size, color):
    return Text(content, font=FONT, font_size=size, color=color)


class Part:
    """零件基类。name 不为空时，暂停后可以点它，show 是点击后显示的物理量。"""

    static = False

    def __init__(self, name=None, show=()):
        self.name = name
        self.show = list(show)

    def backdrop(self):
        """只画一次的部分。"""
        return None

    def draw(self, f):
        """这一帧的画面。静态零件的 f 是 None。"""
        raise NotImplementedError

    def bounds(self, f):
        """可点击的范围 (x0, y0, x1, y1)。"""
        return None

    def problems(self, f):
        """这一帧的布局问题。"""
        return []

    def edges(self, f):
        """不该被文字压住的线段，每条写成 (x0, y0, x1, y1)。"""
        return []


class _Beam(Part):
    static = True
    _hatch_side = 1

    def __init__(self, x0, x1, y):
        super().__init__()
        self.x0, self.x1, self.y = x0, x1, y

    def draw(self, f):
        group = VGroup(Line(_point(self.x0, self.y), _point(self.x1, self.y), color=STEEL, stroke_width=5))
        for x in np.arange(self.x0 + 0.15, self.x1, 0.3):
            group.add(
                Line(
                    _point(x, self.y),
                    _point(x - 0.12, self.y + self._hatch_side * 0.16),
                    color=STEEL,
                    stroke_width=2,
                )
            )
        return group


class Ceiling(_Beam):
    """天花板。从 x0 到 x1 的横梁，下表面在 y。"""


class Ground(_Beam):
    """地面。从 x0 到 x1 的横线，上表面在 y。下面还有 0.16 高的阴影线，所以 y 不要低于 -3.1。"""

    _hatch_side = -1


class Rod(Part):
    """刚性连杆，连接 start 和 end 两点，比如滑轮的支架、挂钩。点写成 (x, y)。"""

    def __init__(self, start, end, color=STEEL, width=4):
        super().__init__()
        self.start, self.end, self.color, self.width = start, end, color, width

    def draw(self, f):
        return Line(
            _point(_val(self.start[0], f), _val(self.start[1], f)),
            _point(_val(self.end[0], f), _val(self.end[1], f)) + _point(1e-4, 0),
            color=self.color,
            stroke_width=self.width,
        )


class Pulley(Part):
    """滑轮，圆心在 (x, y)，半径 r。turn 是转过的角度（弧度）。

    left_x、right_x 是左右切点的横坐标，是函数，可以直接当作绳子端点的 x，但不能做加减。
    y 也可以是函数，做加减要写成 lambda f: moving_y(f) - 0.5。
    """

    def __init__(self, x, y, r=0.35, turn=0, name=None, show=()):
        super().__init__(name, show)
        self.x, self.y, self.r, self.turn = x, y, r, turn

    def center(self, f):
        return _val(self.x, f), _val(self.y, f)

    @property
    def left_x(self):
        return lambda f: _val(self.x, f) - self.r

    @property
    def right_x(self):
        return lambda f: _val(self.x, f) + self.r

    def draw(self, f):
        cx, cy = self.center(f)
        center = _point(cx, cy)
        angle = _val(self.turn, f)
        return VGroup(
            Circle(radius=self.r, color=STEEL, stroke_width=4).move_to(center),
            Line(center, center + self.r * _point(np.cos(angle), np.sin(angle)), color=STEEL, stroke_width=3),
            Dot(center, radius=0.05, color=STEEL),
        )

    def bounds(self, f):
        cx, cy = self.center(f)
        return cx - self.r, cy - self.r, cx + self.r, cy + self.r


class _Wrap:
    def __init__(self, pulley, over):
        self.pulley, self.over = pulley, over


def Over(pulley):
    """绳子从滑轮上方绕过，只用在 Rope 的路径里。"""
    return _Wrap(pulley, True)


def Under(pulley):
    """绳子从滑轮下方绕过，只用在 Rope 的路径里。"""
    return _Wrap(pulley, False)


class Rope(Part):
    """绳子。path 依次列出路径：(x, y) 是端点，Over(滑轮) 和 Under(滑轮) 是绕过滑轮。

    例：Rope([(a.left_x, y0), Over(a), Under(b), (b.right_x, y1)])。
    绳子从哪一侧到达滑轮，就从另一侧离开。设置 name 后，可点击的是最后一段，也就是绳端。
    """

    def __init__(self, path, color=ROPE, width=4, name=None, show=()):
        super().__init__(name, show)
        self.path, self.color, self.width = path, color, width

    def _pieces(self, f):
        pieces = []
        pen = None
        for item in self.path:
            if isinstance(item, _Wrap):
                cx, cy = item.pulley.center(f)
                r = item.pulley.r
                from_left = pen[0] <= cx
                entry = (cx - r if from_left else cx + r, cy)
                pieces.append(("line", pen, entry))
                start = np.pi if from_left else 0.0
                sweep = -np.pi if from_left == item.over else np.pi
                pieces.append(("arc", (cx, cy), r, start, sweep))
                pen = (cx + r if from_left else cx - r, cy)
            else:
                point = (_val(item[0], f), _val(item[1], f))
                if pen is not None:
                    pieces.append(("line", pen, point))
                pen = point
        return pieces

    def draw(self, f):
        group = VGroup()
        for piece in self._pieces(f):
            if piece[0] == "line":
                start, end = piece[1], piece[2]
                if abs(start[0] - end[0]) + abs(start[1] - end[1]) > 1e-3:
                    group.add(Line(_point(*start), _point(*end)))
            else:
                group.add(Arc(radius=piece[2], start_angle=piece[3], angle=piece[4], arc_center=_point(*piece[1], )))
        return group.set_stroke(self.color, self.width)

    def line_pieces(self, f):
        """绳子的直线段，每段写成 (x0, y0, x1, y1)。"""
        return [(*piece[1], *piece[2]) for piece in self._pieces(f) if piece[0] == "line"]

    def problems(self, f):
        for number, (x0, y0, x1, y1) in enumerate(self.line_pieces(f), start=1):
            if abs(x0 - x1) > 0.03 and abs(y0 - y1) > 0.03:
                return [
                    f"绳子第 {number} 段是斜的（x 从 {x0:.2f} 到 {x1:.2f}），会和别的绳子交叉。"
                    "每段绳子要竖直，让端点的 x 对准滑轮的 left_x 或 right_x。滑轮组请直接用 PulleyRig"
                ]
        return []

    def bounds(self, f):
        if not self.name:
            return None
        start, end = next(piece[1:3] for piece in reversed(self._pieces(f)) if piece[0] == "line")
        return (
            min(start[0], end[0]) - 0.2,
            min(start[1], end[1]),
            max(start[0], end[0]) + 0.2,
            max(start[1], end[1]),
        )


class Block(Part):
    """物块，中心在 (x, y)，宽 w 高 h。text 是写在物块上的文字。

    top、bottom 是上下表面的纵坐标，是函数，可以直接当作绳子或连杆端点的 y，但不能做加减。
    """

    def __init__(self, x, y, w, h, text=None, color=OBJECT, name=None, show=()):
        super().__init__(name, show)
        self.x, self.y, self.w, self.h, self.text, self.color = x, y, w, h, text, color

    @property
    def top(self):
        return lambda f: _val(self.y, f) + self.h / 2

    @property
    def bottom(self):
        return lambda f: _val(self.y, f) - self.h / 2

    def _label(self, f):
        content = _val(self.text, f)
        return _text(content, 18, INK) if content else None

    def draw(self, f):
        center = _point(_val(self.x, f), _val(self.y, f))
        group = VGroup(
            Rectangle(
                width=self.w, height=self.h, stroke_color=self.color, fill_color=self.color, fill_opacity=0.35
            ).move_to(center)
        )
        label = self._label(f)
        if label:
            group.add(label.move_to(center))
        return group

    def bounds(self, f):
        x, y = _val(self.x, f), _val(self.y, f)
        return x - self.w / 2, y - self.h / 2, x + self.w / 2, y + self.h / 2

    def problems(self, f):
        label = self._label(f)
        if label and (label.width > self.w or label.height > self.h):
            return [f"物块上的文字「{_val(self.text, f)}」放不下：文字宽 {label.width:.2f}，物块宽 {self.w}"]
        return []

    def edges(self, f):
        x0, y0, x1, y1 = self.bounds(f)
        return [(x0, y0, x0, y1), (x1, y0, x1, y1), (x0, y0, x1, y0), (x0, y1, x1, y1)]


class PulleyRig:
    """完整的滑轮组。题目是滑轮组时优先用它，滑轮和绳子的走法由它保证正确，每段绳子都竖直。

    n 是动滑轮上承担物重的绳子段数，n=1 就是单个定滑轮。pull 是绳端拉动的方向：up 或 down，n=1 只能是 down。
    height 是 lambda f: f.h 这样的函数，单位是米。max_height 是物体上升的最大高度，单位是米，用来自动选比例。
    用 stage.add(*rig.parts) 把它加到舞台上。段数编号会自动标在绳子旁边。

    属性：
    - end_x：绳端的横坐标（数值）；end_y：绳端的纵坐标（函数），可以给 ForceArrow 和 Ruler 用。
    - left_x、right_x：整个滑轮组左右边界（数值），放标尺和文字时要避开。
    - weight_bottom：物体下表面的纵坐标（函数）；weight_start：物体下表面的初始纵坐标（数值）。
    - end_start：绳端的初始纵坐标（数值）；meter：1 米对应的画面长度。
    """

    def __init__(self, n, pull, height, max_height, x=-3.6, weight_text=None, weight_name="物体",
                 weight_show=(), moving_show=(), fixed_show=(), end_show=(), ceiling_y=3.45, ground_y=-3.05):
        if n < 1 or n > 5:
            raise ValueError("PulleyRig 的 n 只支持 1 到 5")
        if pull not in ("up", "down"):
            raise ValueError("PulleyRig 的 pull 只能是 up 或 down")
        if n == 1 and pull == "up":
            raise ValueError("n=1 是单个定滑轮，绳端只能向下拉")
        self.n, self.pull = n, pull
        r = 0.32
        columns = n + (1 if pull == "down" else 0)
        first_x = x - r * (columns - 1)
        column_x = [first_x + 2 * r * i for i in range(columns)]
        fixed_y = ceiling_y - 0.7
        weight_w, weight_h = 1.5, 0.85

        if n == 1:
            # 单个定滑轮：绳子一头直接系在物体上，物体在第一列正下方
            moving_y0 = ground_y + 0.1 + weight_h
            end_travel = 3.0
            end_top = fixed_y - 0.4
            self.end_start = end_top
            self.meter = min(end_travel / max_height, 3.0 / max_height)
        else:
            moving_y0 = ground_y + 0.1 + weight_h + 0.75
            if pull == "up":
                self.end_start = moving_y0 + 0.35
                end_travel = (ceiling_y - 1.0) - self.end_start
            else:
                self.end_start = fixed_y - 0.4
                end_travel = self.end_start - (ground_y + 0.85)
            self.meter = min(end_travel / (n * max_height), (fixed_y - r - moving_y0 - r - 0.25) / max_height)
        meter = self.meter
        travel = lambda f: height(f) * meter
        moving_y = lambda f: moving_y0 + travel(f)
        direction = 1 if pull == "up" else -1
        self.end_x = column_x[-1]
        self.end_y = lambda f: self.end_start + direction * n * travel(f)
        self.left_x = first_x - 0.75
        self.right_x = column_x[-1] + 0.25

        fixed_wheels = []
        moving_wheels = []
        path = []
        odd = n % 2 == 1
        for k in range(n - 1):
            center = column_x[k] + r
            if (k % 2 == 0) == odd:
                fixed_wheels.append(center)
            else:
                moving_wheels.append(center)
        extra_fixed = column_x[n - 1] + r if pull == "down" else None

        self.parts = [Ceiling(first_x - 0.6, column_x[-1] + 0.6, ceiling_y), Ground(-6.8, 0.4, ground_y)]
        all_fixed = fixed_wheels + ([extra_fixed] if extra_fixed is not None else [])
        fixed_objects = {}
        for index, center in enumerate(all_fixed):
            self.parts.append(Rod((center, ceiling_y), (center, fixed_y)))
            wheel = Pulley(
                center, fixed_y, r, turn=lambda f: -travel(f) / r,
                name="定滑轮" if index == 0 and fixed_show else None,
                show=fixed_show if index == 0 else (),
            )
            fixed_objects[center] = wheel

        moving_objects = {}
        for index, center in enumerate(moving_wheels):
            moving_objects[center] = Pulley(
                center, moving_y, r, turn=lambda f: 2 * travel(f) / r,
                name="动滑轮" if index == 0 and moving_show else None,
                show=moving_show if index == 0 else (),
            )

        if n == 1:
            # 物体偏向左边，绳端那一段才不会穿过它
            weight_x = column_x[1] - 0.15 - weight_w / 2
            weight_y = lambda f: ground_y + 0.1 + weight_h / 2 + travel(f)
        else:
            bar_y = lambda f: moving_y(f) - 0.5
            bar_left = column_x[0] if odd else moving_wheels[0]
            bar_right = moving_wheels[-1]
            weight_x = (bar_left + bar_right) / 2
            weight_y = lambda f: moving_y(f) - 0.75 - weight_h / 2
            for center in moving_wheels:
                self.parts.append(Rod((center, moving_y), (center, bar_y)))
            if bar_right > bar_left:
                self.parts.append(Rod((bar_left, bar_y), (bar_right, bar_y), width=5))
            self.parts.append(Rod((weight_x, bar_y), (weight_x, lambda f: moving_y(f) - 0.75)))

        self.weight = Block(
            weight_x, weight_y, weight_w, weight_h, text=weight_text,
            name=weight_name if weight_show else None, show=weight_show,
        )
        self.weight_bottom = self.weight.bottom
        self.weight_start = ground_y + 0.1
        self.parts.append(self.weight)
        self.parts.extend(fixed_objects.values())
        self.parts.extend(moving_objects.values())

        if n == 1:
            path.append((column_x[0], self.weight.top))
        elif odd:
            path.append((column_x[0], lambda f: moving_y(f) - 0.5))
        else:
            path.append((column_x[0], ceiling_y))
        for k in range(n - 1):
            center = column_x[k] + r
            path.append(Over(fixed_objects[center]) if center in fixed_objects else Under(moving_objects[center]))
        if extra_fixed is not None:
            path.append(Over(fixed_objects[extra_fixed]))
        path.append((column_x[-1], self.end_y))
        self.parts.append(Rope(path, name="绳端" if end_show else None, show=end_show))

        if n > 1:
            for k in range(n):
                self.parts.append(self._strand_label(k, column_x[k], k == n - 1 and pull == "up", moving_y, fixed_y))

    def _strand_label(self, k, x, is_end, moving_y, fixed_y):
        top = (lambda f: self.end_y(f)) if is_end else (lambda f: fixed_y)
        return Readout(str(k + 1), x - 0.14, lambda f: (moving_y(f) + top(f)) / 2, size=18, color=ROPE)


_DIRECTIONS = {"up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)}


class ForceArrow(Part):
    """力的箭头，从 (x, y) 出发，朝 direction（up、down、left、right）画，长度 length。

    text 写在箭头末端旁边。长度小于 0.05 时不画。
    """

    def __init__(self, x, y, length, direction="up", text=None, color=ACCENT):
        super().__init__()
        self.x, self.y, self.length, self.direction, self.text, self.color = x, y, length, direction, text, color

    def draw(self, f):
        length = _val(self.length, f)
        group = VGroup()
        if length < 0.05:
            return group
        start = _point(_val(self.x, f), _val(self.y, f))
        dx, dy = _DIRECTIONS[self.direction]
        end = start + length * _point(dx, dy)
        group.add(
            Arrow(start, end, buff=0, color=self.color, stroke_width=5, max_tip_length_to_length_ratio=0.3)
        )
        content = _val(self.text, f)
        if content:
            label = _text(content, 22, self.color)
            side = _point(1, 0) if dy else _point(0, 1)
            group.add(label.next_to(end if dy == 0 else (start + end) / 2, side, buff=0.15))
        return group


_ANCHORS = {"center": None, "left": _point(-1, 0), "right": _point(1, 0)}


class Readout(Part):
    """文字。text 是字符串或 lambda f: ...，anchor 指 (x, y) 对齐文字的哪一边：center、left、right。"""

    def __init__(self, text, x, y, size=24, color=INK, anchor="center"):
        super().__init__()
        self.text, self.x, self.y, self.size, self.color, self.anchor = text, x, y, size, color, anchor

    def draw(self, f):
        label = _text(_val(self.text, f), self.size, self.color)
        target = _point(_val(self.x, f), _val(self.y, f))
        side = _ANCHORS[self.anchor]
        if side is None:
            return label.move_to(target)
        return label.move_to(target, aligned_edge=side)


class Ruler(Part):
    """竖直标尺，从 y0 量到 y1，表示一段距离。text 写在 y1 一端，text_side 是 right、left 或 top。"""

    def __init__(self, x, y0, y1, text=None, color=OBJECT, text_side="right"):
        super().__init__()
        self.x, self.y0, self.y1, self.text, self.color, self.text_side = x, y0, y1, text, color, text_side

    def draw(self, f):
        x, y0, y1 = _val(self.x, f), _val(self.y0, f), _val(self.y1, f)
        group = VGroup()
        if abs(y1 - y0) > 1e-3:
            group.add(Line(_point(x, y0), _point(x, y1), color=self.color, stroke_width=5))
        content = _val(self.text, f)
        if content:
            direction = {"right": _point(1, 0), "left": _point(-1, 0), "top": _point(0, 1)}[self.text_side]
            group.add(_text(content, 22, self.color).next_to(_point(x, y1), direction, buff=0.15))
        return group


class Series:
    """Plot 里的一条曲线。x、y 都是 lambda f: ...。"""

    def __init__(self, x, y, color=OBJECT):
        self.x, self.y, self.color = x, y, color


class Plot(Part):
    """坐标图，固定放在画面右下方，通常不用改位置，一道题最多一个。

    x_range、y_range 写成 (起点, 终点, 刻度间隔)，刻度不要太密，每个轴 5 到 6 个刻度。
    曲线随动画逐帧画出，淡色线是完整走势。
    """

    def __init__(self, x_range, y_range, x_label, y_label, series, x=4.1, y=-1.42, width=4.9, height=2.15):
        super().__init__()
        self.x, self.y, self.width, self.height = x, y, width, height
        self.x_range, self.y_range, self.x_label, self.y_label = x_range, y_range, x_label, y_label
        self.series = series
        self._axes = Axes(
            x_range=list(x_range),
            y_range=list(y_range),
            x_length=width,
            y_length=height,
            tips=False,
            axis_config={"color": STEEL, "stroke_width": 2},
        ).move_to(_point(x, y))
        self._knots = None

    def bind(self, timeline):
        """算出每条曲线的转折点，直线段只保留两端，画起来快。"""
        self._knots = []
        for series in self.series:
            points = []
            for index in range(timeline.frame_count):
                f = timeline.frame(index)
                points.append((index, self._axes.c2p(series.x(f), series.y(f))))
            knots = [points[0]]
            for previous, current, following in zip(points, points[1:], points[2:]):
                a = current[1] - previous[1]
                b = following[1] - current[1]
                if abs(a[0] * b[1] - a[1] * b[0]) > _COLLINEAR:
                    knots.append(current)
            knots.append(points[-1])
            self._knots.append(knots)

    def backdrop(self):
        group = VGroup(self._axes)
        x0, x1, dx = self.x_range
        y0, y1, dy = self.y_range
        for value in _ticks(x0, x1, dx):
            group.add(_text(_tick_text(value), 16, STEEL).next_to(self._axes.c2p(value, y0), _point(0, -1), buff=0.1))
        for value in _ticks(y0, y1, dy):
            if value != y0:
                group.add(_text(_tick_text(value), 16, STEEL).next_to(self._axes.c2p(x0, value), _point(-1, 0), buff=0.1))
        group.add(_text(self.x_label, 18, STEEL).next_to(self._axes.c2p(x1, y0), _point(0, -1), buff=0.36))
        group.add(_text(self.y_label, 18, STEEL).next_to(self._axes.c2p(x0, y1), _point(0, 1), buff=0.1))
        for series, knots in zip(self.series, self._knots):
            ghost = VMobject(stroke_color=series.color, stroke_width=2, stroke_opacity=0.3)
            ghost.set_points_as_corners([point for _, point in knots])
            group.add(ghost)
        return group

    def draw(self, f):
        group = VGroup()
        for series, knots in zip(self.series, self._knots):
            current = self._axes.c2p(series.x(f), series.y(f))
            passed = [point for index, point in knots if index < f.index]
            if passed:
                line = VMobject(stroke_color=series.color, stroke_width=5)
                line.set_points_as_corners(passed + [current])
                group.add(line)
            group.add(Dot(current, radius=0.08, color=series.color))
        return group


_BACKGROUND = "#10151C"
_SIDES = {"top": _point(0, 1), "bottom": _point(0, -1), "left": _point(-1, 0), "right": _point(1, 0)}


class Wire(Part):
    """导线，依次连接 points 里的点，每个点写成 (x, y)。元件放在导线上会盖住它经过的那一段，所以导线可以画成完整的回路。"""

    def __init__(self, points, color=STEEL):
        super().__init__()
        self.points, self.color = points, color

    def draw(self, f):
        line = VMobject(stroke_color=self.color, stroke_width=3)
        line.set_points_as_corners([_point(_val(x, f), _val(y, f)) for x, y in self.points])
        return line


class _Component(Part):
    """电路元件的共同部分：中心在 (x, y)，horizontal 决定沿水平还是竖直导线放置。"""

    SIZE = (0.9, 0.34)

    def __init__(self, x, y, horizontal=True, text=None, text_side="top", name=None, show=()):
        super().__init__(name, show)
        self.x, self.y, self.horizontal, self.text, self.text_side = x, y, horizontal, text, text_side

    def _center(self, f):
        return _point(_val(self.x, f), _val(self.y, f))

    def _extent(self):
        along, across = self.SIZE
        return (along, across) if self.horizontal else (across, along)

    def _axis(self):
        return _point(1, 0) if self.horizontal else _point(0, 1)

    def _label(self, f):
        content = _val(self.text, f)
        if not content:
            return None
        width, height = self._extent()
        side = _SIDES[self.text_side]
        reach = (height if self.text_side in ("top", "bottom") else width) / 2 + 0.16
        return _text(content, 20, INK).next_to(self._center(f) + side * reach, side, buff=0)

    def _with_label(self, group, f):
        label = self._label(f)
        if label:
            group.add(label)
        return group

    def bounds(self, f):
        x, y = _val(self.x, f), _val(self.y, f)
        width, height = self._extent()
        return x - width / 2 - 0.05, y - height / 2 - 0.05, x + width / 2 + 0.05, y + height / 2 + 0.05


class Resistor(_Component):
    """定值电阻，画成矩形。text 是标注，比如 "R1 = 10 Ω"，text_side 是 top、bottom、left 或 right。"""

    def draw(self, f):
        width, height = self._extent()
        body = Rectangle(
            width=width, height=height, stroke_color=INK, stroke_width=3, fill_color=_BACKGROUND, fill_opacity=1
        ).move_to(self._center(f))
        return self._with_label(VGroup(body), f)


class Rheostat(_Component):
    """滑动变阻器，矩形加滑片箭头。slider 是滑片位置，从 0 到 1，通常写成 lambda f: f.R2 / 20。"""

    def __init__(self, x, y, slider, horizontal=True, text=None, text_side="bottom", name=None, show=()):
        super().__init__(x, y, horizontal, text, text_side, name, show)
        self.slider = slider

    def draw(self, f):
        width, height = self._extent()
        center = self._center(f)
        body = Rectangle(
            width=width, height=height, stroke_color=INK, stroke_width=3, fill_color=_BACKGROUND, fill_opacity=1
        ).move_to(center)
        along = self.SIZE[0]
        offset = (min(max(_val(self.slider, f), 0.0), 1.0) - 0.5) * along
        tip = center + self._axis() * offset + (_point(0, self.SIZE[1] / 2) if self.horizontal else _point(self.SIZE[1] / 2, 0))
        tail = tip + (_point(0, 0.42) if self.horizontal else _point(0.42, 0))
        arrow = Arrow(tail, tip, buff=0, color=ACCENT, stroke_width=4, max_tip_length_to_length_ratio=0.4)
        return self._with_label(VGroup(body, arrow), f)


class Battery(_Component):
    """电源，一长一短两条线，长线是正极。positive_first 为真时，正极在左边（竖直放置时在上边）。"""

    SIZE = (0.26, 0.56)

    def __init__(self, x, y, horizontal=True, text=None, text_side="top", positive_first=True, name=None, show=()):
        super().__init__(x, y, horizontal, text, text_side, name, show)
        self.positive_first = positive_first

    def draw(self, f):
        center = self._center(f)
        width, height = self._extent()
        patch = Rectangle(width=width, height=height, stroke_width=0, fill_color=_BACKGROUND, fill_opacity=1).move_to(center)
        axis, across = (self._axis(), _point(0, 1)) if self.horizontal else (_point(0, 1), _point(1, 0))
        sign = -1 if self.positive_first else 1
        if not self.horizontal:
            sign = -sign
        long_at = center + axis * sign * 0.1
        short_at = center - axis * sign * 0.1
        group = VGroup(
            patch,
            Line(long_at - across * 0.28, long_at + across * 0.28, color=INK, stroke_width=3),
            Line(short_at - across * 0.14, short_at + across * 0.14, color=INK, stroke_width=6),
        )
        return self._with_label(group, f)


class Bulb(_Component):
    """灯泡，圆圈加叉。brightness 是亮度，从 0 到 1，通常写成和电功率成比例的 lambda f: ...。"""

    SIZE = (0.56, 0.56)

    def __init__(self, x, y, brightness=1.0, horizontal=True, text=None, text_side="top", name=None, show=()):
        super().__init__(x, y, horizontal, text, text_side, name, show)
        self.brightness = brightness

    def draw(self, f):
        center = self._center(f)
        level = min(max(_val(self.brightness, f), 0.0), 1.0)
        group = VGroup(
            Circle(radius=0.28, stroke_width=0, fill_color=_BACKGROUND, fill_opacity=1).move_to(center),
            Circle(radius=0.28, stroke_width=0, fill_color=ROPE, fill_opacity=level * 0.9).move_to(center),
            Circle(radius=0.28, color=INK, stroke_width=3).move_to(center),
        )
        reach = 0.28 * 0.707
        for sign in (1, -1):
            group.add(
                Line(center + _point(-reach, -reach * sign), center + _point(reach, reach * sign), color=INK, stroke_width=3)
            )
        return self._with_label(group, f)


class Meter(_Component):
    """电表，kind 是 "A"（电流表）或 "V"（电压表）。text 通常是读数，比如 lambda f: f"{f.I:.2f} A"。"""

    SIZE = (0.56, 0.56)

    def __init__(self, x, y, kind, horizontal=True, text=None, text_side="top", name=None, show=()):
        super().__init__(x, y, horizontal, text, text_side, name, show)
        self.kind = kind

    def draw(self, f):
        center = self._center(f)
        group = VGroup(
            Circle(radius=0.28, color=INK, stroke_width=3, fill_color=_BACKGROUND, fill_opacity=1).move_to(center),
            _text(self.kind, 22, INK).move_to(center),
        )
        return self._with_label(group, f)


class Switch(_Component):
    """开关。closed 为真时闭合，可以写成 lambda f: ... 让它在某个阶段合上。"""

    SIZE = (0.7, 0.2)

    def __init__(self, x, y, closed=True, horizontal=True, text=None, text_side="top", name=None, show=()):
        super().__init__(x, y, horizontal, text, text_side, name, show)
        self.closed = closed

    def draw(self, f):
        center = self._center(f)
        axis = self._axis()
        across = _point(0, 1) if self.horizontal else _point(1, 0)
        start, end = center - axis * 0.3, center + axis * 0.3
        blade_end = end if _val(self.closed, f) else end + across * 0.28 - axis * 0.06
        width, height = self._extent()
        group = VGroup(
            Rectangle(width=width, height=height, stroke_width=0, fill_color=_BACKGROUND, fill_opacity=1).move_to(center),
            Line(start, blade_end, color=INK, stroke_width=3),
            Dot(start, radius=0.05, color=INK),
            Dot(end, radius=0.05, color=INK),
        )
        return self._with_label(group, f)


class Road(Part):
    """水平路面，从 x0 到 x1，表面在 y，代表 length 米，每隔 tick 米标一个刻度，刻度不超过 8 个。

    road.x_at(d) 把距离（米）换算成画面横坐标，给 Cart 用：x=lambda f: road.x_at(f.s)。
    road.scale 是每米对应的画面长度。
    """

    static = True

    def __init__(self, x0, x1, y, length, tick, unit="m"):
        super().__init__()
        if length / tick > 10:
            raise ValueError(f"Road 的刻度太密：{length} 米每隔 {tick} 米一个，会挤在一起")
        self.x0, self.x1, self.y, self.length, self.tick, self.unit = x0, x1, y, length, tick, unit
        self.scale = (x1 - x0) / length

    def x_at(self, distance):
        return self.x0 + distance * self.scale

    def draw(self, f):
        group = VGroup(Line(_point(self.x0, self.y), _point(self.x1, self.y), color=STEEL, stroke_width=4))
        for value in _ticks(0, self.length, self.tick):
            x = self.x_at(value)
            group.add(Line(_point(x, self.y), _point(x, self.y - 0.1), color=STEEL, stroke_width=2))
            group.add(_text(_tick_text(value), 16, STEEL).next_to(_point(x, self.y - 0.1), _point(0, -1), buff=0.05))
        return group


class Cart(Part):
    """小车或火车，车身中心横坐标是 x，车轮压在路面 y 上。text 写在车身上。火车就把 w 设成车长乘以 road.scale。"""

    def __init__(self, x, y, w=0.9, h=0.42, text=None, color=OBJECT, name=None, show=()):
        super().__init__(name, show)
        self.x, self.y, self.w, self.h, self.text, self.color = x, y, w, h, text, color

    def draw(self, f):
        x, y = _val(self.x, f), _val(self.y, f)
        wheel = 0.08
        body_y = y + wheel * 2 + self.h / 2
        group = VGroup(
            Rectangle(
                width=self.w, height=self.h, stroke_color=self.color, fill_color=self.color, fill_opacity=0.35
            ).move_to(_point(x, body_y)),
            Circle(radius=wheel, color=STEEL, stroke_width=3).move_to(_point(x - self.w * 0.3, y + wheel)),
            Circle(radius=wheel, color=STEEL, stroke_width=3).move_to(_point(x + self.w * 0.3, y + wheel)),
        )
        content = _val(self.text, f)
        if content:
            group.add(_text(content, 16, INK).move_to(_point(x, body_y)))
        return group

    def bounds(self, f):
        x, y = _val(self.x, f), _val(self.y, f)
        return x - self.w / 2, y, x + self.w / 2, y + 0.16 + self.h

    def problems(self, f):
        content = _val(self.text, f)
        if content and _text(content, 16, INK).width > self.w:
            return [f"车身上的文字「{content}」放不下，车身宽 {self.w}"]
        return []


def _ticks(start, stop, step):
    count = int(round((stop - start) / step))
    return [start + step * i for i in range(count + 1)]


def _tick_text(value):
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


class Beaker(Part):
    """盛水的容器，底部中心在 (x, y0)，宽 w 高 h。level 是水面的纵坐标，可以随帧变化。

    想让物块显得泡在水里，就先 add 物块，再 add 容器。
    """

    def __init__(self, x, y0, w, h, level, name=None, show=()):
        super().__init__(name, show)
        self.x, self.y0, self.w, self.h, self.level = x, y0, w, h, level

    def backdrop(self):
        left, right = self.x - self.w / 2, self.x + self.w / 2
        top = self.y0 + self.h
        wall = VMobject(stroke_color=STEEL, stroke_width=4)
        wall.set_points_as_corners(
            [_point(left, top), _point(left, self.y0), _point(right, self.y0), _point(right, top)]
        )
        return wall

    def draw(self, f):
        level = _val(self.level, f)
        return Rectangle(
            width=self.w - 0.04, height=level - self.y0, stroke_width=0, fill_color=WATER, fill_opacity=0.32
        ).move_to(_point(self.x, (level + self.y0) / 2))

    def bounds(self, f):
        return self.x - self.w / 2, self.y0, self.x + self.w / 2, _val(self.level, f)

    def edges(self, f):
        left, right = self.x - self.w / 2, self.x + self.w / 2
        top = self.y0 + self.h
        return [(left, self.y0, left, top), (right, self.y0, right, top), (left, self.y0, right, self.y0)]


class SpringScale(Part):
    """弹簧测力计，顶部中心在 (x, top)。reading 是示数，max_reading 是量程。

    hook_y 是下端挂钩的纵坐标，可以当作连杆的端点。
    """

    WIDTH = 0.6
    HEIGHT = 1.6
    HOOK = 0.3

    def __init__(self, x, top, reading, max_reading, name=None, show=()):
        super().__init__(name, show)
        self.x, self.top, self.reading, self.max_reading = x, top, reading, max_reading

    @property
    def hook_y(self):
        return lambda f: _val(self.top, f) - self.HEIGHT - self.HOOK

    def draw(self, f):
        top = _val(self.top, f)
        center = _point(self.x, top - self.HEIGHT / 2)
        body = Rectangle(
            width=self.WIDTH, height=self.HEIGHT, stroke_color=STEEL, stroke_width=3, fill_color="#1D2630", fill_opacity=1
        ).move_to(center)
        group = VGroup(body, Line(center + _point(0, -self.HEIGHT / 2), center + _point(0, -self.HEIGHT / 2 - self.HOOK), color=STEEL, stroke_width=3))
        usable = self.HEIGHT - 0.3
        for i in range(6):
            y = top - 0.15 - usable * i / 5
            group.add(Line(_point(self.x - 0.2, y), _point(self.x, y), color=STEEL, stroke_width=2))
        y = top - 0.15 - usable * min(_val(self.reading, f) / self.max_reading, 1.0)
        group.add(Line(_point(self.x - 0.26, y), _point(self.x + 0.2, y), color=ACCENT, stroke_width=5))
        return group

    def bounds(self, f):
        top = _val(self.top, f)
        return self.x - self.WIDTH / 2, top - self.HEIGHT, self.x + self.WIDTH / 2, top
