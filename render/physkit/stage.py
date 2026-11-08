"""舞台：把零件组合成一个场景，加上板书和字幕，并在渲染前检查布局。"""

import re

from manim import MarkupText, Rectangle, Text, VGroup

from .parts import _BACKGROUND, CAPTION_TOP, FONT, INK, ROPE, STAGE_RIGHT, Block, Part, Plot, Rope, _point
from .timeline import SceneError

FRAME_WIDTH = 8 * 16 / 9
FRAME_HEIGHT = 8.0
BOARD_LEFT = 0.95
BOARD_TOP = 3.65
BOARD_WIDTH = 5.95
BOARD_LINE_HEIGHT = 0.56
BOARD_MAX_LINES = 6
CAPTION_WIDTH = 13.4
_EDGE_MARGIN = 0.05


class _Board(Part):
    """画面右上方的板书，最新一条算式高亮。

    所有行用同一个字号。一条算式太长时，在等号或中文逗号处换行，续行缩进，不再整行缩小，
    否则长的算式字小、短的字大，看起来很乱。
    题目有好几问时按问分开写，每问前标 (1)、(2)；写不下时擦掉前面的问，只留当前这一问。
    """

    FONT_SIZE = 25
    INDENT = 0.45

    def __init__(self, timeline):
        super().__init__()
        self.timeline = timeline
        self._groups = {}
        self._rows = {}

    def _text(self, content, color=INK):
        return MarkupText(_markup(content), font=FONT, font_size=self.FONT_SIZE, color=color)

    def _fits(self, content, indent=0.0):
        return self._text(content).width <= BOARD_WIDTH - indent

    def _split(self, content):
        """把一条算式拆成几行。先按中文逗号分成几个式子，每个式子再按等号贪心地装进一行。"""
        if self._fits(content):
            return [content]
        rows = []
        for clause in re.split(r"\s*，\s*", content):
            pieces = clause.split(" = ")
            row = pieces[0]
            for piece in pieces[1:]:
                candidate = f"{row} = {piece}"
                if self._fits(candidate, self.INDENT if rows else 0.0):
                    row = candidate
                else:
                    rows.append(row)
                    row = f"= {piece}"
            rows.append(row)
        return rows

    def _questions(self):
        return {line["question"] for line in self.timeline.board_lines}

    def _rows_for(self, index):
        """一行板书拆成的几行。题目有好几问时，每一问的第一行前面标上 (1)、(2)。"""
        if index not in self._rows:
            line = self.timeline.board_lines[index]
            text = line["text"]
            first_of_question = index == 0 or self.timeline.board_lines[index - 1]["question"] != line["question"]
            if len(self._questions()) > 1 and first_of_question:
                text = f"({line['question']}) {text}"
            self._rows[index] = self._split(text)
        return self._rows[index]

    def _visible(self, count):
        """要显示哪些行：当前这一问的全部，再往前补完整的上一问，写不下就把上一问擦掉。"""
        runs = []  # 按出现顺序，连续属于同一问的几行算一段
        for index, line in enumerate(self.timeline.board_lines[:count]):
            if runs and runs[-1][0] == line["question"]:
                runs[-1][1].append(index)
            else:
                runs.append((line["question"], [index]))

        def rows_of(indices):
            return [(row, index, k) for index in indices for k, row in enumerate(self._rows_for(index))]

        rows = rows_of(runs[-1][1])
        if len(rows) > BOARD_MAX_LINES:
            return rows[-BOARD_MAX_LINES:]
        for _, indices in reversed(runs[:-1]):
            earlier = rows_of(indices)
            if len(rows) + len(earlier) > BOARD_MAX_LINES:
                break
            rows = earlier + rows
        return rows

    def _group(self, count):
        if count not in self._groups:
            group = VGroup()
            if count:
                for position, (content, index, k) in enumerate(self._visible(count)):
                    text = self._text(content, ROPE if index == count - 1 else INK)
                    indent = self.INDENT if k > 0 else 0.0
                    if text.width > BOARD_WIDTH - indent:
                        # 一个式子本身就放不下时才缩小，正常情况下不会发生
                        text.scale((BOARD_WIDTH - indent) / text.width)
                    text.move_to(
                        _point(BOARD_LEFT + indent, BOARD_TOP - BOARD_LINE_HEIGHT * position),
                        aligned_edge=_point(-1, 0),
                    )
                    group.add(text)
            self._groups[count] = group
        return self._groups[count]

    def draw(self, f):
        return self._group(self.timeline.board_count_at(f.index))


