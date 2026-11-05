// 由结构化题目求出逐帧时间线。Manim 场景和网页面板读同一份结果，数值因此不会对不上。
import { readFileSync, writeFileSync } from 'node:fs'

const FPS = 30
const PREP = 1 // 开始提升前的静止时长（秒）
const HOLD = 2 // 提升结束后的静止时长（秒）
const METER = 0.6 // 画面中 1 m 对应的 Manim 单位长度

// 舞台几何，单位是 Manim 坐标
const LAYOUT = {
  frameW: 14.222,
  frameH: 8,
  ym0: -1.75, // 动滑轮中心的初始高度
  yh0: -1.6, // 绳端的初始高度
  weightX: -4.4,
  weightW: 1.3,
  weightH: 0.9,
  ropeEndX: -3.55,
  movingX: -3.9,
  fixedX: -4.6,
  fixedY: 2.75,
  pulleyR: 0.35,
}

function round(x, digits = 4) {
  const k = 10 ** digits
  return Math.round(x * k) / k
}

function solvePulleyLift(ir) {
  const { G, h, t, F, n } = ir.knowns
  const s = n * h
  const vObj = h / t
  const vRope = s / t
  const Wuse = G * h
  const Wtot = F * s
  const P = Wtot / t
  const eta = (Wuse / Wtot) * 100
  const Gm = n * F - G

  const duration = PREP + t + HOLD
  // Manim 输出的帧号是 0 到 duration × fps − 1，时间线和它逐帧对应
  const count = Math.round(duration * FPS)
  const frames = {
    t: [], tau: [], h: [], s: [], v_obj: [], v_rope: [], F: [], G: [], G_m: [],
    W_use: [], W_tot: [], W_ext: [], P: [], eta: [], ym: [], yh: [],
  }
  const regions = { weight: [], moving: [], rope: [], fixed: [] }

  // 把 Manim 坐标的矩形换算成视频画面的百分比，供网页做点击区域
  const toPercent = (x0, y0, x1, y1) => [
    round(((x0 + LAYOUT.frameW / 2) / LAYOUT.frameW) * 100, 2),
    round(((LAYOUT.frameH / 2 - y1) / LAYOUT.frameH) * 100, 2),
    round(((x1 - x0) / LAYOUT.frameW) * 100, 2),
    round(((y1 - y0) / LAYOUT.frameH) * 100, 2),
  ]

  for (let i = 0; i < count; i++) {
    const clock = i / FPS
    const tau = Math.min(Math.max(clock - PREP, 0), t)
    const moving = clock >= PREP && clock <= PREP + t // 含到达的那一帧，讲解跳到这里时功率仍是题目的值
    const hNow = vObj * tau
    const sNow = vRope * tau
    const ym = LAYOUT.ym0 + hNow * METER
    const yh = LAYOUT.yh0 + sNow * METER

    frames.t.push(round(clock))
    frames.tau.push(round(tau))
    frames.h.push(round(hNow))
    frames.s.push(round(sNow))
    frames.v_obj.push(moving ? vObj : 0)
    frames.v_rope.push(moving ? vRope : 0)
    frames.F.push(F)
    frames.G.push(G)
    frames.G_m.push(Gm)
    frames.W_use.push(round(G * hNow))
    frames.W_tot.push(round(F * sNow))
    frames.W_ext.push(round(F * sNow - G * hNow))
    frames.P.push(moving ? P : 0)
    frames.eta.push(tau > 0 ? eta : null) // 还没做功时，效率没有意义
    frames.ym.push(round(ym))
    frames.yh.push(round(yh))

    const weightBottom = ym - 0.75 - LAYOUT.weightH
    regions.weight.push(toPercent(
      LAYOUT.weightX - LAYOUT.weightW / 2, weightBottom,
      LAYOUT.weightX + LAYOUT.weightW / 2, ym - 0.75,
    ))
    regions.moving.push(toPercent(
      LAYOUT.movingX - LAYOUT.pulleyR, ym - LAYOUT.pulleyR,
      LAYOUT.movingX + LAYOUT.pulleyR, ym + LAYOUT.pulleyR,
    ))
    regions.rope.push(toPercent(LAYOUT.ropeEndX - 0.2, ym, LAYOUT.ropeEndX + 0.2, yh + 0.2))
    regions.fixed.push(toPercent(
      LAYOUT.fixedX - LAYOUT.pulleyR, LAYOUT.fixedY - LAYOUT.pulleyR,
      LAYOUT.fixedX + LAYOUT.pulleyR, LAYOUT.fixedY + LAYOUT.pulleyR,
    ))
  }

  return {
    text: ir.text,
    assumptions: ir.assumptions,
    fps: FPS,
    duration,
    layout: { ...LAYOUT, meter: METER },
    quantities: [
      { id: 'tau', symbol: 't', name: '提升用时', unit: 's', digits: 2 },
      { id: 'h', symbol: 'h', name: '物体上升高度', unit: 'm', digits: 2 },
      { id: 's', symbol: 's', name: '绳端移动距离', unit: 'm', digits: 2 },
      { id: 'v_obj', symbol: 'v<sub>物</sub>', name: '物体速度', unit: 'm/s', digits: 2 },
      { id: 'v_rope', symbol: 'v<sub>绳</sub>', name: '绳端速度', unit: 'm/s', digits: 2 },
      { id: 'F', symbol: 'F', name: '绳端拉力', unit: 'N', digits: 0 },
      { id: 'G', symbol: 'G', name: '物重', unit: 'N', digits: 0 },
      { id: 'G_m', symbol: 'G<sub>动</sub>', name: '动滑轮重', unit: 'N', digits: 0 },
      { id: 'W_use', symbol: 'W<sub>有</sub>', name: '有用功（累计）', unit: 'J', digits: 1 },
      { id: 'W_tot', symbol: 'W<sub>总</sub>', name: '总功（累计）', unit: 'J', digits: 1 },
      { id: 'W_ext', symbol: 'W<sub>额</sub>', name: '额外功（累计）', unit: 'J', digits: 1 },
      { id: 'P', symbol: 'P', name: '拉力功率', unit: 'W', digits: 0 },
      { id: 'eta', symbol: 'η', name: '机械效率', unit: '%', digits: 0 },
    ],
    objects: {
      weight: { name: '物体', quantities: ['G', 'h', 'v_obj', 'W_use'] },
      moving: { name: '动滑轮', quantities: ['G_m', 'h', 'W_ext'] },
      rope: { name: '绳端', quantities: ['F', 's', 'v_rope', 'W_tot', 'P'] },
      fixed: { name: '定滑轮', quantities: ['F', 'eta'] },
    },
    formulas: [
      { label: '绳端距离', expr: 's = nh = {n} × {h} m = {s} m' },
      { label: '有用功', expr: 'W<sub>有</sub> = Gh = {G} N × {h} m = {W_use} J' },
      { label: '总功', expr: 'W<sub>总</sub> = Fs = {F} N × {s} m = {W_tot} J' },
      { label: '额外功', expr: 'W<sub>额</sub> = W<sub>总</sub> − W<sub>有</sub> = {W_ext} J' },
    ],
    constants: { n },
    phases: [
      { label: '静止', t0: 0, t1: PREP },
      { label: '匀速提升', t0: PREP, t1: PREP + t },
      { label: '停止', t0: PREP + t, t1: duration },
    ],
    events: [
      { t: PREP, label: '开始提升' },
      { t: PREP + t / 2, label: `上升 ${h / 2} m` },
      { t: PREP + t, label: `上升 ${h} m` },
    ],
    answers: { W_use: Wuse, W_tot: Wtot, P, eta, G_m: Gm, s },
    steps: [
      {
        t: 0,
        title: '审题',
        text: `物重 G = ${G} N，${t} s 内匀速上升 h = ${h} m，拉力 F = ${F} N，动滑轮上有 n = ${n} 段绳子。`,
      },
      {
        t: PREP + t / 2,
        title: '绳端和物体的关系',
        text: `物体上升 ${h / 2} m 时，${n} 段绳子各缩短 ${h / 2} m，绳端移动 ${(n * h) / 2} m，所以 s = nh。`,
      },
      {
        t: PREP + t,
        title: '有用功',
        text: `W有 = Gh = ${G} N × ${h} m = ${Wuse} J。`,
      },
      {
        t: PREP + t,
        title: '总功和功率',
        text: `s = ${n} × ${h} m = ${s} m，W总 = Fs = ${F} N × ${s} m = ${Wtot} J，P = W总 / t = ${Wtot} J ÷ ${t} s = ${P} W。`,
      },
      {
        t: PREP + t,
        title: '机械效率',
        text: `η = W有 / W总 = ${Wuse} J ÷ ${Wtot} J = ${eta}%。`,
      },
      {
        t: PREP + t,
        title: '动滑轮重',
        text: `不计绳重和摩擦，nF = G + G动，所以 G动 = ${n} × ${F} N − ${G} N = ${Gm} N。`,
      },
      {
        t: PREP + t / 2,
        title: '易错点',
        text: '计算总功时，距离要用绳端移动的 s，不能用物体上升的 h。拖动进度条，可以看到 s 始终是 h 的 3 倍。',
      },
    ],
    frames,
    regions,
  }
}

const dir = new URL('./', import.meta.url)
const ir = JSON.parse(readFileSync(new URL('pulley_ir.json', dir), 'utf8'))
const timeline = solvePulleyLift(ir)
writeFileSync(new URL('timeline.json', dir), JSON.stringify(timeline))
console.log('frames', timeline.frames.t.length, 'answers', timeline.answers)
