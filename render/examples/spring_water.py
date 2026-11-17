# 示例：弹簧连着物块，向容器里注水。过程由“水深”驱动，用到 Spring、Beaker、浮力和弹簧弹力的方向变化
from physkit import *

A_CM, G, L0_CM, K = 10, 6, 10, 1  # 正方体边长 cm、重 N、弹簧原长 cm、每 1 N 长度改变 1 cm
RHO_WATER, g = 1000, 10
CM = 0.15  # 画面上 1 cm 的长度
FLOOR = -3.0
X0 = -3.6

timeline = Timeline(
    "如图，容器底部固定一根轻质弹簧，弹簧原长 10 cm，上端连着一个边长 10 cm、重 6 N 的正方体木块，"
    "弹簧每受到 1 N 的力，长度改变 1 cm。向容器中缓慢加水，直到木块刚好完全浸没，g 取 10 N/kg。"
    "求：(1) 弹簧恰好为原长时水的深度；(2) 木块完全浸没时受到的浮力；(3) 此时弹簧对木块的拉力；(4) 此时水对容器底的压强。",
    ["缓慢加水", "刚好完全浸没", "轻质弹簧"],
)

timeline.mark("10 cm")
timeline.mark("6 N")
timeline.mark("1 N")
timeline.mark("缓慢加水", "underline")
timeline.mark("刚好完全浸没", "underline")
timeline.mark("轻质弹簧", "check")

intro = timeline.phase("分析初始状态", question=1)
dry = timeline.phase("加水到木块底部", min_seconds=3, question=1)
rise = timeline.phase("木块浸入，弹簧变回原长", min_seconds=6, question=1)
natural = timeline.phase("求原长时水深", question=1)
stretch = timeline.phase("继续加水到完全浸没", min_seconds=5, question=2)
buoyancy = timeline.phase("求浮力", question=2)
pull = timeline.phase("求拉力", question=3)
pressure = timeline.phase("求压强", question=4)

# 弹簧长 L = 4 cm + d，水深 H = L + d，所以 d = (H − 4 cm) / 2（d 是木块浸入的深度）
timeline.quantity("H", "h", "水深", "cm", 1, lambda f: 4 * dry.progress(f) + 12 * rise.progress(f) + 8 * stretch.progress(f))
timeline.quantity("d", "d", "木块浸入深度", "cm", 1, lambda f: min(max((f.H - 4) / 2, 0), A_CM))
timeline.quantity("V_pai", "V<sub>排</sub>", "排开水的体积", "cm³", 0, lambda f: A_CM * A_CM * f.d)
timeline.quantity("V_si", "V<sub>排</sub>", "排开水的体积（换算成 m³）", "m³", 6, lambda f: f.V_pai * 1e-6)
timeline.quantity("F_fu", "F<sub>浮</sub>", "浮力", "N", 2, lambda f: RHO_WATER * g * f.V_si)
timeline.quantity("G", "G", "木块重", "N", 0, G)
# 正值：弹簧被压缩，向上推木块；负值：弹簧被拉长，向下拉木块
timeline.quantity("F_tan", "F<sub>弹</sub>", "弹簧对木块的力（向上为正）", "N", 2, lambda f: f.G - f.F_fu)
timeline.quantity("L", "L", "弹簧长度", "cm", 1, lambda f: L0_CM - f.F_tan / K)
timeline.quantity("H_si", "h", "水深（换算成 m）", "m", 2, lambda f: f.H * 0.01)
timeline.quantity("p", "p", "水对容器底的压强", "Pa", 0, lambda f: RHO_WATER * g * f.H_si)
timeline.show_clock("H", "水深")

timeline.event(rise.start, "水面到达木块底部")
timeline.event(rise.end, "弹簧恢复原长")
timeline.event(stretch.end, "木块刚好完全浸没")

