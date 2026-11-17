"""讲解的固定结构：开头读题并手绘圈出重要条件，然后题目缩到右上角；换小问时题目放大、划出这一问，再缩回去。

这些由系统自动安排，模型只写读题旁白、要圈哪几处、每个阶段属于第几问。
"""

import re

import numpy as np
from manim import Rectangle, Text, VGroup, VMobject

from . import handdrawn
from .parts import CAPTION_TOP, FONT, INK, Part, _BACKGROUND, _point

# 读题时题目铺在画面中间；缩小后放在右侧一列的最上面，板书接在它下面
FULL_WIDTH = 12.4
FULL_CENTER_Y = 0.35
FULL_MAX_HEIGHT = 6.4
FULL_FONT = 32
LINE_SPACING = 0.42
THUMB_LEFT = 0.95
THUMB_TOP = 3.85
THUMB_WIDTH = 5.95
THUMB_MAX_HEIGHT = 1.35
THUMB_COLOR = "#B9C7C0"

MARK_SECONDS = 0.55  # 画一个圈的时间
SHRINK_SECONDS = 0.8
GROW_SECONDS = 0.6
UNDERLINE_SECONDS = 0.6
QUESTION_NAMES = "一二三四五六七八九"
_SPACE = re.compile(r"\s+")


def plain(text):
    """去掉空白，题目里找短语、和 Text 的字形一一对应都用这个。"""
    return _SPACE.sub("", text)


# ---------- 读题旁白：题目原文转成口语 ----------

_UNITS = [
    ("J/(kg·℃)", "焦每千克摄氏度"), ("J/(kg·°C)", "焦每千克摄氏度"),
    ("kg/m³", "千克每立方米"), ("kg/m3", "千克每立方米"), ("g/cm³", "克每立方厘米"), ("g/cm3", "克每立方厘米"),
    ("N/kg", "牛每千克"), ("km/h", "千米每小时"), ("m/s", "米每秒"), ("J/kg", "焦每千克"), ("J/m³", "焦每立方米"),
    ("kW·h", "千瓦时"), ("kW h", "千瓦时"), ("kWh", "千瓦时"), ("r/(kW·h)", "转每千瓦时"),
    ("kPa", "千帕"), ("Pa", "帕"), ("kW", "千瓦"), ("W", "瓦"), ("kJ", "千焦"), ("J", "焦"), ("kN", "千牛"), ("N", "牛"),
    ("cm²", "平方厘米"), ("cm2", "平方厘米"), ("dm²", "平方分米"), ("dm2", "平方分米"), ("m²", "平方米"), ("m2", "平方米"),
    ("cm³", "立方厘米"), ("cm3", "立方厘米"), ("dm³", "立方分米"), ("dm3", "立方分米"), ("m³", "立方米"), ("m3", "立方米"),
    ("mm", "毫米"), ("cm", "厘米"), ("dm", "分米"), ("km", "千米"), ("mL", "毫升"), ("ml", "毫升"), ("L", "升"),
    ("min", "分钟"), ("kg", "千克"), ("mA", "毫安"), ("Ω", "欧"), ("℃", "摄氏度"), ("°C", "摄氏度"),
    ("m", "米"), ("s", "秒"), ("h", "小时"), ("g", "克"), ("t", "吨"), ("V", "伏"), ("A", "安"),
]
_NUMBER = r"\d+(?:\.\d+)?"
_UNIT_PATTERN = re.compile(
    rf"({_NUMBER}(?:\s*[×x]\s*10\s*(?:\^|<sup>)?\s*[-−⁻]?\s*[\d⁰¹²³⁴⁵⁶⁷⁸⁹]+(?:</sup>)?)?)\s*("
    + "|".join(re.escape(unit) for unit, _ in _UNITS)
    + r")(?![A-Za-z])"
)
_POWER = re.compile(r"(\d+(?:\.\d+)?)\s*[×x]\s*10\s*(?:\^|<sup>)?\s*([-−⁻]?)\s*([\d⁰¹²³⁴⁵⁶⁷⁸⁹]+)(?:</sup>)?")
_SUPERSCRIPT = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
_QUESTION_MARK = re.compile(r"[（(]\s*(\d)\s*[）)]")
_CIRCLED = {"①": "第一", "②": "第二", "③": "第三", "④": "第四"}


