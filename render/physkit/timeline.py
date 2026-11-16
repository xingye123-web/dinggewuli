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
# 模型有时把数字本身写进花括号，比如 {400}，当成普通数字，不算引用物理量
_BRACED_NUMBER = re.compile(r"\{(\d+(?:\.\d+)?)\}")
# 054A 型、99A 坦克这类型号不是单位
_UNIT_AFTER_NUMBER = re.compile(r"\d\s*(?:N|J|W|kg|Pa|cm|mm|km|m|s|g|h|A|V|Ω)(?![A-Za-z型号级])")
_RESERVED = {"index", "clock"}
_EPSILON = 1e-9
MARK_KINDS = ("circle", "underline", "check")
READ_TAIL = 1.1  # 读完题后停一下，题目缩到右上角
ERASE_HOLD = 1.0  # 一问讲完，板书停一会儿再擦
ERASE_SECONDS = 0.9  # 板擦扫过去的时间
SWITCH_TAIL = 1.2  # 换小问：读完这一问后题目缩回去（放大和划线跟读这一问同时进行）
REVEAL_CHARS_PER_SECOND = 14  # 板书逐字写出的速度


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
        return self.phase.begin + self.phase.span * self.fraction


class Phase:
    """动画的一个阶段，由 timeline.phase() 创建。属性 start、end 是它的开始和结束时刻。"""

    def __init__(self, label, min_seconds, question=None, kind="lesson", tail=0.0):
        self.label = label
        self.min_seconds = min_seconds
        self.animated = min_seconds is not None
        self.question = question
        self.kind = kind  # lesson 是模型写的讲解；reading、erase、switch 是系统加的读题、擦板书、换小问
        self.tail = tail
        self.hold = 0.0  # 视频结尾多停的那一秒，不算进进度，最后一帧之前进度就到 1
        self.replays = []  # 后面让这个阶段再动一遍的阶段，见 timeline.replay
        self.replay_range = (0.0, 1.0)
        self.lines = []
        self.boards = []
        self.board_anchors = []
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
        self.lines.append({"raw": _BRACED_NUMBER.sub(r"\1", text), "phase": self})

    def board(self, expr):
        """加一行板书，显示在画面右上方，本阶段开始时出现。同一行也会出现在网页面板里，数值随帧变化。

        可以用 <sub> 写下标，比如 "W<sub>有</sub> = Gh = {G} N × {h} m = {W_use} J"。
        """
        self.boards.append(_BRACED_NUMBER.sub(r"\1", expr))
        # 这行板书跟着它前面那句旁白一起出现，边说边写；前面没有旁白时跟着本阶段第一句
        self.board_anchors.append(len(self.lines) - 1)

    @property
    def span(self):
        """动画实际进行的时长，不含结尾多停的时间。"""
        return self.seconds - self.hold

    def progress(self, f):
        """这一帧在本阶段的进度：开始前是 0，结束后是 1。只有声明了 min_seconds 的阶段才会连续变化。

        用 timeline.replay 让它再动一遍时，在重放的那段时间里进度会重新走一遍。
        """
        for replay in reversed(self.replays):
            if f.clock >= replay.begin - _EPSILON:
                low, high = replay.replay_range
                return low + (high - low) * replay._own_progress(f)
        return self._own_progress(f)

    def _own_progress(self, f):
        if not self.animated:
            return 1.0 if f.clock >= self.begin - _EPSILON else 0.0
        return min(max((f.clock - self.begin) / self.span, 0.0), 1.0)

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
        self.reading = []
        self.marks = []
        self.switches = []
        self.reading_window = None
        self.reading_shrinks = True
        self.question_count = 1
        self._windows = []
        self._inserted = False
        self._columns = None

    @property
    def duration(self):
        return self.phases[-1].begin + self.phases[-1].seconds if self.phases else 0

    @property
    def frame_count(self):
        return round(self.duration * self.fps)

    def phase(self, label, min_seconds=None, question=None):
        """按顺序追加一个阶段，返回 Phase。

        物体在运动的阶段必须给 min_seconds，表示动画至少持续多久。讲解时画面不动的阶段不要给。
        阶段的实际时长由旁白决定，旁白比 min_seconds 长时，动画会放慢。
        question 是这个阶段讲的是第几问（1、2、3…），不写就跟上一个阶段相同。题目只有一问时不用写。
        换到下一问时，系统会先停一下、用板擦擦掉上一问的板书，说「我们来看第二小问」，
        把题目放大、划出这一问再缩回去，然后才进入这个阶段。
        """
        if min_seconds is not None and min_seconds <= 0:
            raise SceneError(f"阶段「{label}」的 min_seconds 必须大于 0")
        if question is not None and (not isinstance(question, int) or not 1 <= question <= 9):
            raise SceneError(f"阶段「{label}」的 question 要写成 1 到 9 的整数，表示第几问")
        phase = Phase(label, min_seconds, question)
        self.phases.append(phase)
        return phase

    def replay(self, phase, label, min_seconds=None, question=None, start=0.0, end=1.0):
        """让前面某个运动阶段在这里再动一遍，返回新的阶段，用法和 timeline.phase 一样。

        比如第三问还要看提升的过程：again = timeline.replay(lift, "再看提升过程", question=3)。
        重放时所有用 lift.progress(f) 算出来的量会跟着重新变化，画面也会重新动。
        start、end 是只重放其中一段，比如 start=0.5 只重放后一半。重放结束后停在 end 那一刻的样子。
        """
        if not isinstance(phase, Phase) or not phase.animated:
            raise SceneError(f"replay 只能重放有 min_seconds 的运动阶段，收到的是 {getattr(phase, 'label', phase)!r}")
        if not 0 <= start < end <= 1:
            raise SceneError("replay 的 start、end 要满足 0 ≤ start < end ≤ 1")
        seconds = min_seconds or phase.min_seconds * (end - start)
        again = self.phase(label, max(seconds, 1.0), question)
        again.replay_range = (start, end)
        phase.replays.append(again)
        return again

    def read(self, text):
        """读题的旁白，开头把题目读一遍，写成口语：单位读中文。可以分几次调用。

        题目有好几问时只写题干，各小问由系统在讲到时再读。不写时系统会把题目原文自动改成口语来读。
        """
        from .lesson import split_sentences

        if "{" in text:
            raise SceneError("读题旁白里不要用 {物理量}，直接照题目读出数字")
        self.reading.extend(split_sentences(text, MAX_SPEECH_CHARS))

    def mark(self, phrase, kind="circle"):
        """读题时在题目上用笔标出重要条件：kind 是 circle（圈）、underline（下划线）或 check（打勾）。

        phrase 要和 Timeline 第一个参数里的原文一字不差（空格可以不同）。按在题目里出现的顺序写，
        读到那里时就画出来。圈已知量的数值和单位，比如 "250 N"；关键词用下划线，比如 "匀速"；
        不计摩擦、忽略绳重这类条件打勾。一道题标 3 到 6 处就够。
        """
        from .lesson import plain

        if kind not in MARK_KINDS:
            raise SceneError(f"mark 的 kind 只能是 circle、underline 或 check，收到的是 {kind!r}")
        if not plain(phrase) or plain(phrase) not in plain(self.text):
            raise SceneError(f"mark 的「{phrase}」在题目原文里找不到，要从 Timeline 的第一个参数里原样复制")
        self.marks.append({"phrase": phrase, "kind": kind, "t": 0.0})

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
        self._insert_system_phases()
        self.lines = [line for phase in self.phases for line in phase.lines]
        if not self.lines:
            raise SceneError("至少要有一句旁白，用 phase.say(...) 添加")
        if speech is not None and len(speech) != len(self.lines):
            raise SceneError(f"配音有 {len(speech)} 句，旁白有 {len(self.lines)} 句")

        for index, line in enumerate(self.lines):
            line["seconds"] = speech[index]["seconds"] if speech else len(line["raw"]) / CHARS_PER_SECOND
            line["clauses"] = speech[index]["clauses"] if speech else None
        self._layout()
        self._schedule()
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
            seconds = max(phase.min_seconds or 0.0, spoken) + phase.tail
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
        self.phases[-1].hold = TAIL_SECONDS

    def _answer_question(self, expr):
        """这行板书算出的是第几问的答案：看最后一个等号右边引用了哪个答案。"""
        answer_ids = [answer["id"] for answer in self.answers]
        slots = [match.group(1) for match in _SLOT.finditer(expr.rsplit("=", 1)[-1])]
        produced = next((id for id in reversed(slots) if id in answer_ids), None)
        return answer_ids.index(produced) + 1 if produced else None

    def _assign_questions(self, phases):
        """每个阶段属于第几问。模型写了 question 就按它的，没写就看板书算出的是第几问的答案推断。"""
        if any(phase.question for phase in phases):
            current = 1
            for phase in phases:
                current = phase.question or current
                phase.question = current
            return
        guesses = []
        for phase in phases:
            found = [q for q in (self._answer_question(expr) for expr in phase.boards) if q]
            guesses.append(min(found) if found else None)
        # 没有板书的阶段算到后面最近的那一问里（多半是在为它做铺垫），最后几个算到最后一问
        following = None
        for index in reversed(range(len(phases))):
            following = guesses[index] or following
            guesses[index] = following
        current = 1
        for phase, guess in zip(phases, guesses):
            current = max(current, guess or current)  # 不往回跳
            phase.question = current

    def _insert_system_phases(self):
        """在模型写的阶段前后加上读题、擦板书、换小问。compile 只调用一次。

        有好几问时，开头只读题干；讲到哪一问，再把这一问拿出来读。只有一问时开头整题读完。
        """
        if self._inserted:
            return
        self._inserted = True
        from .lesson import QUESTION_NAMES, spoken_problem, split_questions, split_sentences

        lessons = list(self.phases)
        self._assign_questions(lessons)
        self.question_count = max(phase.question for phase in lessons)
        stem, asked = split_questions(self.text)
        by_question = self.question_count > 1 and len(asked) >= 2

        # 有好几问时题目不缩小，直接接着拿出第一问来读
        reading = Phase("读题", None, question=None, kind="reading", tail=0.3 if by_question else READ_TAIL)
        for sentence in self.reading or split_sentences(spoken_problem(stem if by_question else self.text),
                                                        MAX_SPEECH_CHARS):
            reading.say(sentence)
        result = [reading]
        previous = None
        for phase in lessons:
            if phase.question != previous and (by_question or previous is not None):
                if previous is not None:
                    result.append(Phase(f"第{previous}问小结", ERASE_HOLD + ERASE_SECONDS, question=previous,
                                        kind="erase"))
                name = QUESTION_NAMES[phase.question - 1]
                switch = Phase(f"第{name}问", None, question=phase.question, kind="switch", tail=SWITCH_TAIL)
                opening = "先看第一小问" if phase.question == 1 else f"我们来看第{name}小问"
                body = spoken_problem(asked[phase.question]) if phase.question in asked else ""
                for sentence in split_sentences(f"{opening}：{body}。" if body else f"{opening}。", MAX_SPEECH_CHARS):
                    switch.say(sentence)
                result.append(switch)
            previous = phase.question
            result.append(phase)
        self.phases = result
        self.reading_shrinks = not by_question

    def _schedule(self):
        """排好读题时每个圈什么时候画、换小问的放大缩小、板书逐字写出和板擦的时刻。
        这些时间段里画面一直在变，unique_frames 要逐帧渲染。"""
        from .lesson import GROW_SECONDS, MARK_SECONDS, SHRINK_SECONDS, UNDERLINE_SECONDS, plain

        windows = []
        reading = self.phases[0]
        end = reading.begin + reading.seconds
        self.reading_window = (reading.begin, end)
        if self.reading_shrinks:
            windows.append((end - SHRINK_SECONDS, end))
        # 读到哪里画到哪里：把短语也改成口语，在读题和各小问的旁白里找到它，按配音的分句时间定下画的时刻
        spoken = [phase for phase in self.phases if phase.kind in ("reading", "switch")]
        cursor = (0, 0, 0)
        for mark in self.marks:
            found = self._spoken_position(spoken, mark["phrase"], cursor)
            if found is None:
                # 找不到时退回按题目里的位置估算
                flat = plain(self.text)
                share = (flat.find(plain(mark["phrase"])) + len(plain(mark["phrase"]))) / max(len(flat), 1)
                spoken_end = reading.lines[-1]["start"] + reading.lines[-1]["seconds"] if reading.lines else end
                moment, owner = reading.begin + (spoken_end - reading.begin) * share, reading
            else:
                moment, cursor, owner = found
            # 题目缩小之前要画完
            latest = owner.begin + owner.seconds - SHRINK_SECONDS - MARK_SECONDS
            mark["t"] = min(max(moment, owner.begin), latest)
            windows.append((mark["t"], mark["t"] + MARK_SECONDS))
        self.switches = []
        for index, phase in enumerate(self.phases):
            begin, finish = phase.begin, phase.begin + phase.seconds
            if phase.kind == "switch":
                # 紧接着读题的第一问，题目本来就是大的，不用再放大
                grow = self.phases[index - 1].kind != "reading"
                underline_at = (phase.lines[0]["start"] if phase.lines else begin) + (GROW_SECONDS if grow else 0) + 0.2
                self.switches.append({"question": phase.question, "t": begin, "t_end": finish,
                                      "t_underline": underline_at, "grow": grow})
                if grow:
                    windows.append((begin, begin + GROW_SECONDS))
                windows += [(underline_at, underline_at + UNDERLINE_SECONDS), (finish - SHRINK_SECONDS, finish)]
            elif phase.kind == "erase":
                windows.append((begin + ERASE_HOLD, finish))
        self._windows = windows

    @staticmethod
    def _spoken_position(phases, phrase, cursor):
        """短语在读题旁白里开始读到的时刻。返回 (秒, 下次从哪里接着找, 所在阶段)，找不到返回 None。"""
        from .lesson import plain, spoken_problem

        targets = [plain(spoken_problem(phrase)), plain(phrase)]
        for which in range(cursor[0], len(phases)):
            phase = phases[which]
            first_line = cursor[1] if which == cursor[0] else 0
            for number in range(first_line, len(phase.lines)):
                line = phase.lines[number]
                text = line["raw"]
                skip = cursor[2] if (which, number) == cursor[:2] else 0
                for target in targets:
                    position = text.find(target, skip) if target else -1
                    if position < 0:
                        continue
                    offset = Timeline._time_in_line(line, text, position + len(target) * 0.5)
                    return line["start"] + offset, (which, number, position + len(target)), phase
        return None

    @staticmethod
    def _time_in_line(line, text, position):
        """一句旁白里第 position 个字大约在第几秒读到。有配音的分句时间就用它，没有就按字数平分。"""
        clauses = line.get("clauses")
        if not clauses:
            return line["seconds"] * position / max(len(text), 1)
        consumed = 0
        for index, clause in enumerate(clauses):
            length = len(clause["text"])
            if position <= consumed + length or index == len(clauses) - 1:
                start = clause["start"]
                stop = clauses[index + 1]["start"] if index + 1 < len(clauses) else line["seconds"]
                return start + (stop - start) * min(max(position - consumed, 0) / max(length, 1), 1.0)
            consumed += length
        return line["seconds"]

    def phase_at(self, t):
        begins = [phase.begin for phase in self.phases]
        return self.phases[max(bisect.bisect_right(begins, t + _EPSILON) - 1, 0)]

    def question_at(self, t):
        """这一时刻在讲第几问。读题时是 None。"""
        return self.phase_at(t).question

    def overlay_key(self, index):
        """这一帧是否处在读题圈注、题目放大缩小、板书逐字写出、板擦擦除这些动画里。"""
        t = index / self.fps
        for start, stop in self._windows:
            if start - _EPSILON <= t <= stop + _EPSILON:
                return index
        return None

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
                raise SceneError(
                    f"{where}「{text}」里的 {{{slot}}} 没有对应的物理量或常数。"
                    f"已声明的有：{'、'.join(sorted(known))}。用其中一个，或者先用 timeline.quantity 声明它"
                )

    def _fill_text(self):
        for line in self.lines:
            index = self.frame_at(line["phase"].end.seconds)
            line["text"] = _SLOT.sub(lambda m: self._spoken_value(m.group(1), index, spoken_number), line["raw"])
            if line["phase"].kind != "lesson":
                continue  # 读题和换小问的话是系统写的，不拿模型的规矩去查
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
        """板书按阶段所属的问分组。同一阶段的几行依次逐字写出，写完一行再写下一行。"""
        self.board_lines = []
        for phase in self.phases:
            index = self.frame_at(phase.end.seconds)
            cursor = phase.begin + 0.1
            # 同一句旁白配了几行板书时，这句话的时长平分给它们
            shares = {}
            for anchor in phase.board_anchors:
                shares[max(anchor, 0)] = shares.get(max(anchor, 0), 0) + 1
            for expr, anchor in zip(phase.boards, phase.board_anchors):
                text = _SLOT.sub(lambda m: self._spoken_value(m.group(1), index, board_number), expr)
                visible = len(re.sub(r"</?su[bp]>|\s", "", text))
                reveal = min(max(visible / REVEAL_CHARS_PER_SECOND, 0.4), 1.6)
                if phase.lines:
                    line = phase.lines[max(anchor, 0)]
                    # 跟着这句旁白开始写，写的时间铺满这句话，声音和字一起出现、一起结束
                    reveal = min(max(line["seconds"] * 0.9 / shares[max(anchor, 0)], 0.5), 4.0)
                    cursor = max(cursor, line["start"])
                self.board_lines.append(
                    {
                        "expr": expr,
                        "t": cursor,
                        "reveal": reveal,
                        "t_end": phase.begin + phase.seconds,
                        "question": phase.question or 1,
                        "text": text,
                    }
                )
                self._windows.append((cursor, cursor + reveal))
                cursor += reveal + 0.15
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
                self.overlay_key(index),
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
            "formulas": [{k: line[k] for k in ("expr", "t", "t_end", "question")} for line in self.board_lines],
            "phases": [
                {"label": p.label, "t0": p.begin, "t1": p.begin + p.seconds, "kind": p.kind, "question": p.question}
                for p in self.phases
            ],
            "events": [{"t": event["moment"].seconds, "label": event["label"]} for event in self.events],
            "steps": [
                {"t": line["start"], "title": line["phase"].label, "text": to_display(line["text"])} for line in self.lines
            ],
            "answers": self.answer_values(),
            "frames": self._columns,
            "objects": stage.objects(),
            "regions": stage.regions(),
        }
