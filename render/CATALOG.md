# 物理题讲解动画代码规范

你要写一段 Python，把一道初中物理题变成带配音的讲解视频。外观由零件决定，你决定用哪些零件、放在哪、和哪个物理量绑定，以及怎么讲。

## 硬性要求

- 第一行写 `from physkit import *`，另外只能 `import math`。
- 顶层必须定义 `timeline = Timeline(...)` 和 `stage = Stage(timeline)`。
- 不能用 while、try、class、with，不能访问下划线开头的名字，也不能调用 open、eval、getattr 等内置函数，不能用 f.clock 和 f.index。
- 每一帧只能取决于 `f`，不能用随机数、时间或任何全局状态。
- 所有会变的数值都先用 `timeline.quantity` 声明，零件和文字再通过 `f.x` 读取，不要另外计算一遍。

## 物理

- 只用初中物理的概念和公式，不出现加速度、牛顿第二定律、动能定理等高中内容。
- 代入计算时单位要统一：题目给 cm、cm²、cm³、g 的，先声明换算成 m、m²、m³、kg 的量，板书里代入换算后的值。
- 动画的快慢由旁白决定，所以题目里的时间和距离一律用 `phase.progress(f)` 换算，比如 `T * lift.progress(f)`。

## 讲解

- 物体运动的阶段给 `min_seconds`，讲解时画面不动的阶段不给。
- 讲解要按解答的顺序覆盖每一问：说清用什么公式、为什么用这个距离或这个力，再代入。
- 旁白写成老师说话的口语，每句不超过 40 字。单位用中文（牛、米、焦、瓦、秒、帕），公式里的字母说成名称（“有用功”，不说“W有”）。
- 旁白和板书尽量用 `{id}` 引用物理量，不要手写算出来的结果。
- 每一步代入计算都要有一行 `phase.board(...)`，板书用符号和单位，比如 N、J。
- 题目所求的每一项都要用 `timeline.answer` 标记。过程结束后会变化的量（比如瞬时功率）要用 at 指定取值时刻。
- 随过程变化的量，digits 至少是 2，暂停时才读得准。画面上的读数和面板用相同的小数位数。
- 绝对值大于 10000 或小于 0.001 的数要用科学计数法。旁白和板书里的 {id} 会自动转换；画面上的读数用 sci(值, 小数位数) 生成，比如 Readout(lambda f: f"p = {sci(f.p, 0)} Pa", ...)；直接写在旁白或板书里的这类数，也要写成 1.5×10<sup>4</sup>、8×10<sup>-4</sup>（板书）或 1.5乘10的4次方、8乘10的负4次方（旁白）。

## 画面

- 题目是滑轮组（含单个定滑轮、动滑轮）时一律用 PulleyRig，不要自己摆 Pulley 和 Rope。
- 题目是杠杆时用 Lever，是斜面时用 Incline，物块用它们的 hang、block 方法生成，不要自己用 Rod 和 Block 拼。
- 力不是竖直或水平时，ForceArrow 的 direction 写角度，比如沿斜面向上写 incline.angle。

- 坐标：x 从 -7.11 到 7.11，y 从 -4 到 4，原点在中心。
- 实物放在左边：x 不超过 0.75，y 不低于 -3.3。
- 右上方由系统显示板书，底部由系统显示字幕，这两处不要放东西。Plot 自动放在右下方，不用给位置。
- 文字不能超出画面，不能互相重叠，不能压在容器壁或物块边框上，否则会被退回，错误信息会给出是哪个零件的文字、文字的坐标范围，以及至少要挪开多远，照着改。
- 零件的 text 和 Readout 和板书一样可以用 <sub>、<sup> 写下标上标，比如 text="R<sub>1</sub>"。

## 常见错误（以往被退回最多的，写完逐条对一遍）

- 会动的物体，要算它在开始和结束两个位置时是否都还在实物区内（x 不超过 0.75、y 不低于 -3.3），不只看开始。
- Ground、Road 的 y 不要低于 -3.1，下面还有阴影线。
- 文字放在容器外面或物块正中，离容器壁、物块边框至少 0.3；两段文字之间也要留空，尤其是会移动的标签（比如两车相遇时各自的标签）。
- 旁白和板书里的 `{id}` 只能是 `timeline.quantity` 或 `timeline.constant` 声明过的 id，不能是 Python 变量名。
- 零件的属性（`block.top`、`block.bottom`、PulleyRig 的位置等）是函数，做加减要写 `lambda f: block.top(f) + 0.3`，不能写 `block.top + 0.3`。
- 零件的 `show` 只能放 `timeline.quantity` 声明的量，常数不能放；有 `show` 的零件必须给 `name`。
- 必须调用一次 `timeline.show_clock(id, 名称)`。
- 随过程变化的量 digits 至少是 2。