def spoken_problem(text):
    """题目原文改成老师读题的说法：单位读成中文，10 的几次方读出来，（1）读成第一问。"""
    units = dict(_UNITS)
    spoken = _UNIT_PATTERN.sub(lambda m: f"{m.group(1)}{units[m.group(2)]}", text)
    spoken = _POWER.sub(
        lambda m: f"{m.group(1)}乘10的{'负' if m.group(2) else ''}{m.group(3).translate(_SUPERSCRIPT)}次方", spoken
    )
    spoken = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"百分之\1", spoken)
    spoken = _QUESTION_MARK.sub(lambda m: f"第{QUESTION_NAMES[int(m.group(1)) - 1]}问，", spoken)
    for symbol, word in _CIRCLED.items():
        spoken = spoken.replace(symbol, word + "，")
    spoken = re.sub(r"ρ\s*([一-鿿]{1,2})", r"\1的密度", spoken)
    spoken = spoken.replace("＝", "等于").replace("=", "等于").replace("×", "乘").replace("÷", "除以")
    spoken = re.sub(r"[（(]\s*[）)]", "", spoken)  # 选择题的空括号
    spoken = re.sub(r"_{2,}|＿+", "多少", spoken)  # 填空题的横线
    spoken = _SPACE.sub("", spoken)
    return spoken


_QUESTION_LABEL = re.compile(r"[（(]\s*([1-9])\s*[）)]")


def split_questions(text):
    """把题目拆成题干和各小问：返回 (题干, {1: "第一问的问法", 2: ...})。没有（1）（2）这样的小问时，小问是空的。

    小问要从 (1) 开始连续编号才算，选择题选项里偶然出现的括号数字不算。题干末尾的「求：」去掉。
    """
    found = list(_QUESTION_LABEL.finditer(text))
    labels = [int(m.group(1)) for m in found]
    expected = list(range(1, len(labels) + 1))
    if len(labels) < 2 or labels != expected:
        return text, {}
    stem = re.sub(r"[，,\s]*(求|问)?[:：]?\s*$", "", text[: found[0].start()].rstrip())
    questions = {}
    for index, match in enumerate(found):
        stop = found[index + 1].start() if index + 1 < len(found) else len(text)
        body = text[match.end(): stop].strip()
        questions[labels[index]] = re.sub(r"[；;，,。.？?\s]+$", "", body)
    return stem + ("。" if stem and stem[-1] not in "。！？；" else ""), questions


def split_sentences(text, limit):
    """按句号、分号拆成几句，每句不超过 limit 个字。"""
    pieces = [p for p in re.split(r"(?<=[。！？；;])", text) if p.strip()]
    lines = []
    for piece in pieces:
        while len(piece) > limit:
            cut = max(piece.rfind("，", 0, limit), piece.rfind(",", 0, limit))
            cut = cut + 1 if cut > limit // 3 else limit
            lines.append(piece[:cut])
            piece = piece[cut:]
        if piece:
            lines.append(piece)
    return lines


# ---------- 题目卡片 ----------

_NO_LINE_START = "，。；：、）》！？,.;:)!?"