class _Caption(Part):
    """画面底部的字幕。"""

    def __init__(self, timeline):
        super().__init__()
        self.timeline = timeline
        self._groups = {}

    def _group(self, position):
        if position not in self._groups:
            group = VGroup(
                Rectangle(width=FRAME_WIDTH, height=0.66, stroke_width=0, fill_color="#000000", fill_opacity=0.55)
                .move_to(_point(0, -3.67))
            )
            if position is not None:
                text = Text(self.timeline.captions[position]["text"], font=FONT, font_size=28, color=INK)
                if text.width > CAPTION_WIDTH:
                    text.scale(CAPTION_WIDTH / text.width)
                group.add(text.move_to(_point(0, -3.67)))
            self._groups[position] = group
        return self._groups[position]

    def draw(self, f):
        return self._group(self.timeline.caption_at(f.index))


class Stage:
    """一道题的画面。按 add 的先后顺序绘制，后加的盖在上面。板书和字幕由系统自动加上。"""

    def __init__(self, timeline, background=_BACKGROUND):
        self.timeline = timeline
        self.background = background
        self.parts = []
        self.overlays = []

    def add(self, *parts):
        """把零件加到舞台上。"""
        for part in parts:
            if not isinstance(part, Part):
                raise SceneError(f"stage.add 只能加零件，收到的是 {type(part).__name__}")
            self.parts.append(part)

    def bind(self):
        """在时间线算好之后，让需要预先计算的零件做准备，并检查零件的声明。"""
        known = {q["id"] for q in self.timeline.quantities}
        for part in self.parts:
            if hasattr(part, "bind"):
                part.bind(self.timeline)
            for id in part.show:
                if id not in known:
                    raise SceneError(f"零件「{part.name}」的 show 引用了没有声明的物理量 {id}（常数不能放进 show）")
            if part.show and not part.name:
                raise SceneError("声明了 show 的零件必须有 name，否则无法点击")
        self.overlays = [_Board(self.timeline), _Caption(self.timeline)]

    @property
    def all_parts(self):
        return self.parts + self.overlays

    def _clickable(self):
        return [(f"part{index}", part) for index, part in enumerate(self.parts) if part.name]

    def objects(self):
        return {key: {"name": part.name, "quantities": part.show} for key, part in self._clickable()}

    def regions(self):
        """每个可点击零件在每一帧的范围，换算成视频画面的百分比 [x, y, 宽, 高]。"""
        result = {}
        for key, part in self._clickable():
            column = []
            for index in range(self.timeline.frame_count):
                x0, y0, x1, y1 = part.bounds(self.timeline.frame(index))
                column.append(
                    [
                        round((x0 + FRAME_WIDTH / 2) / FRAME_WIDTH * 100, 2),
                        round((FRAME_HEIGHT / 2 - y1) / FRAME_HEIGHT * 100, 2),
                        round((x1 - x0) / FRAME_WIDTH * 100, 2),
                        round((y1 - y0) / FRAME_HEIGHT * 100, 2),
                    ]
                )
            result[key] = column
        return result

    def _sample_frames(self):
        timeline = self.timeline
        moments = [0, timeline.duration]
        for phase in timeline.phases:
            moments += [phase.begin, phase.begin + phase.seconds / 2, phase.begin + phase.seconds]
        moments += [event["moment"].seconds for event in timeline.events]
        return sorted({timeline.frame_at(t) for t in moments})

    def lint(self):
        """在抽样的帧上检查布局，返回问题列表。"""
        found = []
        for index in self._sample_frames():
            f = self.timeline.frame(index)
            texts = []
            for number, part in enumerate(self.all_parts):
                is_overlay = part in self.overlays
                label = f"{type(part).__name__} #{number}"
                mobject = part.draw(None if part.static else f)
                backdrop = part.backdrop()
                for layer in filter(None, [mobject, backdrop]):
                    found.extend(self._edge_problems(layer, label, index))
                    if not is_overlay and not isinstance(part, Plot):
                        found.extend(self._zone_problems(layer, label, index))
                    texts.extend((number, m) for m in layer.get_family() if isinstance(m, (Text, MarkupText)))
                found.extend(f"第 {index} 帧：{problem}" for problem in part.problems(f))
            found.extend(self._overlaps(texts, index))
            found.extend(self._crossings(texts, f, index))
            found.extend(self._rope_through_block(f, index))
        return list(dict.fromkeys(found))

    def _rope_through_block(self, f, index):
        found = []
        for rope in (part for part in self.parts if isinstance(part, Rope)):
            for block in (part for part in self.parts if isinstance(part, Block)):
                left, bottom, right, top = block.bounds(f)
                for x0, y0, x1, y1 in rope.line_pieces(f):
                    if (
                        min(x0, x1) < right - 0.02
                        and left + 0.02 < max(x0, x1)
                        and min(y0, y1) < top - 0.02
                        and bottom + 0.02 < max(y0, y1)
                    ):
                        found.append(f"第 {index} 帧：绳子穿过了物块，要把绳子或物块移开")
        return found

    @staticmethod
    def _has_extent(mobject):
        return mobject.has_points() or bool(mobject.submobjects)

    def _edge_problems(self, mobject, label, index):
        if not self._has_extent(mobject):
            return []
        x0, x1 = mobject.get_left()[0], mobject.get_right()[0]
        y0, y1 = mobject.get_bottom()[1], mobject.get_top()[1]
        half_w, half_h = FRAME_WIDTH / 2 + _EDGE_MARGIN, FRAME_HEIGHT / 2 + _EDGE_MARGIN
        if x0 < -half_w or x1 > half_w or y0 < -half_h or y1 > half_h:
            return [
                f"第 {index} 帧：{label} 超出画面，范围 x {x0:.2f} 到 {x1:.2f}，y {y0:.2f} 到 {y1:.2f}；"
                f"画面范围 x ±{FRAME_WIDTH / 2:.2f}，y ±{FRAME_HEIGHT / 2:.2f}"
            ]
        return []

    def _zone_problems(self, mobject, label, index):
        if not self._has_extent(mobject):
            return []
        found = []
        right = mobject.get_right()[0]
        bottom = mobject.get_bottom()[1]
        if right > STAGE_RIGHT:
            found.append(f"第 {index} 帧：{label} 进入了右侧板书区，右边界 x={right:.2f}，不能超过 {STAGE_RIGHT}")
        if bottom < CAPTION_TOP:
            found.append(f"第 {index} 帧：{label} 进入了底部字幕区，下边界 y={bottom:.2f}，不能低于 {CAPTION_TOP}")
        return found

    @staticmethod
    def _overlaps(texts, index):
        found = []
        for i, (owner_a, a) in enumerate(texts):
            for owner_b, b in texts[i + 1 :]:
                if owner_a == owner_b:
                    continue
                if (
                    a.get_left()[0] < b.get_right()[0]
                    and b.get_left()[0] < a.get_right()[0]
                    and a.get_bottom()[1] < b.get_top()[1]
                    and b.get_bottom()[1] < a.get_top()[1]
                ):
                    found.append(f"第 {index} 帧：文字「{a.text}」和「{b.text}」重叠")
        return found

    def _crossings(self, texts, f, index):
        """文字压在容器壁、物块边框这些线上时，读起来会很吃力。"""
        found = []
        for number, part in enumerate(self.parts):
            for x0, y0, x1, y1 in part.edges(f):
                for owner, text in texts:
                    if owner == number:
                        continue
                    box = (text.get_left()[0], text.get_bottom()[1], text.get_right()[0], text.get_top()[1])
                    if _segment_hits_box(x0, y0, x1, y1, box):
                        found.append(f"第 {index} 帧：文字「{text.text}」压在 {type(part).__name__} #{number} 的边线上")
        return found


def _segment_hits_box(x0, y0, x1, y1, box):
    """线段和文字框是否相交（严格在内部，只擦到边不算）。斜面这样的斜线不能用包围盒判断。"""
    left, bottom, right, top = box
    t0, t1 = 0.0, 1.0
    dx, dy = x1 - x0, y1 - y0
    for p, q in ((-dx, x0 - left), (dx, right - x0), (-dy, y0 - bottom), (dy, top - y0)):
        if abs(p) < 1e-12:
            if q <= 0:
                return False
            continue
        r = q / p
        if p < 0:
            t0 = max(t0, r)
        else:
            t1 = min(t1, r)
        if t0 >= t1:
            return False
    return True


_TAG = re.compile(r"(</?(?:sub|sup)>)")


def _markup(text):
    """板书只认 <sub> 和 <sup>，其余的 <、>、& 都当普通字符，比如 F1 < F2。"""
    pieces = _TAG.split(text)
    return "".join(
        piece if _TAG.fullmatch(piece) else piece.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        for piece in pieces
    )