intro.say("没加水时，木块压着弹簧，弹簧被压缩了6厘米，长4厘米。")
dry.say("水面还没碰到木块，没有浮力，弹簧长度不变。")
rise.say("木块浸入水中，浮力变大，弹簧对木块向上的推力变小，弹簧慢慢变长。")
rise.say("浮力等于重力6牛时，弹簧不受力，恢复原长10厘米。")
natural.say("这时木块浸入6厘米，水深等于弹簧原长加浸入深度，{H}厘米。")
natural.board("F<sub>浮</sub> = G：ρ<sub>水</sub>g·(0.1 m)²·d = 6 N，d = 6 cm")
natural.board("h = L<sub>0</sub> + d = 10 cm + 6 cm = {H} cm")
stretch.say("继续加水，浮力大于重力，弹簧被拉长，木块跟着上升。")
buoyancy.say("刚好完全浸没时，排开水的体积是1000立方厘米，换算成1乘10的负3次方立方米，浮力是{F_fu}牛。")
buoyancy.board("F<sub>浮</sub> = ρ<sub>水</sub>gV<sub>排</sub> = 1000 kg/m³ × 10 N/kg × {V_si} m³ = {F_fu} N")
pull.say("木块受浮力向上，重力和弹簧拉力向下，拉力等于浮力减重力，4牛，弹簧伸长了4厘米。")
pull.board("F<sub>拉</sub> = F<sub>浮</sub> − G = {F_fu} N − {G} N = 4 N")
pressure.say("这时弹簧长14厘米，加上木块10厘米，水深0.24米，水对容器底的压强是{p}帕。")
pressure.board("p = ρ<sub>水</sub>gh = 1000 kg/m³ × 10 N/kg × {H_si} m = {p} Pa")

timeline.answer("H", "弹簧恰好为原长时水的深度", at=rise.end)
timeline.answer("F_fu", "木块完全浸没时受到的浮力", at=stretch.end)
timeline.quantity("F_la", "F<sub>拉</sub>", "弹簧对木块的拉力", "N", 2, lambda f: max(-f.F_tan, 0))
timeline.answer("F_la", "完全浸没时弹簧对木块的拉力", at=stretch.end)
timeline.answer("p", "完全浸没时水对容器底的压强", at=stretch.end)

stage = Stage(timeline)

FORCE = 0.12
SIDE = A_CM * CM
cube_bottom = lambda f: FLOOR + f.L * CM
cube_y = lambda f: cube_bottom(f) + SIDE / 2
cube = Block(X0, cube_y, SIDE, SIDE, "木块", color=OBJECT, name="木块", show=["G", "F_fu", "F_tan", "V_pai"])
spring_state = lambda f: (
    "弹簧原长" if abs(f.L - L0_CM) < 0.05
    else f"压缩 {L0_CM - f.L:.1f} cm" if f.L < L0_CM
    else f"伸长 {f.L - L0_CM:.1f} cm"
)

stage.add(
    Spring((X0, FLOOR), (X0, cube.bottom), coils=6, width=0.4, name="弹簧", show=["L", "F_tan"]),
    cube,
    Beaker(X0, FLOOR, 4.2, 31 * CM, lambda f: FLOOR + f.H * CM, name="水", show=["H", "p"]),
    Ground(-6.4, -0.8, FLOOR),
    ForceArrow(X0 - 0.45, cube_y, lambda f: f.F_fu * FORCE, "up", color=OBJECT),
    ForceArrow(X0 + 0.45, cube_y, lambda f: f.G * FORCE, "down", color=ACCENT),
    # 读数放在容器右边一列，不压容器壁
    Readout(lambda f: f"水深 {f.H:.1f} cm", -1.15, 1.2, size=22, anchor="left"),
    Readout(lambda f: f"F浮 = {f.F_fu:.2f} N", -1.15, 0.7, size=20, color=OBJECT, anchor="left"),
    Readout(lambda f: f"G = {f.G:.0f} N", -1.15, 0.3, size=20, color=ACCENT, anchor="left"),
    Readout(spring_state, -1.15, -0.1, size=20, anchor="left"),
    Plot(
        (0, 25, 5), (0, 12, 4), "h / cm", "力 / N",
        [
            Series(lambda f: f.H, lambda f: f.F_fu, OBJECT),
            Series(lambda f: f.H, lambda f: f.G, ACCENT),
        ],
    ),
)
