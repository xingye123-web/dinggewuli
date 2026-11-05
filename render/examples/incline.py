# 示例：斜面。物体沿斜面运动用 incline.block，沿斜面的力用 incline.angle 作方向
from physkit import *

G, L, H, F, T = 500, 5, 2, 250, 10

timeline = Timeline(
    "用沿斜面向上 250 N 的拉力，把重 500 N 的物体从斜面底端匀速拉到顶端，斜面长 5 m、高 2 m，用时 10 s。"
    "求：(1) 有用功；(2) 拉力的功率；(3) 斜面的机械效率；(4) 物体受到的摩擦力。",
    ["匀速拉动", "拉力沿斜面向上"],
)
intro = timeline.phase("审题")
pull = timeline.phase("沿斜面拉上去", min_seconds=6)
useful = timeline.phase("有用功")
total = timeline.phase("总功和功率")
efficiency = timeline.phase("机械效率")
friction = timeline.phase("摩擦力")

timeline.quantity("t", "t", "题中时间", "s", 2, lambda f: T * pull.progress(f))
timeline.quantity("s", "s", "沿斜面移动的距离", "m", 2, lambda f: L * pull.progress(f))
timeline.quantity("h", "h", "物体升高的高度", "m", 2, lambda f: f.s * H / L)
timeline.quantity("F", "F", "拉力", "N", 0, F)
timeline.quantity("G", "G", "物重", "N", 0, G)
timeline.quantity("W_use", "W<sub>有</sub>", "有用功（累计）", "J", 1, lambda f: f.G * f.h)
timeline.quantity("W_tot", "W<sub>总</sub>", "总功（累计）", "J", 1, lambda f: f.F * f.s)
timeline.quantity("W_ext", "W<sub>额</sub>", "额外功（累计）", "J", 1, lambda f: f.W_tot - f.W_use)
timeline.quantity("P_avg", "P", "拉力的平均功率", "W", 0, lambda f: f.W_tot / f.t if f.t > 0 else None)
timeline.quantity("eta", "η", "机械效率", "%", 0, lambda f: f.W_use / f.W_tot * 100 if f.W_tot > 0 else None)
timeline.quantity("f_fr", "f", "摩擦力", "N", 0, (F * L - G * H) / L)
timeline.show_clock("t", "题中时间")

timeline.event(pull.start, "从底端出发")
timeline.event(pull.end, "到达顶端")

intro.say("用250牛的拉力，沿斜面把500牛的物体从底端拉到顶端，斜面长5米，高2米。")
pull.say("物体沿斜面走了5米，但竖直方向只升高了2米。")
useful.say("有用功是把物体举高做的功，等于物重乘高度，是{W_use}焦。")
useful.board("W<sub>有</sub> = Gh = {G} N × {h} m = {W_use} J")
total.say("总功是拉力做的功，距离要用斜面长{s}米，总功是{W_tot}焦，功率是{P_avg}瓦。")
total.board("W<sub>总</sub> = Fs = {F} N × {s} m = {W_tot} J")
total.board("P = W<sub>总</sub> / t = {W_tot} J ÷ {t} s = {P_avg} W")
efficiency.say("机械效率等于有用功除以总功，是百分之{eta}。")
efficiency.board("η = W<sub>有</sub> / W<sub>总</sub> = {W_use} J ÷ {W_tot} J = {eta}%")
friction.say("额外功是克服摩擦做的功，除以斜面长，摩擦力是{f_fr}牛。")
friction.say("注意摩擦力不等于拉力，因为拉力还要把物体往高处拉。")
friction.board("f = W<sub>额</sub> / s = ({W_tot} J − {W_use} J) ÷ {s} m = {f_fr} N")

timeline.answer("W_use", "有用功")
timeline.answer("P_avg", "拉力的功率")
timeline.answer("eta", "斜面的机械效率")
timeline.answer("f_fr", "物体受到的摩擦力")

stage = Stage(timeline)

incline = Incline(L, H, x0=-6.0, y0=-2.6, width=5.4, length_text="L = 5 m", height_text="h = 2 m")
travel = lambda f: f.s
stage.add(
    Ground(-6.9, 0.5, -2.6),
    *incline.parts,
    incline.block(travel, w=1.0, h=0.6, text="500 N", name="物体", show=["G", "s", "h", "W_use"]),
    # 拉力从物块朝坡顶的那一面画出，摩擦力从朝坡脚的那一面画出
    ForceArrow(incline.block_x(travel, w=1.0, h=0.6, at="front"), incline.block_y(travel, w=1.0, h=0.6, at="front"),
               0.9, incline.angle, text="F", color=ACCENT),
    ForceArrow(incline.block_x(travel, w=1.0, h=0.6, at="back"), incline.block_y(travel, w=1.0, h=0.6, at="back"),
               lambda f: 0.5 if pull.active(f) else 0, incline.angle + 180, text="f", color=STEEL),
    Readout(lambda f: f"s = {f.s:.2f} m", -6.2, 3.3, size=22, anchor="left"),
    Readout(lambda f: f"h = {f.h:.2f} m", -6.2, 2.7, size=22, anchor="left"),
    Readout(lambda f: f"t = {f.t:.2f} s", -3.6, 3.3, size=22, anchor="left"),
    Plot(
        (0, 10, 2), (0, 1500, 500), "t / s", "功 / J",
        [
            Series(lambda f: f.t, lambda f: f.W_tot, ACCENT),
            Series(lambda f: f.t, lambda f: f.W_use, OBJECT),
        ],
    ),
)