class _Layout:
    """题目排成几行。每行一个 Text，记下每个非空白字符落在哪一行的第几个字形。"""

    def __init__(self, text):
        self.text = text.strip()
        size = FULL_FONT
        while True:
            # 按字形宽度估的行宽会偏小（中文标点占整字宽但字形窄），排出来超宽就收窄重排，最多三次
            limit = FULL_WIDTH
            for _ in range(3):
                rows = self._wrap(size, limit)
                texts = VGroup(*[Text(row, font=FONT, font_size=size, color=INK) for row in rows])
                if texts.width <= FULL_WIDTH:
                    break
                limit -= max(row.width for row in texts) - FULL_WIDTH + 0.05
            texts.arrange(_point(0, -1), aligned_edge=_point(-1, 0), buff=LINE_SPACING * size / FULL_FONT)
            if texts.height <= FULL_MAX_HEIGHT or size <= 20:
                break
            size -= 2
        texts.move_to(_point(0, FULL_CENTER_Y))
        self.rows, self.texts, self.size = rows, texts, size
        self.glyphs = [glyph for text in texts for glyph in text.submobjects]
        self.row_of = [index for index, text in enumerate(texts) for _ in text.submobjects]
        self.flat = "".join(plain(row) for row in rows)
        if len(self.flat) != len(self.glyphs):
            # 个别字符（比如组合符号）字形数对不上时，圈注退化成不画，不影响读题
            self.glyphs = []

    def _wrap(self, size, limit=None):
        """先整段排一次量出每个字的宽度，再按宽度断行，句首不放标点。"""
        source = self.text.replace("\n", "")
        whole = Text(source, font=FONT, font_size=size)
        chars = [c for c in source]
        glyphs = iter(whole.submobjects)
        widths = []
        for char in chars:
            if char.isspace():
                widths.append(size / FULL_FONT * 0.16)
            else:
                glyph = next(glyphs, None)
                widths.append(glyph.width + size / FULL_FONT * 0.05 if glyph is not None else size / FULL_FONT * 0.4)
        rows, row, used = [], "", 0.0
        for char, width in zip(chars, widths):
            if used + width > (limit or FULL_WIDTH) and row and char not in _NO_LINE_START:
                rows.append(row.rstrip())
                row, used = "", 0.0
                if char.isspace():
                    continue
            row += char
            used += width
        if row.strip():
            rows.append(row.rstrip())
        return rows

    def find(self, phrase, after=0):
        """短语在题目里的位置（去掉空白后的下标），找不到返回 None。"""
        target = plain(phrase)
        if not target:
            return None
        position = self.flat.find(target, after)
        if position < 0:
            position = self.flat.find(target)
        return None if position < 0 else (position, position + len(target))

    def spans(self, start, end):
        """一段文字按行拆开，每行给出 (左, 右, 下, 中心 y, 高)。"""
        result = []
        for row in sorted({self.row_of[i] for i in range(start, end)}):
            glyphs = [self.glyphs[i] for i in range(start, end) if self.row_of[i] == row]
            group = VGroup(*glyphs)
            result.append((group.get_left()[0], group.get_right()[0], group.get_bottom()[1],
                           group.get_center()[1], group.height))
        return result


def _mark_shape(layout, span, kind, seed):
    pieces = layout.spans(*span)
    if not pieces:
        return None
    line_height = layout.size / FULL_FONT * 0.42
    if kind == "circle" and len(pieces) == 1:
        left, right, _, center_y, _ = pieces[0]
        return handdrawn.ellipse(((left + right) / 2, center_y), (right - left) / 2 + 0.12, line_height / 2 + 0.2, seed)
    if kind == "check":
        left, right, _, center_y, _ = pieces[-1]
        return handdrawn.check((right + 0.38, center_y), size=0.38, seed=seed)
    # 下划线，或者跨行的圈改成每行一条下划线
    group = VGroup()
    for k, (left, right, bottom, _, _) in enumerate(pieces):
        group.add(*handdrawn.underline(left, right, bottom - 0.1, seed=seed + k).submobjects)
    return group


def _question_span(layout, number):
    """第 number 问的文字：从（number）开始，到下一问或句末为止。"""
    flat = layout.flat
    match = None
    for candidate in (f"（{number}）", f"({number})"):
        position = flat.find(candidate)
        if position >= 0:
            match = position
            break
    if match is None:
        return None
    following = [flat.find(f"（{number + 1}）", match + 1), flat.find(f"({number + 1})", match + 1)]
    end = min([p for p in following if p > 0], default=len(flat))
    while end > match and flat[end - 1] in "。；;，,？?":
        end -= 1
    return match, end


def _smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def _plain_copy(group):
    """把文字拆成只有轮廓和颜色的普通 VMobject，画出来一样，拷贝快得多。"""
    plain = VGroup()
    for piece in group.family_members_with_points():
        shape = VMobject()
        shape.set_points(piece.points.copy())
        shape.match_style(piece, family=False)
        plain.add(shape)
    return plain