# 零件手册

## Timeline(text, assumptions=())

题目的物理过程：分哪几个阶段、有哪些物理量、每个物理量怎样随帧变化。

- `answer(id, label, at=None)`：标记题目所求的量，label 要和解答里的答案名称完全一致，系统会逐项核对数值。

at 是取值时刻，默认取最后一帧。过程结束后会变化的量要指定，比如功率：物体停下后是 0。
- `constant(id, value)`：声明公式里要用的常数，比如绳子段数 n。
- `event(moment, label)`：声明一个关键时刻，moment 写成 lift.at(0.5) 或 lift.end。
- `phase(label, min_seconds=None)`：按顺序追加一个阶段，返回 Phase。

物体在运动的阶段必须给 min_seconds，表示动画至少持续多久。讲解时画面不动的阶段不要给。
阶段的实际时长由旁白决定，旁白比 min_seconds 长时，动画会放慢。
- `quantity(id, symbol, name, unit, digits, value)`：声明一个物理量。value 是数值，或 lambda f: ... 这样的函数，可以用 f.x 引用先声明的量。

symbol 可以含 <sub> 标签，比如 "W<sub>有</sub>"。digits 是显示的小数位数。
函数返回 None 表示这一帧没有意义，面板会显示“—”。
- `show_clock(id, label)`：指定面板顶部显示的进度量，比如题中时间或下降深度。

## Stage(timeline, background='#12291F')

一道题的画面。按 add 的先后顺序绘制，后加的盖在上面。板书和字幕由系统自动加上。

- `add(*parts)`：把零件加到舞台上。

## Ceiling(x0, x1, y)

天花板。从 x0 到 x1 的横梁，下表面在 y。

## Ground(x0, x1, y)

地面。从 x0 到 x1 的横线，上表面在 y。下面还有 0.16 高的阴影线，所以 y 不要低于 -3.1。

## PulleyRig(n, pull, height, max_height, x=-3.6, weight_text=None, weight_name='物体', weight_show=(), moving_show=(), fixed_show=(), end_show=(), ceiling_y=3.45, ground_y=-3.05)

完整的滑轮组。题目是滑轮组时优先用它，滑轮和绳子的走法由它保证正确，每段绳子都竖直。

n 是动滑轮上承担物重的绳子段数，n=1 就是单个定滑轮。pull 是绳端拉动的方向：up 或 down，n=1 只能是 down。
height 是 lambda f: f.h 这样的函数，单位是米。max_height 是物体上升的最大高度，单位是米，用来自动选比例。
用 stage.add(*rig.parts) 把它加到舞台上。段数编号会自动标在绳子旁边。

属性：
- end_x：绳端的横坐标（数值）；end_y：绳端的纵坐标（函数），可以给 ForceArrow 和 Ruler 用。
- left_x、right_x：整个滑轮组左右边界（数值），放标尺和文字时要避开。
- weight_bottom：物体下表面的纵坐标（函数）；weight_start：物体下表面的初始纵坐标（数值）。
- end_start：绳端的初始纵坐标（数值）；meter：1 米对应的画面长度。

## Lever(left, right, x=-3.2, y=0.6, width=5.6, angle=0, name=None, show=())

杠杆。题目是杠杆时用它：一根杆加三角形支点 O，杆可以绕支点转动。

left、right 是支点左边和右边的杆长（米）。杆的中点在 (x, y)，画面上的总长是 width，比例自动算。
angle 是杆和水平方向的夹角（度，逆时针为正），可以写 lambda f: ...，让杠杆转起来。
name、show 用于点击杆。用 stage.add(*lever.parts) 加到舞台上。

属性和方法：
- pivot_x、pivot_y：支点坐标（数值）；scale：1 米对应的画面长度。
- x_at(d)、y_at(d)：杆上离支点 d 米的点（支点左边 d 取负数），返回函数，可直接给 ForceArrow 当 x、y。
- hang(d, w=0.7, h=0.6, text=None, drop=0.5, color=OBJECT, name=None, show=())：在杆上 d 处用细绳挂一个物块，
  物块上沿比挂点低 drop，文字放不下时物块会自动加宽。返回一个零件，要另外 stage.add。
