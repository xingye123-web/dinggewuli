# 示例：杠杆。先求平衡时的动力，再让杠杆转动，演示竖直方向的力的力臂随转动变短、比值不变
from physkit import *
import math

G, OA, OB, H = 30, 0.2, 0.6, 0.1

timeline = Timeline(
    "轻质杠杆 AB 可绕支点 O 转动，OA = 0.2 m，OB = 0.6 m。A 端挂一个重 30 N 的物体，在 B 端竖直向下用力，"
    "使杠杆在水平位置平衡。求：(1) 所需的动力；(2) 用这个杠杆把物体匀速提升 0.1 m，B 端下降的距离；(3) 动力做的功。",
    ["轻质杠杆，不计杠杆自重", "动力始终竖直向下"],
)
intro = timeline.phase("审题")
balance = timeline.phase("杠杆平衡")
lift = timeline.phase("提升物体", min_seconds=6)
distance = timeline.phase("B 端下降的距离")
work = timeline.phase("动力做的功")

timeline.quantity("h", "h", "物体上升高度", "m", 3, lambda f: H * lift.progress(f))
timeline.quantity("theta", "θ", "杠杆转过的角度", "°", 1, lambda f: math.degrees(math.asin(f.h / OA)))
timeline.quantity("G", "G", "物重", "N", 0, G)
timeline.quantity("L2", "L<sub>2</sub>", "阻力臂", "m", 3, lambda f: OA * math.cos(math.radians(f.theta)))
timeline.quantity("L1", "L<sub>1</sub>", "动力臂", "m", 3, lambda f: OB * math.cos(math.radians(f.theta)))
timeline.quantity("F1", "F<sub>1</sub>", "动力", "N", 0, lambda f: f.G * f.L2 / f.L1)
timeline.quantity("s", "s", "B 端下降距离", "m", 3, lambda f: OB * math.sin(math.radians(f.theta)))
timeline.quantity("W1", "W", "动力做的功（累计）", "J", 2, lambda f: f.F1 * f.s)
timeline.quantity("W2", "W<sub>有</sub>", "克服物重做的功（累计）", "J", 2, lambda f: f.G * f.h)
timeline.show_clock("h", "物体上升高度")

timeline.event(lift.start, "开始提升")
timeline.event(lift.end, "上升 0.1 m")

intro.say("杠杆绕支点O转动，A端挂30牛的物体，B端用竖直向下的力把它撬起来。")
balance.say("力臂是支点到力的作用线的距离，两个力都竖直，力臂就是水平距离。")
balance.say("杠杆平衡时，动力乘动力臂等于阻力乘阻力臂，所以动力是{F1}牛。")
balance.board("F<sub>1</sub> = GL<sub>2</sub> / L<sub>1</sub> = {G} N × 0.2 m ÷ 0.6 m = {F1} N")
lift.say("杠杆转动后，两个力臂都变短了，但它们的比值始终是1比3，所以动力一直是{F1}牛。")
distance.say("B端到支点的距离是A端的3倍，所以B端下降的距离也是物体上升高度的3倍，是{s}米。")
distance.board("s = 3h = 3 × {h} m = {s} m")
work.say("动力做的功等于动力乘B端下降的距离，是{W1}焦，正好等于克服物重做的功。")
work.say("容易错的是用杠杆长度当距离，要用力的方向上移动的距离。")
work.board("W = F<sub>1</sub>s = {F1} N × {s} m = {W1} J")

timeline.answer("F1", "所需的动力")
timeline.answer("s", "B 端下降的距离")
timeline.answer("W1", "动力做的功")

stage = Stage(timeline)

# 杆向下转时 angle 为负：A 端（左边）上升，B 端（右边）下降
lever = Lever(OA, OB, x=-3.4, y=1.0, width=5.2, angle=lambda f: -f.theta, name="杠杆", show=["L1", "L2", "theta"])
stage.add(
    *lever.parts,
    lever.hang(-OA, w=0.8, text="30 N", name="物体", show=["G", "h", "W2"]),
    lever.arm(-OA, lambda f: f"L2 = {f.L2:.3f} m"),
    lever.arm(OB, lambda f: f"L1 = {f.L1:.3f} m"),
    ForceArrow(lever.x_at(OB), lever.y_at(OB), 0.8, "down", text=lambda f: f"F1 = {f.F1:.0f} N"),
    Readout(lambda f: f"h = {f.h:.3f} m", -6.2, 3.3, size=22, anchor="left"),
    Readout(lambda f: f"s = {f.s:.3f} m", -3.6, 3.3, size=22, anchor="left"),
    Plot(
        (0, 0.1, 0.02), (0, 0.6, 0.2), "h / m", "力臂 / m",
        [
            Series(lambda f: f.h, lambda f: f.L1, ACCENT),
            Series(lambda f: f.h, lambda f: f.L2, OBJECT),
        ],
    ),
)
