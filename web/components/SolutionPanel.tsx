import type { Solution } from "@/lib/types";

/** 文字解析：模型独立解题的结果，不用等视频生成。 */
export default function SolutionPanel({ solution }: { solution: Solution }) {
  return (
    <section className="card">
      <h2>文字解析{solution.topic ? `（${solution.topic}）` : ""}</h2>

      {!!solution.knowns?.length && (
        <>
          <h3>已知</h3>
          <ul>
            {solution.knowns.map((known, index) => (
              <li key={index}>
                {known.name} {known.symbol} = {known.value} {known.unit}
              </li>
            ))}
          </ul>
        </>
      )}

      {!!solution.steps?.length && (
        <>
          <h3>解题步骤</h3>
          <ol>
            {solution.steps.map((step, index) => (
              <li key={index}>
                <b>{step.title}</b>
                {step.explain && <p>{step.explain}</p>}
                {step.formula && <p className="formula">{step.formula}</p>}
              </li>
            ))}
          </ol>
        </>
      )}

      {!!solution.answers?.length && (
        <>
          <h3>答案</h3>
          <ul>
            {solution.answers.map((answer, index) => (
              <li key={index}>
                {answer.label}：{answer.value} {answer.unit}
              </li>
            ))}
          </ul>
        </>
      )}

      {solution.pitfall && (
        <>
          <h3>易错点</h3>
          <p>{solution.pitfall}</p>
        </>
      )}
    </section>
  );
}