class ProblemCard(Part):
    """题目卡片：读题时铺满画面，读完缩到右上角；换小问时放大、划出这一问，再缩回去。"""

    def __init__(self, timeline):
        super().__init__()
        self.timeline = timeline
        self.layout = _Layout(timeline.text)
        full = self.layout.texts
        self.scale = min(THUMB_WIDTH / full.width, THUMB_MAX_HEIGHT / full.height, 1.0)
        width, height = full.width * self.scale, full.height * self.scale
        self.thumb_center = np.array([THUMB_LEFT + width / 2, THUMB_TOP - height / 2, 0.0])
        self.thumb_bottom = THUMB_TOP - height
        self.marks = []
        if self.layout.glyphs:
            cursor = 0
            for number, mark in enumerate(timeline.marks):
                span = self.layout.find(mark["phrase"], cursor)
                if span is None:
                    continue
                cursor = span[1]
                shape = _mark_shape(self.layout, span, mark["kind"], seed=7 + number * 13)
                if shape is not None:
                    self.marks.append((mark["t"], shape))
        self.question_lines = {}
        if self.layout.glyphs:
            for switch in timeline.switches:
                span = _question_span(self.layout, switch["question"])
                if span:
                    shape = _mark_shape(self.layout, span, "underline", seed=101 + switch["question"])
                    shape.set_color(handdrawn.HIGHLIGHT)
                    self.question_lines[switch["question"]] = (switch["t_underline"], switch["t_end"], shape)
        self._cache = {}
        # 题目文字的轻量副本：只留轮廓和颜色。Text 带着大量排版信息，长题目每帧深拷贝一次要近一秒
        self._plain = _plain_copy(self.layout.texts)

    def alpha(self, t):
        """1 是铺满画面，0 是右上角的小图。"""
        reading = self.timeline.reading_window
        if reading is None:
            return 0.0
        if t < reading[1]:
            # 有好几问时读完题干不缩小，接着拿出第一问
            if not self.timeline.reading_shrinks or t < reading[1] - SHRINK_SECONDS:
                return 1.0
            return 1 - _smooth((t - (reading[1] - SHRINK_SECONDS)) / SHRINK_SECONDS)
        for switch in self.timeline.switches:
            begin, end = switch["t"], switch["t_end"]
            if begin <= t < end:
                if switch["grow"] and t < begin + GROW_SECONDS:
                    return _smooth((t - begin) / GROW_SECONDS)
                if t > end - SHRINK_SECONDS:
                    return 1 - _smooth((t - (end - SHRINK_SECONDS)) / SHRINK_SECONDS)
                return 1.0
        return 0.0

    def _question_line(self, t):
        """当前这一问的划线和它开始画的时刻。换到下一问时，上一问的划线去掉。"""
        current = None
        for start, _, shape in sorted(self.question_lines.values(), key=lambda item: item[0]):
            if t >= start:
                current = (start, shape)
        return current

    def _content(self, t, alpha):
        texts = self._plain.copy()
        if alpha < 0.5:
            texts.set_color(THUMB_COLOR)
        group = VGroup(texts)
        for start, shape in self.marks:
            progress = (t - start) / MARK_SECONDS
            if progress > 0:
                group.add(handdrawn.partial(shape, progress).copy())
        line = self._question_line(t)
        if line:
            group.add(handdrawn.partial(line[1], (t - line[0]) / UNDERLINE_SECONDS).copy())
        return group

    def _redraw_key(self, f):
        """题目卡片停着不动时（大多数帧），返回它的状态。题目长时重画一次要几百毫秒，渲染时靠它跳过。

        只看卡片自己的动画（放大缩小、圈注、划线），板书逐字写出时卡片并不动。
        """
        t = f.clock
        alpha = self.alpha(t)
        if alpha not in (0.0, 1.0):
            return None
        if any(0 < (t - start) / MARK_SECONDS < 1 for start, _ in self.marks):
            return None
        line = self._question_line(t)
        if line and (t - line[0]) / UNDERLINE_SECONDS < 1:
            return None
        return (alpha, sum(1 for start, _ in self.marks if t >= start + MARK_SECONDS), line and line[0])

    def draw(self, f):
        t = f.clock
        alpha = self.alpha(t)
        still = self.timeline.overlay_key(f.index) is None and alpha in (0.0, 1.0)
        if still:
            line = self._question_line(t)
            state = (alpha, sum(1 for start, _ in self.marks if t >= start + MARK_SECONDS), line and line[0])
            if state in self._cache:
                # Manim 每帧用 become 改写拿到的对象，缓存要给副本，否则会被改坏
                return self._cache[state].copy()
        content = self._content(t, alpha)
        origin = self.layout.texts.get_center()
        scale = self.scale + (1 - self.scale) * alpha
        content.scale(scale, about_point=origin).shift((self.thumb_center - origin) * (1 - alpha))
        # 题目放大时盖住后面的实物图和板书。结构每帧都一样（底板在下、题目在上），
        # 否则 Manim 沿用上一帧的对象时会把底板排到题目上面，把题目盖住
        cover = Rectangle(width=14.3, height=4 - CAPTION_TOP + 0.05, stroke_width=0,
                          fill_color=_BACKGROUND, fill_opacity=_smooth(alpha * 1.4))
        group = VGroup(cover.move_to(_point(0, (4 + CAPTION_TOP) / 2)), content)
        if still:
            self._cache[state] = group.copy()
        return group
