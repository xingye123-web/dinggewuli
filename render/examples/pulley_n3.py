# 示例：滑轮组提升物体。物体运动的阶段给 min_seconds，讲解时画面不动的阶段不给
from physkit import *

G, H, T, F, N = 240, 2, 10, 100, 3

timeline = Timeline(
    "用滑轮组将重 240 N 的物体在 10 s 内匀速提升 2 m，绳子自由端的拉力为 100 N，动滑轮上有 3 段绳子。"
    "不计绳重和摩擦。求：(1) 有用功；(2) 拉力的功率；(3) 滑轮组的机械效率；(4) 动滑轮的重力。",
    ["匀速提升", "不计绳重和摩擦"],
)
intro = timeline.phase("审题")
lift = timeline.phase("匀速提升", min_seconds=6)
useful = timeline.phase("有用功")
total = timeline.phase("总功和功率")
efficiency = timeline.phase("机械效率")
wheel = timeline.phase("动滑轮重")

timeline.constant("n", N)
# 题目里的时间和距离都用 progress 换算，不受动画快慢影响
timeline.quantity("t", "t", "题中时间", "s", 2, lambda f: T * lift.progress(f))
timeline.quantity("h", "h", "物体上升高度", "m", 2, lambda f: H * lift.progress(f))
timeline.quantity("s", "s", "绳端移动距离", "m", 2, lambda f: N * f.h)
timeline.quantity("v_obj", "v<sub>物</sub>", "物体速度", "m/s", 2, lambda f: H / T if lift.active(f) else 0)
timeline.quantity("v_rope", "v<sub>绳</sub>", "绳端速度", "m/s", 2, lambda f: N * f.v_obj)
timeline.quantity("F", "F", "绳端拉力", "N", 0, F)
timeline.quantity("G", "G", "物重", "N", 0, G)
timeline.quantity("G_m", "G<sub>动</sub>", "动滑轮重", "N", 0, N * F - G)
timeline.quantity("W_use", "W<sub>有</sub>", "有用功（累计）", "J", 1, lambda f: f.G * f.h)
timeline.quantity("W_tot", "W<sub>总</sub>", "总功（累计）", "J", 1, lambda f: f.F * f.s)
timeline.quantity("W_ext", "W<sub>额</sub>", "额外功（累计）", "J", 1, lambda f: f.W_tot - f.W_use)
timeline.quantity("P", "P", "拉力功率", "W", 0, lambda f: f.F * f.v_rope)
timeline.quantity("P_avg", "P", "拉力的平均功率", "W", 0, lambda f: f.W_tot / f.t if f.t > 0 else None)
timeline.quantity("eta", "η", "机械效率", "%", 0, lambda f: f.W_use / f.W_tot * 100 if f.W_tot > 0 else None)
timeline.show_clock("t", "题中时间")

timeline.event(lift.start, "开始提升")
timeline.event(lift.at(0.5), "上升 1 m")
timeline.event(lift.end, "上升 2 m")

intro.say("这道题用滑轮组提升物体。物重240牛，10秒内匀速上升2米，拉力是100牛。")
intro.say("先看动滑轮，它上面有3段绳子。")
lift.say("物体上升时，这3段绳子一起缩短，所以绳端移动的距离是物体上升高度的3倍。")
lift.board("s = nh = {n} × {h} m = {s} m")
useful.say("有用功是克服物重做的功，等于{G}牛乘以{h}米，也就是{W_use}焦。")
useful.board("W<sub>有</sub> = Gh = {G} N × {h} m = {W_use} J")
total.say("总功是拉力做的功。注意距离要用绳端移动的{s}米，不能用{h}米，所以总功是{W_tot}焦。")
total.board("W<sub>总</sub> = Fs = {F} N × {s} m = {W_tot} J")
total.say("总功除以时间{t}秒，得到拉力的功率是{P_avg}瓦。")
total.board("P = W<sub>总</sub> / t = {W_tot} J ÷ {t} s = {P_avg} W")
efficiency.say("机械效率等于有用功除以总功，算出来是百分之{eta}。")
efficiency.board("η = W<sub>有</sub> / W<sub>总</sub> = {W_use} J ÷ {W_tot} J = {eta}%")
wheel.say("不计绳重和摩擦时，3段绳子的拉力之和等于物重加动滑轮重，所以动滑轮重{G_m}牛。")
wheel.board("G<sub>动</sub> = nF − G = {n} × {F} N − {G} N = {G_m} N")

timeline.answer("W_use", "有用功")
timeline.answer("P_avg", "拉力的功率")
timeline.answer("eta", "机械效率")
timeline.answer("G_m", "动滑轮的重力")

stage = Stage(timeline)

rig = PulleyRig(
    n=N,
    pull="up",
    height=lambda f: f.h,
    max_height=H,
    weight_text="G = 240 N",
    weight_show=["G", "h", "v_obj", "W_use"],
    moving_show=["G_m", "h", "W_ext"],
    fixed_show=["F", "eta"],
    end_show=["F", "s", "v_rope", "W_tot", "P"],
)

stage.add(
    *rig.parts,
    ForceArrow(rig.end_x, rig.end_y, 0.75, rig.pull, text=lambda f: f"F = {f.F:.0f} N"),
    # 标尺放在滑轮组的两边，读数和面板用相同的小数位数
    Ruler(
        rig.left_x - 0.6,
        rig.weight_start,
        lambda f: rig.weight_start + f.h * rig.meter,
        text=lambda f: f"h = {f.h:.2f} m",
        text_side="top",
    ),
    Ruler(rig.right_x + 1.0, rig.end_start, rig.end_y, text=lambda f: f"s = {f.s:.2f} m", color=ROPE),
    Readout(lambda f: f"t = {f.t:.2f} s", -0.6, 3.15, size=24),
    Plot(
        (0, 10, 2), (0, 6, 2), "t / s", "距离 / m",
        [
            Series(lambda f: f.t, lambda f: f.h, OBJECT),
            Series(lambda f: f.t, lambda f: f.s, ROPE),
        ],
    ),
)
