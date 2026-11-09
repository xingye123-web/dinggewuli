import { PauseIcon } from "@/components/Icons";
import ProblemForm from "@/components/ProblemForm";
import TopBar from "@/components/TopBar";
import { EXAMPLES } from "@/lib/examples";

// 首页右边的演示：滑轮组示例停在物体升高 1 m 的那一帧，框出的是暂停后可以点的物体
const DEMO_BOXES = [
  { left: 18.29, top: 69.06, width: 10.55, height: 10.62, selected: true },
  { left: 24.69, top: 55.69, width: 4.5, height: 8 },
  { left: 20.19, top: 11.63, width: 4.5, height: 8 },
  { left: 27.78, top: 40.94, width: 2.81, height: 18.75 },
];

const HOW = [
  { title: "输入题目", text: "打字、粘贴截图或拍照都行。图片题读完后，会请你对照原图核对一遍。" },
  { title: "等三五分钟", text: "先出文字解析，再出带配音的讲解视频。答案会和视频里算出的结果互相核对。" },
  { title: "暂停读数", text: "拖进度条或逐帧前进，点画面里的物体，只看它的物理量和代入计算。" },
];

export default async function HomePage({ searchParams }: { searchParams: Promise<{ text?: string | string[] }> }) {
  const { text } = await searchParams;
  return (
    <>
      <TopBar page="home" hasExamples={EXAMPLES.length > 0} />
      <main className="wrap">
        <section className="hero">
          <div>
            <p className="kicker">
              <span className="kicker-line" aria-hidden="true" />
              初中物理 · 带配音的讲解视频
              <span className="kicker-chip">可暂停</span>
            </p>
            <h1 className="hero-title">
              把物理过程
              <br />
              按下暂停
            </h1>
            <p className="lede">输入一道题，生成一段讲解视频。随时暂停，点一下画面里的物体，就能读出这一刻它的每一个物理量。</p>
            <ProblemForm initialText={typeof text === "string" ? text : ""} />
          </div>

          <figure className="demo">
            <div className="demo-frame">
              <div className="demo-bar">
                <span className="paused">
                  <PauseIcon />
                  已定格
                </span>
                <span className="mono">第 471 帧 · t = 5.00 s</span>
              </div>
              <div className="stage">
                {/* eslint-disable-next-line @next/next/no-img-element -- 静态演示图，不需要图片优化 */}
                <img src="/demo/paused.jpg" alt="滑轮组提升物体的讲解视频，暂停在物体升高 1 m 的一帧" />
                {DEMO_BOXES.map((box) => (
                  <span
                    key={`${box.left}-${box.top}`}
                    className={box.selected ? "hitbox vf selected" : "hitbox vf"}
                    style={{ left: `${box.left}%`, top: `${box.top}%`, width: `${box.width}%`, height: `${box.height}%` }}
                  >
                    {box.selected && <span className="tag">物体</span>}
                  </span>
                ))}
              </div>
              <div className="strip">
                <span className="strip-title">物体 · 这一刻</span>
                <span>
                  <i>h</i>
                  <b>1.00 m</b>
                  <em>上升高度</em>
                </span>
                <span>
                  <i>
                    v<sub>物</sub>
                  </i>
                  <b>0.20 m/s</b>
                  <em>速度</em>
                </span>
                <span>
                  <i>G</i>
                  <b>240 N</b>
                  <em>物重</em>
                </span>
                <span>
                  <i>
                    W<sub>有</sub>
                  </i>
                  <b>240.0 J</b>
                  <em>有用功</em>
                </span>
              </div>
            </div>
            <figcaption>暂停在物体升高 1 m 的那一帧：绳端已经拉出 3 m，正好是 3 段绳子的 3 倍。</figcaption>
          </figure>
        </section>

        {EXAMPLES.length > 0 && (
          <section className="section" id="examples">
            <div className="section-head">
              <div>
                <p className="eyebrow">
                  <span className="kicker-line" aria-hidden="true" />
                  例题库 <em>EXAMPLES</em>
                </p>
                <h2 className="section-title">看看例题</h2>
              </div>
              <p>都已生成好，点开就能看</p>
            </div>
            <div className="examples">
              {EXAMPLES.map((example) => (
                <a className="card example" key={example.id} href={`/jobs/${example.id}`}>
                  <span className="thumb vf">
                    {/* eslint-disable-next-line @next/next/no-img-element -- 静态缩略图 */}
                    <img src={example.image} alt="" />
                    <span className="duration mono">{example.length}</span>
                  </span>
                  <div className="example-body">
                    <div className="topic">{example.topic}</div>
                    <p>{example.text}</p>
                  </div>
                </a>
              ))}
            </div>
          </section>
        )}

        <section className="section" id="how">
          <div className="section-head">
            <div>
              <p className="eyebrow">
                <span className="kicker-line" aria-hidden="true" />
                使用方式 <em>HOW IT WORKS</em>
              </p>
              <h2 className="section-title">怎么用</h2>
            </div>
          </div>
          <ol className="steps3">
            {HOW.map((step, index) => (
              <li key={step.title}>
                <span className="step-no">
                  0{index + 1}
                  <sup>/{HOW.length}</sup>
                </span>
                <b>{step.title}</b>
                <p>{step.text}</p>
              </li>
            ))}
          </ol>
        </section>
      </main>
    </>
  );
}
