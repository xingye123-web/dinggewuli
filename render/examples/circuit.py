# 示例：动态电路。过程由滑片位置驱动，先画完整的导线回路，再把元件放在导线上
from physkit import *

U, R1, R2_MAX = 6, 10, 20

timeline = Timeline(
    "定值电阻 R1 = 10 Ω 与最大阻值为 20 Ω 的滑动变阻器串联，接在 6 V 的电源上，电流表测电路中的电流。"
    "滑片从阻值最小端移到最大端。求：(1) 滑动变阻器接入 20 Ω 时电路中的电流；(2) 此时 R1 两端的电压；(3) 此时 R1 的电功率。",
    ["电源电压不变"],
)
intro = timeline.phase("审题")
slide = timeline.phase("移动滑片", min_seconds=6)
current = timeline.phase("求电流")
voltage = timeline.phase("求电压")
power = timeline.phase("求电功率")

timeline.quantity("R2", "R<sub>2</sub>", "变阻器接入的电阻", "Ω", 2, lambda f: R2_MAX * slide.progress(f))
timeline.quantity("U", "U", "电源电压", "V", 0, U)
timeline.quantity("R1", "R<sub>1</sub>", "定值电阻", "Ω", 0, R1)
timeline.quantity("R_sum", "R", "总电阻", "Ω", 2, lambda f: f.R1 + f.R2)
timeline.quantity("I", "I", "电路中的电流", "A", 2, lambda f: f.U / f.R_sum)
timeline.quantity("U1", "U<sub>1</sub>", "R1 两端的电压", "V", 2, lambda f: f.I * f.R1)
timeline.quantity("P1", "P<sub>1</sub>", "R1 的电功率", "W", 2, lambda f: f.U1 * f.I)
timeline.show_clock("R2", "变阻器接入")

timeline.event(slide.start, "滑片在最小端")
timeline.event(slide.end, "滑片在最大端")

intro.say("电阻和滑动变阻器串联，接在{U}伏的电源上。滑片移动时，接入的电阻会变化。")
slide.say("滑片向右移动，接入电路的电阻变大，总电阻变大，所以电流变小。")
current.say("串联电路的总电阻等于各电阻之和，是{R_sum}欧。")
current.board("R = R<sub>1</sub> + R<sub>2</sub> = {R1} Ω + {R2} Ω = {R_sum} Ω")
current.say("根据欧姆定律，电流等于电压除以总电阻，是{I}安。")
current.board("I = U / R = {U} V ÷ {R_sum} Ω = {I} A")
voltage.say("R1两端的电压等于电流乘以R1的电阻，是{U1}伏。注意不能直接用电源电压。")
voltage.board("U<sub>1</sub> = IR<sub>1</sub> = {I} A × {R1} Ω = {U1} V")
power.say("R1的电功率等于它两端的电压乘以电流，是{P1}瓦。")
power.board("P<sub>1</sub> = U<sub>1</sub>I = {U1} V × {I} A = {P1} W")

timeline.answer("I", "电路中的电流")
timeline.answer("U1", "R1 两端的电压")
timeline.answer("P1", "R1 的电功率")

stage = Stage(timeline)

LEFT, RIGHT, TOP, BOTTOM = -5.6, -0.8, 1.9, -1.9

stage.add(
    Wire([(LEFT, TOP), (RIGHT, TOP), (RIGHT, BOTTOM), (LEFT, BOTTOM), (LEFT, TOP)]),
    Battery(LEFT, 0, horizontal=False, text=lambda f: f"{f.U:.0f} V", text_side="left", name="电源", show=["U", "I"]),
    Meter(-4.3, TOP, "A", text=lambda f: f"{f.I:.2f} A", name="电流表", show=["I", "R_sum"]),
    Resistor(-2.3, TOP, text=lambda f: f"R1 = {f.R1:.0f} Ω", name="R1", show=["R1", "U1", "P1", "I"]),
    Rheostat(
        -3.2,
        BOTTOM,
        lambda f: f.R2 / R2_MAX,
        text=lambda f: f"R2 = {f.R2:.2f} Ω",
        name="滑动变阻器",
        show=["R2", "R_sum", "I"],
    ),
    Readout(lambda f: f"U1 = {f.U1:.2f} V", -3.2, 0.3, size=24, color=OBJECT),
    Readout(lambda f: f"I = {f.I:.2f} A", -3.2, -0.3, size=24, color=ROPE),
    Plot(
        (0, 20, 5), (0, 0.6, 0.2), "R2 / Ω", "I / A",
        [Series(lambda f: f.R2, lambda f: f.I, ROPE)],
    ),
)