- arm(d, text, offset=0.5, color=ACCENT)：标出支点到 d 处的力臂。竖直方向的力，力臂就是水平距离，
  所以标注线是水平的。offset 为正画在杆的上方，为负画在下方。返回一个零件，要另外 stage.add。

## Incline(length, height, x0=-6.5, y0=-2.7, width=5.8, rise_to='right', length_text=None, height_text=None)

斜面。题目是斜面时用它：直角三角形，底边在 y0，坡脚在 x0，坡面向右上升（rise_to="left" 时向左上升）。

length、height 是斜面的长和高（米）。width 是坡面水平方向在画面上的最大长度，比例自动算，
高度太高时会自动缩小。length_text、height_text 写在坡面和高的标注旁边，比如 "L = 4 m"。
用 stage.add(*incline.parts) 加到舞台上。

属性和方法：
- angle：坡面的方向（度），ForceArrow 的 direction 写它就是沿斜面向上，写 angle + 180 是沿斜面向下。
- scale：1 米对应的画面长度；top_x、top_y：坡顶的坐标（数值）。
- x_at(s)、y_at(s)：坡面上离坡脚 s 米的点，s 可以是 lambda f: ...，返回函数。
- block(s, w=0.9, h=0.6, text=None, color=OBJECT, name=None, show=())：放在坡面上的物块，返回零件，要另外 stage.add。
  s 是物块沿斜面走过的距离（米），s=0 时物块在坡脚，s=length 时物块到坡顶（画面上按物块长度压缩了一点）。
- block_x(s, w=0.9, h=0.6, at="center")、block_y(...)：物块上一点的坐标，返回函数，给 ForceArrow 当起点。
  at 是 center（中心）、front（朝坡顶那一面的中点）或 back（朝坡脚那一面的中点）。
  沿斜面向上的拉力从 front 画，沿斜面向下的摩擦力从 back 画，箭头就不会压住物块上的字。

## Rod(start, end, color='#AEB8C4', width=4)

刚性连杆，连接 start 和 end 两点，比如滑轮的支架、挂钩。点写成 (x, y)。

## Pulley(x, y, r=0.35, turn=0, name=None, show=())

滑轮，圆心在 (x, y)，半径 r。turn 是转过的角度（弧度）。

left_x、right_x 是左右切点的横坐标，是函数，可以直接当作绳子端点的 x，但不能做加减。
y 也可以是函数，做加减要写成 lambda f: moving_y(f) - 0.5。

## Over(pulley)

绳子从滑轮上方绕过，只用在 Rope 的路径里。

## Under(pulley)

绳子从滑轮下方绕过，只用在 Rope 的路径里。

## Rope(path, color='#E8C547', width=4, name=None, show=())

绳子。path 依次列出路径：(x, y) 是端点，Over(滑轮) 和 Under(滑轮) 是绕过滑轮。

例：Rope([(a.left_x, y0), Over(a), Under(b), (b.right_x, y1)])。
绳子从哪一侧到达滑轮，就从另一侧离开。设置 name 后，可点击的是最后一段，也就是绳端。

- `line_pieces(f)`：绳子的直线段，每段写成 (x0, y0, x1, y1)。

## Block(x, y, w, h, text=None, color='#5DA9E9', name=None, show=())

物块，中心在 (x, y)，宽 w 高 h。text 是写在物块上的文字。

top、bottom 是上下表面的纵坐标，是函数，可以直接当作绳子或连杆端点的 y，但不能做加减。

## ForceArrow(x, y, length, direction='up', text=None, color='#FF7A59')

力的箭头，从 (x, y) 出发，朝 direction 画，长度 length。

direction 是 up、down、left、right，或者一个角度（度，从水平向右逆时针量），
比如沿斜面向上写 incline.angle，沿斜面向下写 incline.angle + 180。
text 写在箭头旁边。长度小于 0.05 时不画。

## Readout(text, x, y, size=24, color='#E6EBF0', anchor='center')

文字。text 是字符串或 lambda f: ...，anchor 指 (x, y) 对齐文字的哪一边：center、left、right。

超出画面或进入右侧板书区、底部字幕区时会自动往里挪，但不会避开别的文字和线条。

## Ruler(x, y0, y1, text=None, color='#5DA9E9', text_side='right')

