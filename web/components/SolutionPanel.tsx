import { formatAny } from "@/lib/format";
import type { Solution } from "@/lib/types";
import { PlayIcon } from "./Icons";
import Markup from "./Markup";

export interface StepPicture {
  url: string;
  t: number;
}

interface Props {
  solution: Solution;
  /** 第几步（从 1 开始）配哪张视频截图。没有视频时为空。 */
  pictures?: Record<number, StepPicture>;
  /** 点配图时让视频跳到那一刻。 */
  onSeek?: (seconds: number) => void;
}

function clock(seconds: number) {
  const whole = Math.round(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

/** 文字解析：模型独立解题的结果，不用等视频生成。答案放在最前面，每一步旁边配视频里对应时刻的截图。 */
export default function SolutionPanel({ solution, pictures = {}, onSeek }: Props) {
  const answers = solution.answers ?? [];
  return (
    <div className="card solution">
      <h2>文字解析</h2>

      {answers.length > 0 && (
        <>
          <h3>答案</h3>
          <div className="answers">
            {answers.map((answer, index) => (
              <div className="answer" key={index}>
                <span>
                  {answers.length > 1 ? `(${index + 1}) ` : ""}
                  {answer.label}
                </span>
                <b>
                  <Markup text={formatAny(answer.value)} />
                  {answer.unit && <small>{answer.unit}</small>}
                </b>
              </div>
            ))}
          </div>
        </>
      )}

      {!!solution.knowns?.length && (
        <>
          <h3>已知</h3>
          <ul className="knowns">
            {solution.knowns.map((known, index) => (
              <li key={index}>
                {known.name}{" "}
                {known.symbol && (
                  <i>
                    <Markup text={known.symbol} />
                  </i>
                )}{" "}
                = <Markup text={formatAny(known.value)} /> {known.unit}
              </li>
            ))}
          </ul>
        </>
      )}

      {!!solution.steps?.length && (
        <>
          <h3>解题步骤</h3>
          <ol className="solve">
            {solution.steps.map((step, index) => {
              const picture = pictures[index + 1];
              return (
                <li key={index} className={picture ? "has-picture" : ""}>
                  <div className="solve-text">
                    {step.title && <b>{step.title}</b>}
                    {step.explain && <p>{step.explain}</p>}
                    {step.formula && (
                      <span className="eq">
                        <Markup text={step.formula} />
                      </span>
                    )}
                  </div>
                  {picture && (
                    <button
                      type="button"
                      className="step-picture"
                      onClick={() => onSeek?.(picture.t)}
                      aria-label={`视频跳到 ${clock(picture.t)}，看这一步`}
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element -- 服务器生成的截图 */}
                      <img src={picture.url} alt={`第 ${index + 1} 步在视频里的画面`} loading="lazy" />
                      <span>
                        <PlayIcon />
                        {clock(picture.t)}
                      </span>
                    </button>
                  )}
                </li>
              );
            })}
          </ol>
        </>
      )}

      {solution.pitfall && (
        <p className="pitfall">
          <b>易错点</b>
          {solution.pitfall}
        </p>
      )}
    </div>
  );
}
