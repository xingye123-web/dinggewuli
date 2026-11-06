import type { JobStatus } from "@/lib/types";

const STEPS = [
  { key: "reading", label: "读题" },
  { key: "solving", label: "解题" },
  { key: "authoring", label: "写动画代码" },
  { key: "checking", label: "检查和核对答案" },
  { key: "narrating", label: "配音" },
  { key: "rendering", label: "渲染视频" },
];

function seconds(value: number | undefined) {
  if (value === undefined) return "";
  const whole = Math.round(value);
  return whole < 60 ? `${whole} 秒` : `${Math.floor(whole / 60)} 分 ${whole % 60} 秒`;
}

/** 正在做的这一步的补充说明，比如配到第几句、第几次写代码。 */
function detail(status: JobStatus) {
  if (status.status === "narrating" && status.narration_total) {
    return `${status.narration_done ?? 0} / ${status.narration_total} 句`;
  }
  if ((status.status === "authoring" || status.status === "checking") && status.attempt && status.attempt > 1) {
    return `第 ${status.attempt} 次`;
  }
  if (status.status === "rendering" && status.progress?.total) {
    return `${status.progress.done ?? 0} / ${status.progress.total} 段`;
  }
  return "进行中…";
}

/** 视频出来前，台面的位置显示生成到哪一步。只有图片题才有「读题」这一步。 */
export default function Progress({ status, solutionReady, workerOnline }: { status: JobStatus; solutionReady: boolean; workerOnline: boolean }) {
  const done = status.stage_seconds ?? {};
  const hasReading = "reading" in done || status.status === "reading";
  const steps = STEPS.filter((step) => step.key !== "reading" || hasReading);
  const current = steps.findIndex((step) => step.key === status.status);

  return (
    <section className="progress" aria-label="生成进度">
      <ol className="stepper">
        {steps.map((step, index) => {
          const state = current === -1 ? "" : index < current ? "ok" : index === current ? "now" : "";
          return (
            <li key={step.key} className={state}>
              {step.label}
              <small>{state === "ok" ? seconds(done[step.key]) : state === "now" ? detail(status) : ""}</small>
            </li>
          );
        })}
      </ol>
      <p>
        {status.status === "queued" ? (
          workerOnline ? (
            <b>排队中，马上开始。</b>
          ) : (
            <>
              <b>生成服务暂时离线，</b>它上线后会自动开始这道题。
            </>
          )
        ) : solutionReady ? (
          <>
            <b>文字解析已经出来了，</b>可以先往下看。
          </>
        ) : (
          "一道题通常要 3 到 5 分钟，这个页面可以开着等，也可以收藏下来稍后再看。"
        )}
      </p>
    </section>
  );
}
