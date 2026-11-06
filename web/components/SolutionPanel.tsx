import { formatAny } from "@/lib/format";
import type { Solution } from "@/lib/types";
import Markup from "./Markup";

/** 文字解析：模型独立解题的结果，不用等视频生成。答案放在最前面。 */
export default function SolutionPanel({ solution }: { solution: Solution }) {
  const answers = solution.answers ?? [];
  return (
    <div className="card">
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
            {solution.steps.map((step, index) => (
              <li key={index}>
                {step.title && <b>{step.title}</b>}
                {step.explain && <p>{step.explain}</p>}
                {step.formula && (
                  <span className="eq">
                    <Markup text={step.formula} />
                  </span>
                )}
              </li>
            ))}
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
