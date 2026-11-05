"""时间线：把题目的物理过程和讲解变成逐帧数据。视频和网页面板读的都是这份数据。

动画的快慢由旁白决定，所以题目里的时间不能直接用动画时间，要用 phase.progress(f) 换算。
"""

import bisect
import math
import re

from speech_text import split_clauses

from .numbers import board_number, spoken_number, to_display

FPS = 30
MAX_SECONDS = 300
MAX_SPEECH_CHARS = 120
SPEECH_GAP = 0.35  # 两句旁白之间的停顿（秒）
TAIL_SECONDS = 1.0  # 讲完后多停一会儿
CHARS_PER_SECOND = 4.8  # 还没有配音时，用它估算时长
_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SLOT = re.compile(r"\{(\w+)\}")
_UNIT_AFTER_NUMBER = re.compile(r"\d\s*(?:N|J|W|kg|Pa|cm|mm|km|m|s|g|h|A|V|Ω)(?![A-Za-z])")
_RESERVED = {"index", "clock"}
_EPSILON = 1e-9


class SceneError(Exception):
    """生成的代码有问题。消息会原样回传给模型，所以要写清楚怎么改。"""


class Frame:
    """某一帧的取值。f.h 是物理量 h 在这一帧的值，常数也能这样读。"""

    __slots__ = ("_columns", "_constants", "index", "clock")

    def __init__(self, columns, constants, index, fps):
        self._columns = columns
        self._constants = constants
        self.index = index
        self.clock = index / fps

    def __getattr__(self, name):
        if name in self._constants:
            return self._constants[name]
        try:
            return self._columns[name][self.index]
        except KeyError:
            raise AttributeError(f"物理量 {name} 还没有声明，必须先声明才能使用") from None


class Moment:
    """阶段里的一个时刻，等旁白时长确定后才知道具体是第几秒。"""

    def __init__(self, phase, fraction):
        self.phase = phase
        self.fraction = fraction

    @property
    def seconds(self):
        return self.phase.begin + self.phase.seconds * self.fraction


class Phase:
    """动画的一个阶段，由 timeline.phase() 创建。属性 start、end 是它的开始和结束时刻。"""

    def __init__(self, label, min_seconds):
        self.label = label
        self.min_seconds = min_seconds
        self.animated = min_seconds is not None
        self.lines = []
        self.boards = []
        self.begin = 0.0
        self.seconds = 0.0

    @property
    def start(self):
        return Moment(self, 0.0)

    @property
    def end(self):
        return Moment(self, 1.0)

    def at(self, fraction):
        """本阶段某个进度对应的时刻，at(0.5) 是阶段中点。"""
        return Moment(self, fraction)

    def say(self, text):
        """加一句旁白，按顺序读出，同时显示成字幕。

        写成口语：单位用中文（牛、米、焦），不要写符号。{id} 替换成本阶段结束时的数值。
        """
        if len(text) > MAX_SPEECH_CHARS:
            raise SceneError(f"一句旁白不能超过 {MAX_SPEECH_CHARS} 字，请拆成几句：{text}")
        self.lines.append({"raw": text, "phase": self})

    def board(self, expr):
        """加一行板书，显示在画面右上方，本阶段开始时出现。同一行也会出现在网页面板里，数值随帧变化。

        可以用 <sub> 写下标，比如 "W<sub>有</sub> = Gh = {G} N × {h} m = {W_use} J"。
        """
        self.boards.append(expr)

    def progress(self, f):
        """这一帧在本阶段的进度：开始前是 0，结束后是 1。只有声明了 min_seconds 的阶段才会连续变化。"""
        if not self.animated:
            return 1.0 if f.clock >= self.begin - _EPSILON else 0.0
        return min(max((f.clock - self.begin) / self.seconds, 0.0), 1.0)

    def active(self, f):
        """这一帧是否处在本阶段内，含首尾两帧。"""
        return self.begin - _EPSILON <= f.clock <= self.begin + self.seconds + _EPSILON


