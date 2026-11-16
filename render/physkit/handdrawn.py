"""手绘风的圈、下划线和勾，用来在读题时标出重要条件。

画法参考 rough-notation（MIT，https://github.com/rough-stuff/rough-notation）：椭圆加一点平滑的抖动，
描两遍，首尾故意不完全闭合，看起来像老师用笔圈的。随机数全部由种子决定，同一帧每次画出来都一样。
"""

import math
import random

import numpy as np
from manim import VGroup, VMobject

PEN = "#FF7A59"
CHECK = "#7BD389"
HIGHLIGHT = "#E8C547"


def _noise(seed, terms=3):
    """几个低频正弦叠起来，比纯随机平滑，像手抖而不是锯齿。"""
    rng = random.Random(seed)
    waves = [(rng.uniform(1, 3.5), rng.uniform(0, 2 * math.pi), rng.uniform(0.3, 1)) for _ in range(terms)]
    total = sum(w for _, _, w in waves)
    return lambda t: sum(w * math.sin(k * t + p) for k, p, w in waves) / total


def ellipse(center, rx, ry, seed=1, color=PEN, width=4):
    """圈：从左上方起笔，顺时针转一圈多一点，第二笔稍微错开、细一点。"""
    rng = random.Random(seed)
    group = VGroup()
    for k in range(2):
        wobble = _noise(seed * 31 + k)
        start = rng.uniform(2.2, 2.8)
        sweep = 2 * math.pi + rng.uniform(0.25, 0.6)
        tilt = rng.uniform(-0.06, 0.06)
        scale = 1 + 0.06 * k
        points = []
        for i in range(60):
            t = start - sweep * i / 59
            r = 1 + 0.06 * wobble(t * 1.3)
            x, y = rx * scale * r * math.cos(t), ry * scale * r * math.sin(t)
            x, y = x * math.cos(tilt) - y * math.sin(tilt), x * math.sin(tilt) + y * math.cos(tilt)
            points.append(np.array([center[0] + x, center[1] + y, 0.0]))
        stroke = VMobject(stroke_color=color, stroke_width=width * (1 - 0.25 * k))
        stroke.set_points_smoothly(points)
        group.add(stroke)
    return group


def underline(x0, x1, y, seed=3, color=PEN, width=4):
    """下划线：中间略微下垂，右端往上挑一点。"""
    wobble = _noise(seed)
    points = []
    for i in range(24):
        s = i / 23
        x = x0 - 0.05 + (x1 - x0 + 0.12) * s
        points.append(np.array([x, y - 0.025 * math.sin(math.pi * s) + 0.015 * wobble(s * 6) + 0.05 * s**6, 0.0]))
    stroke = VMobject(stroke_color=color, stroke_width=width)
    stroke.set_points_smoothly(points)
    return VGroup(stroke)


def check(at, size=0.35, seed=2, color=CHECK, width=5):
    """勾：短的一笔向右下，长的一笔向右上，带一点弧度。"""
    rng = random.Random(seed)
    x, y = at
    a = np.array([x - size * 0.55, y + size * 0.05, 0.0])
    b = np.array([x - size * 0.1 + rng.uniform(-0.03, 0.03), y - size * 0.45, 0.0])
    c = np.array([x + size * 0.75, y + size * 0.6 + rng.uniform(-0.05, 0.05), 0.0])
    stroke = VMobject(stroke_color=color, stroke_width=width)
    stroke.set_points_smoothly([a, (a + b) / 2 + np.array([-0.02, -0.03, 0.0]), b,
                                (b + c) / 2 + np.array([-0.06, 0.02, 0.0]), c])
    return VGroup(stroke)


def partial(mark, progress):
    """画到 progress（0 到 1）时的样子，几笔按顺序依次画出。"""
    if progress >= 1:
        return mark
    out = VGroup()
    strokes = list(mark.submobjects)
    for i, stroke in enumerate(strokes):
        local = min(max(progress * len(strokes) - i, 0.0), 1.0)
        if local > 0:
            piece = stroke.copy()
            piece.pointwise_become_partial(stroke, 0, local)
            out.add(piece)
    return out