竖直标尺，从 y0 量到 y1，表示一段距离。text 写在 y1 一端，text_side 是 right、left 或 top。

## Plot(x_range, y_range, x_label, y_label, series, x=4.1, y=-1.42, width=4.9, height=2.15)

坐标图，固定放在画面右下方，通常不用改位置，一道题最多一个。

x_range、y_range 写成 (起点, 终点, 刻度间隔)，刻度不要太密，每个轴 5 到 6 个刻度。
曲线随动画逐帧画出，淡色线是完整走势。

## Series(x, y, color='#5DA9E9')

Plot 里的一条曲线。x、y 都是 lambda f: ...。

## Beaker(x, y0, w, h, level, name=None, show=())

盛水的容器，底部中心在 (x, y0)，宽 w 高 h。level 是水面的纵坐标，可以随帧变化。

想让物块显得泡在水里，就先 add 物块，再 add 容器。

## SpringScale(x, top, reading, max_reading, name=None, show=())

弹簧测力计，顶部中心在 (x, top)。reading 是示数，max_reading 是量程。

hook_y 是下端挂钩的纵坐标，可以当作连杆的端点。

## Wire(points, color='#AEB8C4')

导线，依次连接 points 里的点，每个点写成 (x, y)。元件放在导线上会盖住它经过的那一段，所以导线可以画成完整的回路。

## Battery(x, y, horizontal=True, text=None, text_side='top', positive_first=True, name=None, show=())

电源，一长一短两条线，长线是正极。positive_first 为真时，正极在左边（竖直放置时在上边）。

## Resistor(x, y, horizontal=True, text=None, text_side='top', name=None, show=())

定值电阻，画成矩形。text 是标注，比如 "R1 = 10 Ω"，text_side 是 top、bottom、left 或 right。

## Rheostat(x, y, slider, horizontal=True, text=None, text_side='bottom', name=None, show=())

滑动变阻器，矩形加滑片箭头。slider 是滑片位置，从 0 到 1，通常写成 lambda f: f.R2 / 20。

## Bulb(x, y, brightness=1.0, horizontal=True, text=None, text_side='top', name=None, show=())

灯泡，圆圈加叉。brightness 是亮度，从 0 到 1，通常写成和电功率成比例的 lambda f: ...。

## Meter(x, y, kind, horizontal=True, text=None, text_side='top', name=None, show=())

电表，kind 是 "A"（电流表）或 "V"（电压表）。text 通常是读数，比如 lambda f: f"{f.I:.2f} A"。

## Switch(x, y, closed=True, horizontal=True, text=None, text_side='top', name=None, show=())

开关。closed 为真时闭合，可以写成 lambda f: ... 让它在某个阶段合上。

## Road(x0, x1, y, length, tick, unit='m')

水平路面，从 x0 到 x1，表面在 y，代表 length 米，每隔 tick 米标一个刻度，刻度不超过 8 个。

road.x_at(d) 把距离（米）换算成画面横坐标，给 Cart 用：x=lambda f: road.x_at(f.s)。
road.scale 是每米对应的画面长度。

## Cart(x, y, w=0.9, h=0.42, text=None, color='#5DA9E9', name=None, show=())

小车或火车，车身中心横坐标是 x，车轮压在路面 y 上。text 写在车身上。火车就把 w 设成车长乘以 road.scale。

## sci(value, digits=2)

画面上显示数字时用它：很大或很小的数写成 1.5×10⁴，否则保留 digits 位小数。

## Phase（由 timeline.phase 返回）

动画的一个阶段，由 timeline.phase() 创建。属性 start、end 是它的开始和结束时刻。

- `active(f)`：这一帧是否处在本阶段内，含首尾两帧。
- `at(fraction)`：本阶段某个进度对应的时刻，at(0.5) 是阶段中点。
- `board(expr)`：加一行板书，显示在画面右上方，本阶段开始时出现。同一行也会出现在网页面板里，数值随帧变化。

可以用 <sub> 写下标，比如 "W<sub>有</sub> = Gh = {G} N × {h} m = {W_use} J"。
- `progress(f)`：这一帧在本阶段的进度：开始前是 0，结束后是 1。只有声明了 min_seconds 的阶段才会连续变化。
- `say(text)`：加一句旁白，按顺序读出，同时显示成字幕。

写成口语：单位用中文（牛、米、焦），不要写符号。{id} 替换成本阶段结束时的数值。

可用颜色常量：ROPE、OBJECT、STEEL、ACCENT、INK。
