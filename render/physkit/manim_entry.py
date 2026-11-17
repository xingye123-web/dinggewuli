"""Manim 渲染入口。

只渲染画面真正不同的帧，由一个 ValueTracker 按序号驱动。每一帧只取决于帧号，所以可以分段并行渲染。
"""

import os

from manim import Scene, ValueTracker, linear

from physkit.loader import load_scene

timeline, stage = load_scene(os.environ["PHYSKIT_SCENE"], os.environ.get("PHYSKIT_SPEECH"))
firsts, _ = timeline.unique_frames()


def _redraw(part, current):
    """和 always_redraw 一样每帧重画，但零件报告画面没变（_redraw_key 和上一帧相同）时跳过。"""
    frame = current()
    mobject = part.draw(frame)
    last = [part._redraw_key(frame)]

    def update(target):
        frame = current()
        key = part._redraw_key(frame)
        if key is not None and key == last[0]:
            return
        target.become(part.draw(frame))
        last[0] = key

    mobject.add_updater(update)
    return mobject


class Problem(Scene):
    def construct(self):
        self.camera.background_color = stage.background
        first = int(os.environ.get("CLIP_FIRST_FRAME", 0))
        end = int(os.environ.get("CLIP_END_FRAME", len(firsts)))
        # Manim 用浮点步长数帧，时长恰好是整数帧时可能多出一帧。少算半帧，帧数才准确
        run_time = (end - first - 0.5) / timeline.fps
        position = ValueTracker(first)

        def current():
            return timeline.frame(firsts[min(int(round(position.get_value())), len(firsts) - 1)])

        for part in stage.all_parts:
            backdrop = part.backdrop()
            if backdrop is not None:
                self.add(backdrop)
            if part.static:
                self.add(part.draw(None))
            else:
                self.add(_redraw(part, current))

        self.play(
            position.animate.set_value(first + run_time * timeline.fps),
            run_time=run_time,
            rate_func=linear,
        )
