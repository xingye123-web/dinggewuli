# 示例：电热器高低挡。单刀双掷开关 S 接 1 时 R2 被短路，只有 R1 工作，是高温挡；接 2 时 R1、R2 串联，是低温挡。
# 开关跟着讲解拨到对应的挡位，先求高温挡的 R1，再求低温挡的总电阻和 R2，最后算低温挡工作 10 min 的电能
from physkit import *

U, P_HIGH, P_LOW, T_LOW = 220, 1100, 440, 600

timeline = Timeline(
    "某电热器有高、低两挡，电源电压 220 V。单刀双掷开关 S 接 1 时只有 R1 工作，为高温挡，功率 1100 W；"
    "S 接 2 时 R1 与 R2 串联，为低温挡，功率 440 W。求：(1) R1 的阻值；(2) R2 的阻值；(3) 低温挡工作 10 min 消耗的电能。",
    ["电源电压不变", "电阻不随温度变化"],
)
intro = timeline.phase("审题")
high = timeline.phase("高温挡求 R1")
low = timeline.phase("低温挡求 R2")
heat = timeline.phase("低温挡工作 10 min", min_seconds=6)
summary = timeline.phase("小结")

timeline.quantity("U", "U", "电源电压", "V", 0, U)
timeline.quantity("P_high", "P<sub>高</sub>", "高温挡功率", "W", 0, P_HIGH)
timeline.quantity("P_low", "P<sub>低</sub>", "低温挡功率", "W", 0, P_LOW)
timeline.quantity("R1", "R<sub>1</sub>", "R1 的阻值", "Ω", 0, lambda f: f.U ** 2 / f.P_high)
timeline.quantity("R_sum", "R<sub>串</sub>", "低温挡总电阻", "Ω", 0, lambda f: f.U ** 2 / f.P_low)
timeline.quantity("R2", "R<sub>2</sub>", "R2 的阻值", "Ω", 0, lambda f: f.R_sum - f.R1)
# 接 1 只有 R1，接 2 两个电阻串联；审题时先放在低温挡
timeline.quantity("gear", "S", "开关接的触点", "", 0, lambda f: 1 if high.active(f) else 2)
timeline.quantity(
    "I", "I", "电路中的电流", "A", 2, lambda f: f.U / (f.R1 if f.gear == 1 else f.R_sum)
)
timeline.quantity("t", "t", "低温挡工作时间", "s", 0, lambda f: T_LOW * heat.progress(f))
timeline.quantity("W", "W", "低温挡消耗的电能", "J", 0, lambda f: f.P_low * f.t)
timeline.show_clock("t", "低温挡工作")

timeline.event(high.start, "S 接 1：高温挡")
timeline.event(low.start, "S 接 2：低温挡")
timeline.event(heat.end, "工作 10 min")

intro.say("这是一道电热器挡位题，关键是看开关接到不同触点时，有几个电阻在工作。")
intro.say("电压一定时，接入的电阻越小，功率越大，就是高温挡。")
high.say("开关接1，电流从触点1直接过去，R2被短路，只有R1工作，电阻最小，是高温挡。")
high.say("由P等于U方除以R，R1等于{U}伏的平方除以{P_high}瓦，是{R1}欧。")
high.board("R<sub>1</sub> = U² / P<sub>高</sub> = ({U} V)² ÷ {P_high} W = {R1} Ω")
low.say("开关接2，R1和R2串联，总电阻变大，功率变小，是低温挡。")
low.say("先求串联的总电阻，是{R_sum}欧，再减去R1，得到R2是{R2}欧。")
low.board("R<sub>串</sub> = U² / P<sub>低</sub> = ({U} V)² ÷ {P_low} W = {R_sum} Ω")
low.board("R<sub>2</sub> = R<sub>串</sub> − R<sub>1</sub> = {R_sum} Ω − {R1} Ω = {R2} Ω")
heat.say("低温挡工作10分钟，时间要换成{t}秒，电能等于功率乘时间，是{W}焦。")
heat.board("W = P<sub>低</sub>t = {P_low} W × {t} s = {W} J")
summary.say("易错的地方是分不清挡位：不能看开关接哪边，要看接入电路的总电阻是大还是小。")

timeline.answer("R1", "R1 的阻值")
timeline.answer("R2", "R2 的阻值")
timeline.answer("W", "低温挡工作 10 min 消耗的电能")

stage = Stage(timeline)

LEFT, NODE, TOP, BOTTOM = -6.0, -1.0, 1.9, -1.9
PIVOT = (-4.6, TOP)
CONTACT_1, CONTACT_2 = (-3.8, 2.5), (-3.8, 1.3)

stage.add(
    # 电源正极到开关转轴，再从 R1 经电流表回到电源
    Wire([PIVOT, (LEFT, TOP), (LEFT, BOTTOM), (NODE, BOTTOM), (NODE, CONTACT_2[1])]),
    # 触点 1 直接连到右边的节点，把 R2 短路
    Wire([CONTACT_1, (NODE, CONTACT_1[1]), (NODE, CONTACT_2[1])]),
    # 触点 2 经过 R2 连到同一个节点
    Wire([CONTACT_2, (NODE, CONTACT_2[1])]),
    Battery(LEFT, 0, horizontal=False, text=lambda f: f"{f.U:.0f} V", text_side="left", name="电源", show=["U"]),
    DoubleThrowSwitch(PIVOT, [CONTACT_1, CONTACT_2], to=lambda f: f.gear, text="S", text_side="bottom",
                      name="开关 S", show=["gear", "I"]),
    Resistor(-2.4, CONTACT_2[1], text="R<sub>2</sub>", text_side="bottom", name="R2", show=["R2", "R_sum"]),
    Resistor(NODE, -0.3, horizontal=False, text="R<sub>1</sub>", text_side="left", name="R1", show=["R1"]),
    Meter(-3.5, BOTTOM, "A", text=lambda f: f"I = {f.I:.2f} A", text_side="top", name="电流表", show=["I"]),
    Readout(lambda f: "高温挡" if f.gear == 1 else "低温挡", -3.5, 0.2, size=30, color=ACCENT),
    Readout(lambda f: f"W = {sci(f.W, 2)} J" if f.W else "W = 0 J", -3.5, -0.6, size=24, color=OBJECT),
    Plot(
        (0, 600, 150), (0, 300000, 100000), "t / s", "W / J",
        [Series(lambda f: f.t, lambda f: f.W, OBJECT)],
    ),
)