class Timeline:
    """题目的物理过程：分哪几个阶段、有哪些物理量、每个物理量怎样随帧变化。"""

    def __init__(self, text, assumptions=()):
        self.text = text
        self.assumptions = list(assumptions)
        self.fps = FPS
        self.phases = []
        self.constants = {}
        self.quantities = []
        self.events = []
        self.answers = []
        self.clock = None
        self.lines = []
        self.board_lines = []
        self.captions = []
        self._columns = None

    @property
    def duration(self):
        return self.phases[-1].begin + self.phases[-1].seconds if self.phases else 0

    @property
    def frame_count(self):
        return round(self.duration * self.fps)

    def phase(self, label, min_seconds=None):
        """按顺序追加一个阶段，返回 Phase。

        物体在运动的阶段必须给 min_seconds，表示动画至少持续多久。讲解时画面不动的阶段不要给。
        阶段的实际时长由旁白决定，旁白比 min_seconds 长时，动画会放慢。
        """
        if min_seconds is not None and min_seconds <= 0:
            raise SceneError(f"阶段「{label}」的 min_seconds 必须大于 0")
        phase = Phase(label, min_seconds)
        self.phases.append(phase)
        return phase

    def constant(self, id, value):
        """声明公式里要用的常数，比如绳子段数 n。"""
        self._check_id(id)
        self.constants[id] = value

    def quantity(self, id, symbol, name, unit, digits, value):
        """声明一个物理量。value 是数值，或 lambda f: ... 这样的函数，可以用 f.x 引用先声明的量。

        symbol 可以含 <sub> 标签，比如 "W<sub>有</sub>"。digits 是显示的小数位数。
        函数返回 None 表示这一帧没有意义，面板会显示“—”。
        """
        self._check_id(id)
        self.quantities.append(
            {"id": id, "symbol": symbol, "name": name, "unit": unit, "digits": digits, "value": value}
        )

    def event(self, moment, label):
        """声明一个关键时刻，moment 写成 lift.at(0.5) 或 lift.end。"""
        if not isinstance(moment, Moment):
            raise SceneError(f"event 的时刻要写成 phase.at(0.5) 或 phase.end，收到的是 {moment!r}")
        self.events.append({"moment": moment, "label": label})

    def answer(self, id, label, at=None):
        """标记题目所求的量，label 要和解答里的答案名称完全一致，系统会逐项核对数值。

        at 是取值时刻，默认取最后一帧。过程结束后会变化的量要指定，比如功率：物体停下后是 0。
        """
        self.answers.append({"id": id, "label": label, "at": at})

    def show_clock(self, id, label):
        """指定面板顶部显示的进度量，比如题中时间或下降深度。"""
        self.clock = {"id": id, "label": label}

    def _check_id(self, id):
        if not _ID.match(id) or id in _RESERVED:
            raise SceneError(f"物理量名 {id!r} 不可用：只能用字母、数字、下划线，也不能叫 index 或 clock")
        if id in self.constants or any(q["id"] == id for q in self.quantities):
            raise SceneError(f"物理量 {id} 声明了两次")

    def compile(self, speech=None):
        """算出每一帧的全部数据。speech 是配音后的实际时长和字幕时间，没有时按字数估算。"""
        if not self.phases:
            raise SceneError("时间线至少要有一个阶段")
        self.lines = [line for phase in self.phases for line in phase.lines]
        if not self.lines:
            raise SceneError("至少要有一句旁白，用 phase.say(...) 添加")
        if speech is not None and len(speech) != len(self.lines):
            raise SceneError(f"配音有 {len(speech)} 句，旁白有 {len(self.lines)} 句")

        for index, line in enumerate(self.lines):
            line["seconds"] = speech[index]["seconds"] if speech else len(line["raw"]) / CHARS_PER_SECOND
        self._layout()
        if self.duration > MAX_SECONDS:
            raise SceneError(f"动画时长 {self.duration:.0f} 秒超过上限 {MAX_SECONDS} 秒，请精简讲解")
        self._compute_columns()
        self._check_references()
        self._fill_text()
        if speech is not None:
            for line, spoken in zip(self.lines, speech):
                if line["text"] != spoken["text"]:
                    raise SceneError(f"旁白里的数值依赖了动画时长：配音是「{spoken['text']}」，现在是「{line['text']}」")
        self._build_captions(speech)
        self._build_board()

    def _layout(self):
        """排出每个阶段的起止时间。阶段边界对齐到整数帧，结束那一帧的进度才正好是 1，读数才是题目的值。"""
        cursor = 0
        for phase in self.phases:
            spoken = sum(line["seconds"] + SPEECH_GAP for line in phase.lines)
            seconds = max(phase.min_seconds or 0.0, spoken)
            if seconds <= 0:
                raise SceneError(f"阶段「{phase.label}」既没有旁白也没有 min_seconds，时长是 0")
            frames = math.ceil(seconds * self.fps - _EPSILON)
            phase.begin = cursor / self.fps
            phase.seconds = frames / self.fps
            offset = phase.begin
            for line in phase.lines:
                line["start"] = offset
                offset += line["seconds"] + SPEECH_GAP
            cursor += frames
        self.phases[-1].seconds += TAIL_SECONDS

    def _compute_columns(self):
        columns = {}
        self._columns = columns
        count = self.frame_count
        for q in self.quantities:
            column = []
            columns[q["id"]] = column
            for index in range(count):
                f = Frame(columns, self.constants, index, self.fps)
                raw = q["value"](f) if callable(q["value"]) else q["value"]
                column.append(self._clean(q["id"], raw, index))
            self._check_digits(q, column)

    @staticmethod
    def _check_digits(q, column):
        """暂停时要能读到准确的数，小量没有小数位时，1.2 米会显示成 1 米。"""
        values = [value for value in column if value is not None]
        if q["digits"] == 0 and values and max(values) - min(values) < 20:
            if any(abs(value - round(value)) > 0.01 for value in values):
                raise SceneError(f"物理量 {q['id']} 有小数，变化范围也小，digits 不能是 0，请用 2")

    def _clean(self, id, raw, index):
        if raw is None:
            return None
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise SceneError(f"物理量 {id} 在第 {index} 帧的值不是数字：{raw!r}")
        if not math.isfinite(raw):
            raise SceneError(f"物理量 {id} 在第 {index} 帧的值无效：{raw}")
        return round(float(raw), 9)

    def _check_references(self):
        known = set(self.constants) | set(self._columns)
        for phase in self.phases:
            for expr in phase.boards:
                self._check_slots(expr, known, "板书")
            for line in phase.lines:
                self._check_slots(line["raw"], known, "旁白")
        for answer in self.answers:
            if answer["id"] not in known:
                raise SceneError(f"answer 引用了没有声明的物理量 {answer['id']}")
            if answer["at"] is not None and not isinstance(answer["at"], Moment):
                raise SceneError(f"answer 的 at 要写成 phase.end 或 phase.at(...)，收到的是 {answer['at']!r}")
        if not self.clock:
            raise SceneError("必须用 show_clock 指定面板顶部显示的进度量")
        if self.clock["id"] not in self._columns:
            raise SceneError(f"show_clock 引用了没有声明的物理量 {self.clock['id']}")

    @staticmethod
    def _check_slots(text, known, where):
        for slot in _SLOT.findall(text):
            if slot not in known:
                raise SceneError(f"{where}「{text}」里的 {{{slot}}} 没有对应的物理量或常数")

    def _fill_text(self):
        for line in self.lines:
            index = self.frame_at(line["phase"].end.seconds)
            line["text"] = _SLOT.sub(lambda m: self._spoken_value(m.group(1), index, spoken_number), line["raw"])
            if _UNIT_AFTER_NUMBER.search(line["text"]):
                raise SceneError(f"旁白要写成口语，数字后面的单位用中文（牛、米、焦、瓦、秒）：{line['text']}")
            if "<" in line["text"]:
                raise SceneError(f"旁白里不能有标签：{line['text']}")

    def _spoken_value(self, id, index, writer):
        """旁白和板书里的数值。很大或很小的数由 writer 写成科学计数法。"""
        if id in self.constants:
            value, digits = self.constants[id], 4
        else:
            value = self._columns[id][index]
            if value is None:
                raise SceneError(f"旁白或板书引用的 {id} 在这一刻没有数值")
            digits = next(q["digits"] for q in self.quantities if q["id"] == id)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return writer(value, digits)
        return str(value)

    def _build_captions(self, speech):
        self.captions = []
        for index, line in enumerate(self.lines):
            if speech:
                clauses = speech[index]["clauses"]
            else:
                total = max(len(line["text"]), 1)
                clauses = [
                    {
                        "text": line["text"][a:b],
                        "start": line["seconds"] * a / total,
                    }
                    for a, b in split_clauses(line["text"])
                ]
            for clause in clauses:
                # 字幕显示 1.5×10⁴ 这样的符号写法，配音仍然读“1.5乘10的4次方”
                self.captions.append({"t": line["start"] + clause["start"], "text": to_display(clause["text"])})
        self._caption_times = [caption["t"] for caption in self.captions]

    def _build_board(self):
        self.board_lines = []
        for phase in self.phases:
            index = self.frame_at(phase.end.seconds)
            for expr in phase.boards:
                self.board_lines.append(
                    {
                        "expr": expr,
                        "t": phase.begin,
                        "text": _SLOT.sub(lambda m: self._spoken_value(m.group(1), index, board_number), expr),
                    }
                )
        self._board_times = [line["t"] for line in self.board_lines]

    def caption_at(self, index):
        """这一帧的字幕，在第一句开始前是 None。"""
        position = bisect.bisect_right(self._caption_times, index / self.fps + _EPSILON) - 1
        return position if position >= 0 else None

    def board_count_at(self, index):
        """这一帧已经出现了几行板书。"""
        return bisect.bisect_right(self._board_times, index / self.fps + _EPSILON)

    def unique_frames(self):
        """找出画面真正不同的帧，返回每个不同画面的首帧和它要重复的次数。

        讲解时画面大多静止，只渲染变化的帧可以省下大部分时间。
        """
        columns = list(self._columns.values())
        begins = [phase.begin for phase in self.phases]
        firsts = []
        repeats = []
        previous = None
        for index in range(self.frame_count):
            f = self.frame(index)
            current = self.phases[max(bisect.bisect_right(begins, f.clock + _EPSILON) - 1, 0)]
            signature = (
                tuple(column[index] for column in columns),
                id(current),
                current.progress(f) if current.animated else None,
                self.caption_at(index),
                self.board_count_at(index),
            )
            if signature == previous:
                repeats[-1] += 1
            else:
                firsts.append(index)
                repeats.append(1)
                previous = signature
        return firsts, repeats

    def frame(self, index):
        return Frame(self._columns, self.constants, min(max(index, 0), self.frame_count - 1), self.fps)

    def frame_at(self, t):
        return min(max(round(t * self.fps), 0), self.frame_count - 1)

    def format_value(self, id, index):
        if id in self.constants:
            return str(self.constants[id])
        value = self._columns[id][index]
        if value is None:
            return "—"
        digits = next(q["digits"] for q in self.quantities if q["id"] == id)
        return f"{value:.{digits}f}"

    def answer_values(self):
        """题目所求的量和它们的数值，用来和独立解答核对。"""
        result = []
        for answer in self.answers:
            if answer["id"] in self.constants:
                value, unit = self.constants[answer["id"]], ""
            else:
                index = self.frame_count - 1 if answer["at"] is None else self.frame_at(answer["at"].seconds)
                value = self._columns[answer["id"]][index]
                unit = next(q["unit"] for q in self.quantities if q["id"] == answer["id"])
            result.append({"id": answer["id"], "label": answer["label"], "value": value, "unit": unit})
        return result

    def export(self, stage):
        """导出网页播放器读取的数据。"""
        return {
            "text": self.text,
            "assumptions": self.assumptions,
            "fps": self.fps,
            "duration": self.duration,
            "clock": {
                **self.clock,
                "unit": next(q["unit"] for q in self.quantities if q["id"] == self.clock["id"]),
            },
            "quantities": [{k: q[k] for k in ("id", "symbol", "name", "unit", "digits")} for q in self.quantities],
            "constants": self.constants,
            "formulas": [{"expr": line["expr"]} for line in self.board_lines],
            "phases": [{"label": p.label, "t0": p.begin, "t1": p.begin + p.seconds} for p in self.phases],
            "events": [{"t": event["moment"].seconds, "label": event["label"]} for event in self.events],
            "steps": [
                {"t": line["start"], "title": line["phase"].label, "text": to_display(line["text"])} for line in self.lines
            ],
            "answers": self.answer_values(),
            "frames": self._columns,
            "objects": stage.objects(),
            "regions": stage.regions(),
        }
