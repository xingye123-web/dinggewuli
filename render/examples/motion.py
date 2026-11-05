# 示例：匀速运动。火车过桥，距离要算上车长。路面按比例换算，车长和桥长都不失真
from physkit import *

TRAIN, BRIDGE, V = 200, 1000, 20
TOTAL = BRIDGE + TRAIN

timeline = Timeline(
    "一列长 200 m 的火车以 20 m/s 的速度匀速通过一座长 1000 m 的大桥。求：(1) 火车完全通过大桥经过的路程；(2) 火车完全通过大桥所用的时间。",
    ["匀速直线运动"],
)
intro = timeline.phase("审题")
cross = timeline.phase("火车过桥", min_seconds=8)
distance = timeline.phase("求路程")
time_used = timeline.phase("求时间")

timeline.quantity("s", "s", "火车通过的路程", "m", 1, lambda f: TOTAL * cross.progress(f))
timeline.quantity("v", "v", "火车速度", "m/s", 0, V)
timeline.quantity("t", "t", "题中时间", "s", 2, lambda f: f.s / f.v)
timeline.show_clock("t", "题中时间")

timeline.event(cross.start, "车头上桥")
timeline.event(cross.at(BRIDGE / TOTAL), "车头离桥")
timeline.event(cross.end, "车尾离桥")

intro.say("火车长200米，大桥长1000米，速度是每秒20米。")
cross.say("从车头上桥开始，一直到车尾离开大桥，才算完全通过。")
cross.say("所以这段路程不只是桥长，还要加上车长。这里最容易漏掉车长。")
distance.say("火车通过的路程等于桥长加车长，是{s}米。")
distance.board("s = s<sub>桥</sub> + s<sub>车</sub> = 1000 m + 200 m = {s} m")
time_used.say("时间等于路程除以速度，是{t}秒。")
time_used.board("t = s / v = {s} m ÷ {v} m/s = {t} s")

timeline.answer("s", "火车完全通过大桥经过的路程")
timeline.answer("t", "火车完全通过大桥所用的时间")

stage = Stage(timeline)

road = Road(-6.6, 0.4, -0.6, 1400, 200)
SHIFT = 200  # 路面从车头上桥前 200 米开始画
head = lambda f: road.x_at(SHIFT + f.s)
train_w = TRAIN * road.scale
bridge_left = road.x_at(SHIFT)
bridge_right = road.x_at(SHIFT + BRIDGE)

stage.add(
    road,
    Rod((bridge_left, -0.6), (bridge_left, -1.9), width=6),
    Rod((bridge_right, -0.6), (bridge_right, -1.9), width=6),
    Readout("大桥 1000 m", (bridge_left + bridge_right) / 2, -2.2, size=22),
    Cart(
        lambda f: head(f) - train_w / 2,
        -0.6,
        w=train_w,
        name="火车",
        show=["s", "v", "t"],
    ),
    Readout(lambda f: f"s = {f.s:.1f} m", -3.1, 1.6, size=28, color=OBJECT),
    Readout(lambda f: f"t = {f.t:.2f} s", -3.1, 1.0, size=28),
    Plot(
        (0, 60, 10), (0, 1200, 400), "t / s", "s / m",
        [Series(lambda f: f.t, lambda f: f.s, OBJECT)],
    ),
)
