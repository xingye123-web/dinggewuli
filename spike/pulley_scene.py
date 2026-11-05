"""滑轮组场景。整段动画由一个 ValueTracker 驱动，每一帧只取决于时间线的帧号。"""

import json
import os
from pathlib import Path

import numpy as np
from manim import (
    Arc,
    Arrow,
    Axes,
    Circle,
    DashedLine,
    Dot,
    Line,
    Rectangle,
    Scene,
    Text,
    ValueTracker,
    VGroup,
    always_redraw,
    linear,
)

TL = json.loads((Path(__file__).parent / "timeline.json").read_text(encoding="utf-8"))
LAYOUT = TL["layout"]
FONT = "Microsoft YaHei"
BACKGROUND = "#10151C"
ROPE = "#E8C547"
OBJECT = "#5DA9E9"
STEEL = "#AEB8C4"
ACCENT = "#FF7A59"
INK = "#E6EBF0"


def label(text, size=24, color=INK):
    return Text(text, font=FONT, font_size=size, color=color)


class Pulley(Scene):
    def construct(self):
        self.camera.background_color = BACKGROUND
        # 每帧只取决于时间，所以可以切成几段分别渲染再拼接
        first_frame = int(os.environ.get("CLIP_FIRST_FRAME", 0))
        end_frame = int(os.environ.get("CLIP_END_FRAME", len(TL["frames"]["t"])))
        start_time = first_frame / TL["fps"]
        # Manim 用浮点步长数帧，时长恰好是整数帧时可能多出一帧。少算半帧，帧数才准确，每帧时间仍是帧号除以帧率
        run_time = (end_frame - first_frame - 0.5) / TL["fps"]
        clock = ValueTracker(start_time)
        last = len(TL["frames"]["t"]) - 1

        def q(name):
            index = min(int(round(clock.get_value() * TL["fps"])), last)
            return TL["frames"][name][index]

        R = LAYOUT["pulleyR"]
        fixed_x, fixed_y = LAYOUT["fixedX"], LAYOUT["fixedY"]
        moving_x = LAYOUT["movingX"]
        strand_a = fixed_x - R
        strand_b = fixed_x + R
        strand_c = LAYOUT["ropeEndX"]
        weight_x = LAYOUT["weightX"]
        ground_y = -3.6

        ceiling = Line([-6.4, 3.45, 0], [-2.6, 3.45, 0], color=STEEL, stroke_width=6)
        ground = Line([-6.8, ground_y, 0], [0.4, ground_y, 0], color=STEEL, stroke_width=4)
        bracket = Line([fixed_x, 3.45, 0], [fixed_x, fixed_y, 0], color=STEEL, stroke_width=4)

        def pulley(center, angle):
            wheel = Circle(radius=R, color=STEEL, stroke_width=4).move_to(center)
            axle = Dot(center, radius=0.05, color=STEEL)
            spoke_end = np.array(center) + R * np.array([np.cos(angle), np.sin(angle), 0])
            spoke = Line(center, spoke_end, color=STEEL, stroke_width=3)
            return VGroup(wheel, spoke, axle)

        fixed_pulley = always_redraw(
            lambda: pulley([fixed_x, fixed_y, 0], -q("h") * LAYOUT["meter"] / R)
        )
        moving_pulley = always_redraw(
            lambda: pulley([moving_x, q("ym"), 0], 2 * q("h") * LAYOUT["meter"] / R)
        )

        def rope():
            ym, yh = q("ym"), q("yh")
            attach = ym - 0.5
            return VGroup(
                Line([strand_a, attach, 0], [strand_a, fixed_y, 0]),
                Arc(radius=R, start_angle=np.pi, angle=-np.pi, arc_center=[fixed_x, fixed_y, 0]),
                Line([strand_b, fixed_y, 0], [strand_b, ym, 0]),
                Arc(radius=R, start_angle=np.pi, angle=np.pi, arc_center=[moving_x, ym, 0]),
                Line([strand_c, ym, 0], [strand_c, yh, 0]),
            ).set_stroke(ROPE, 4)

        def carrier():
            ym = q("ym")
            bar_y = ym - 0.5
            top = ym - 0.75
            return VGroup(
                Line([strand_a, bar_y, 0], [moving_x, bar_y, 0], color=STEEL, stroke_width=5),
                Line([moving_x, ym, 0], [moving_x, bar_y, 0], color=STEEL, stroke_width=4),
                Line([weight_x, bar_y, 0], [weight_x, top, 0], color=STEEL, stroke_width=4),
                Rectangle(
                    width=LAYOUT["weightW"],
                    height=LAYOUT["weightH"],
                    stroke_color=OBJECT,
                    fill_color=OBJECT,
                    fill_opacity=0.35,
                ).move_to([weight_x, top - LAYOUT["weightH"] / 2, 0]),
            )

        def pull_arrow():
            yh = q("yh")
            return Arrow(
                [strand_c, yh, 0],
                [strand_c, yh + 0.85, 0],
                buff=0,
                color=ACCENT,
                stroke_width=5,
                max_tip_length_to_length_ratio=0.3,
            )

        weight_text = always_redraw(
            lambda: label(f"G = {q('G'):.0f} N", 18).move_to(
                [weight_x, q("ym") - 0.75 - LAYOUT["weightH"] / 2, 0]
            )
        )
        pull_text = always_redraw(
            lambda: label(f"F = {q('F'):.0f} N", 22, ACCENT).next_to(
                [strand_c, q("yh") + 0.5, 0], buff=0.2, direction=[1, 0, 0]
            )
        )

        # 高度和绳端距离的标尺，读数烧录在视频里，用来核对网页面板是否同步
        h_x, s_x = -6.25, -2.4
        h_start = LAYOUT["ym0"] - 0.75 - LAYOUT["weightH"]
        h_line = always_redraw(
            lambda: Line(
                [h_x, h_start, 0],
                [h_x, h_start + q("h") * LAYOUT["meter"] + 0.001, 0],
                color=OBJECT,
                stroke_width=5,
            )
        )
        h_text = always_redraw(
            lambda: label(f"h = {q('h'):.2f} m", 20, OBJECT).next_to(
                [h_x, h_start + q("h") * LAYOUT["meter"], 0], direction=[0, 1, 0], buff=0.15
            )
        )
        s_line = always_redraw(
            lambda: Line(
                [s_x, LAYOUT["yh0"], 0],
                [s_x, q("yh") + 0.001, 0],
                color=ROPE,
                stroke_width=5,
            )
        )
        s_text = always_redraw(
            lambda: label(f"s = {q('s'):.2f} m", 24, ROPE).next_to(
                [s_x, q("yh"), 0], direction=[1, 0, 0], buff=0.15
            )
        )

        # 标出动滑轮上的 3 段绳子，这是 s = nh 的依据
        def strand_marks():
            ym, yh = q("ym"), q("yh")
            return VGroup(
                label("1", 20, ROPE).move_to([strand_a - 0.2, (ym - 0.5 + fixed_y) / 2, 0]),
                label("2", 20, ROPE).move_to([strand_b + 0.2, (ym + fixed_y) / 2, 0]),
                label("3", 20, ROPE).move_to([strand_c + 0.2, (ym + yh) / 2, 0]),
            )

        axes = Axes(
            x_range=[0, 10, 2],
            y_range=[0, 6, 1],
            x_length=5.0,
            y_length=4.4,
            tips=False,
            axis_config={"color": STEEL, "stroke_width": 2},
        ).move_to([4.1, -0.2, 0])
        ticks = VGroup()
        for value in range(0, 11, 2):
            ticks.add(label(str(value), 18, STEEL).next_to(axes.c2p(value, 0), [0, -1, 0], buff=0.14))
        for value in range(1, 7):
            ticks.add(label(str(value), 18, STEEL).next_to(axes.c2p(0, value), [-1, 0, 0], buff=0.14))
        axes_x = label("t / s", 20, STEEL).next_to(axes.c2p(10, 0), [0, -1, 0], buff=0.5)
        axes_y = label("距离 / m", 20, STEEL).next_to(axes.c2p(0, 6), [0, 1, 0], buff=0.2)
        full_h = DashedLine(axes.c2p(0, 0), axes.c2p(10, 2), color=OBJECT, stroke_opacity=0.3)
        full_s = DashedLine(axes.c2p(0, 0), axes.c2p(10, 6), color=ROPE, stroke_opacity=0.3)

        def curves():
            tau = q("tau") + 0.001
            h, s = q("h") + 0.001, q("s") + 0.001
            return VGroup(
                Line(axes.c2p(0, 0), axes.c2p(tau, h), color=OBJECT, stroke_width=5),
                Line(axes.c2p(0, 0), axes.c2p(tau, s), color=ROPE, stroke_width=5),
                Dot(axes.c2p(tau, h), radius=0.08, color=OBJECT),
                Dot(axes.c2p(tau, s), radius=0.08, color=ROPE),
            )

        time_text = always_redraw(
            lambda: label(f"t = {q('tau'):.2f} s", 34).move_to([4.1, 3.2, 0])
        )

        self.add(
            ground, ceiling, bracket, axes, ticks, axes_x, axes_y, full_h, full_s,
            always_redraw(carrier), fixed_pulley, moving_pulley, always_redraw(rope),
            always_redraw(strand_marks), always_redraw(pull_arrow), weight_text, pull_text,
            h_line, h_text, s_line, s_text, always_redraw(curves), time_text,
        )
        self.play(clock.animate.set_value(start_time + run_time), run_time=run_time, rate_func=linear)
