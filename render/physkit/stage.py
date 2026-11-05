"""舞台：把零件组合成一个场景，加上板书和字幕，并在渲染前检查布局。"""

from manim import MarkupText, Rectangle, Text, VGroup

from .parts import FONT, INK, ROPE, Block, Part, Plot, Rope, _point
from .timeline import SceneError

FRAME_WIDTH = 8 * 16 / 9
FRAME_HEIGHT = 8.0
STAGE_RIGHT = 0.75  # 实物不能超过这条线，右边是板书和坐标图
CAPTION_TOP = -3.3  # 实物不能低于这条线，下面是字幕
BOARD_LEFT = 0.95
BOARD_TOP = 3.65
BOARD_WIDTH = 5.95
BOARD_LINE_HEIGHT = 0.56
BOARD_MAX_LINES = 6
CAPTION_WIDTH = 13.4
_EDGE_MARGIN = 0.05


class _Board(Part):
    """画面右上方的板书，只显示最新的几行，最新一行高亮。"""

    def __init__(self, timeline):
        super().__init__()
        self.timeline = timeline
        self._groups = {}

    def _group(self, count):
        if count not in self._groups:
            group = VGroup()
            shown = self.timeline.board_lines[max(count - BOARD_MAX_LINES, 0) : count]
            for row, line in enumerate(shown):
                is_newest = row == len(shown) - 1
                text = MarkupText(line["text"], font=FONT, font_size=25, color=ROPE if is_newest else INK)
                if text.width > BOARD_WIDTH:
                    text.scale(BOARD_WIDTH / text.width)
                text.move_to(_point(BOARD_LEFT, BOARD_TOP - BOARD_LINE_HEIGHT * row), aligned_edge=_point(-1, 0))
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

    def __init__(self, timeline, background="#10151C"):
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
                    if (
                        text.get_left()[0] < max(x0, x1)
                        and min(x0, x1) < text.get_right()[0]
                        and text.get_bottom()[1] < max(y0, y1)
                        and min(y0, y1) < text.get_top()[1]
                    ):
                        found.append(f"第 {index} 帧：文字「{text.text}」压在 {type(part).__name__} #{number} 的边线上")
        return found
