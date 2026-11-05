# 示例：不按时间推进的题。过程由“下降距离”驱动，用到弹簧测力计和容器
from physkit import *

G, AREA_CM2, HEIGHT_CM, GAP_CM, EXTRA_CM = 12, 40, 20, 10, 5
RHO_WATER, g = 1000, 10
CM = 0.05
WATER_Y = -0.5

timeline = Timeline(
    "弹簧测力计下挂一个重 12 N 的圆柱体，底面积 40 cm²，高 20 cm。让它从下表面距水面 10 cm 处缓慢匀速下降，"
    "完全浸没后再下降 5 cm。水足够深，水面高度变化忽略不计，g 取 10 N/kg。"
    "求：(1) 圆柱体受到的最大浮力；(2) 完全浸没时测力计的示数；(3) 圆柱体的密度；(4) 刚好完全浸没时下表面受到水的压强。",
    ["缓慢匀速下降", "水面高度变化忽略不计", "g = 10 N/kg"],
)
intro = timeline.phase("审题")
above = timeline.phase("未接触水面", min_seconds=2)
entering = timeline.phase("逐渐浸入", min_seconds=6)
pressure = timeline.phase("求压强和密度")
under = timeline.phase("完全浸没后", min_seconds=2)

timeline.quantity(
    "x", "x", "下降距离", "cm", 1,
    lambda f: GAP_CM * above.progress(f) + HEIGHT_CM * entering.progress(f) + EXTRA_CM * under.progress(f),
)
timeline.quantity("d", "d", "下表面在水下的深度", "cm", 1, lambda f: max(f.x - GAP_CM, 0))
timeline.quantity("V_pai", "V<sub>排</sub>", "排开水的体积", "cm³", 0, lambda f: AREA_CM2 * min(f.d, HEIGHT_CM))
# 题目给的是 cm 和 cm³，代入公式前要换算成国际单位
timeline.quantity("V_si", "V<sub>排</sub>", "排开水的体积（换算成 m³）", "m³", 6, lambda f: f.V_pai * 1e-6)
timeline.quantity("d_si", "d", "下表面深度（换算成 m）", "m", 3, lambda f: f.d * 0.01)
timeline.quantity("F_fu", "F<sub>浮</sub>", "浮力", "N", 2, lambda f: RHO_WATER * g * f.V_si)
timeline.quantity("G", "G", "圆柱体重", "N", 0, G)
timeline.quantity("F", "F", "测力计示数", "N", 2, lambda f: f.G - f.F_fu)
timeline.quantity("p", "p", "下表面受到水的压强", "Pa", 0, lambda f: RHO_WATER * g * f.d_si)
timeline.quantity("rho", "ρ<sub>物</sub>", "圆柱体密度", "kg/m³", 0, G / g / (AREA_CM2 * HEIGHT_CM * 1e-6))
timeline.show_clock("x", "下降距离")

timeline.event(entering.start, "刚接触水面")
timeline.event(entering.end, "刚好完全浸没")
timeline.event(under.end, "再下降 5 厘米")

intro.say("弹簧测力计挂着一个重12牛的圆柱体，它慢慢下降，我们来看示数怎样变化。")
above.say("还没接触水面时，没有浮力，示数等于重力，12牛。")
entering.say("进入水中后，排开的水越来越多，浮力变大，示数变小。")
entering.say("刚好完全浸没时，排开水的体积是800立方厘米，换算成8乘10的负4次方立方米，浮力达到最大，{F_fu}牛。")
entering.board("F<sub>浮</sub> = ρ<sub>水</sub>gV<sub>排</sub> = 1000 kg/m³ × 10 N/kg × {V_si} m³ = {F_fu} N")
entering.say("这时测力计的示数等于重力减去浮力，{F}牛。")
entering.board("F = G − F<sub>浮</sub> = {G} N − {F_fu} N = {F} N")
pressure.say("此时下表面的深度是0.2米，所以受到水的压强是{p}帕。")
pressure.board("p = ρ<sub>水</sub>gd = 1000 kg/m³ × 10 N/kg × {d_si} m = {p} Pa")
pressure.say("圆柱体质量是1.2千克，体积是8乘10的负4次方立方米，所以密度是{rho}千克每立方米。")
pressure.board("ρ<sub>物</sub> = m / V = 1.2 kg ÷ 8×10<sup>-4</sup> m³ = {rho} kg/m³")
under.say("继续下降，排开水的体积不变，所以浮力和示数都不再变化，这是容易出错的地方。")

timeline.answer("F_fu", "最大浮力", at=entering.end)
timeline.answer("F", "完全浸没时测力计的示数", at=entering.end)
timeline.answer("rho", "圆柱体的密度")
timeline.answer("p", "刚好完全浸没时下表面受到水的压强", at=entering.end)

stage = Stage(timeline)

X0 = -3.6
WIDTH = 1.0
BLOCK_H = HEIGHT_CM * CM
FORCE = 0.1
block_y = lambda f: WATER_Y + (GAP_CM - f.x) * CM + BLOCK_H / 2
block_top = lambda f: block_y(f) + BLOCK_H / 2
scale_top = lambda f: block_top(f) + 0.1 + SpringScale.HOOK + SpringScale.HEIGHT
cylinder = Block(X0, block_y, WIDTH, BLOCK_H, name="圆柱体", show=["G", "F_fu", "V_pai", "rho", "p"])
scale = SpringScale(X0, scale_top, lambda f: f.F, 15, name="测力计", show=["F", "G", "F_fu"])

stage.add(
    Ceiling(-6.0, -1.2, 3.6),
    Rod((X0, 3.6), (X0, scale_top)),
    scale,
    Rod((X0, scale.hook_y), (X0, cylinder.top)),
    cylinder,
    Beaker(X0, -3.0, 3.4, 3.1, WATER_Y, name="水", show=["V_pai", "d", "p"]),
    Ground(-6.4, -0.8, -3.0),
    ForceArrow(X0 - 0.3, block_y, lambda f: f.F_fu * FORCE, "up", color=OBJECT),
    ForceArrow(X0 + 0.3, block_y, lambda f: f.G * FORCE, "down", color=ACCENT),
    Readout(lambda f: f"F浮 = {f.F_fu:.2f} N", -6.2, lambda f: block_y(f) + 0.3, size=20, color=OBJECT),
    Readout(lambda f: f"G = {f.G:.0f} N", -0.95, lambda f: block_y(f) - 0.5, size=20, color=ACCENT),
    Readout(lambda f: f"F = {f.F:.2f} N", -1.9, lambda f: scale_top(f) - 0.8, size=22),
    Readout(lambda f: f"下降 {f.x:.1f} cm", -5.8, 3.05, size=24),
    Plot(
        (0, 35, 5), (0, 12, 4), "x / cm", "力 / N",
        [
            Series(lambda f: f.x, lambda f: f.F, ACCENT),
            Series(lambda f: f.x, lambda f: f.F_fu, OBJECT),
        ],
    ),
)
