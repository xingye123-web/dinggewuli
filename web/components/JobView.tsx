"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchSolution, fetchStatus, fetchTimeline, fetchWorkerOnline, videoUrl } from "@/lib/api";
import type { JobStatus, Solution, Timeline } from "@/lib/types";
import ConfirmForm from "./ConfirmForm";
import Progress from "./Progress";
import SolutionPanel from "./SolutionPanel";
import TopBar from "./TopBar";
import VideoPlayer from "./VideoPlayer";

const POLL_MS = 2000;
const MAX_POLL_FAILURES = 5;

const STAGE_NAMES: Record<string, string> = {
  queued: "排队中",
  reading: "正在读题",
  awaiting_confirmation: "等你核对题目",
  solving: "正在解题",
  authoring: "正在写动画代码",
  checking: "正在检查代码和核对答案",
  narrating: "正在配音",
  rendering: "正在渲染视频",
  done: "已完成",
  failed: "生成失败",
};

const FAILURE_REASONS: Record<string, string> = {
  unsupported: "现有的动画零件还画不出这道题。",
  solving: "这道题没有解出答案，可能是条件不全或超出初中范围。",
  reading: "没有从图片里读出题目，请换一张清晰的照片。",
  model: "调用解题模型失败，请稍后再试。",
  narration: "配音失败，请稍后再试。",
};

function editableText(status: JobStatus) {
  const text = status.problem_text ?? "";
  return status.figure ? `${text}\n题图信息：${status.figure}` : text;
}

function duration(seconds: number) {
  const whole = Math.round(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

/** 视频还没出来时，画面位置显示的进度。 */
function pendingText(status: JobStatus | null) {
  if (!status) return undefined;
  if (status.status === "failed") return "视频没有生成成功";
  if (status.status === "rendering" && status.progress?.total) {
    return `正在渲染视频，${status.progress.done ?? 0} / ${status.progress.total} 段`;
  }
  return STAGE_NAMES[status.status] ?? "视频生成中";
}

export default function JobView({ id }: { id: string }) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [solution, setSolution] = useState<Solution | null>(null);
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [lostConnection, setLostConnection] = useState(false);
  const [workerOnline, setWorkerOnline] = useState(true);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    let failures = 0;

    async function poll() {
      let finished = false;
      try {
        const next = await fetchStatus(id);
        if (stopped) return;
        failures = 0;
        setLostConnection(false);
        setStatus(next);
        finished = next.status === "done" || next.status === "failed";
        if (next.status === "queued") setWorkerOnline(await fetchWorkerOnline());
      } catch {
        failures += 1;
        if (failures >= MAX_POLL_FAILURES) setLostConnection(true);
      }
      if (!stopped && !finished) timer = setTimeout(poll, POLL_MS);
    }

    void poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [id]);

  const solutionReady = !!status?.solution_ready;
  const timelineReady = !!status?.timeline_ready;

  useEffect(() => {
    if (solutionReady) fetchSolution(id).then(setSolution, () => setSolution(null));
  }, [id, solutionReady]);

  useEffect(() => {
    if (timelineReady) fetchTimeline(id).then(setTimeline, () => setTimeline(null));
  }, [id, timelineReady]);

  const failed = status?.status === "failed";
  const finished = status?.status === "done";
  const awaiting = status?.status === "awaiting_confirmation";
  const solutionCard = solution ? <SolutionPanel solution={solution} /> : null;
  const stateClass = finished ? "state done" : failed ? "state failed" : "state busy";

  return (
    <>
      <TopBar page="job" />
      <main className="wrap">
        {!status && !lostConnection && <p className="hint">正在读取任务…</p>}
        {lostConnection && (
          <p className="error" role="alert">
            连接不上服务器，正在重试。
          </p>
        )}

        {awaiting && status ? (
          <ConfirmForm
            id={id}
            imageCount={status.image_count ?? 1}
            initialText={status.problem_text ?? ""}
            initialFigure={status.figure ?? ""}
          />
        ) : (
          status?.problem_text && (
            <section className="card problem">
              <div className="problem-head">
                {solution?.topic && <span className="chip">{solution.topic}</span>}
                <span className={stateClass} role="status">
                  {STAGE_NAMES[status.status] ?? status.status}
                </span>
                {finished && status.total_seconds !== undefined && (
                  <span className="muted mono">用时 {duration(status.total_seconds)}</span>
                )}
                {(finished || failed) && (
                  <Link href={`/?text=${encodeURIComponent(editableText(status))}`}>题目读错了？修改后重新生成</Link>
                )}
              </div>
              <p className="problem-text">{status.problem_text}</p>
              {status.figure && <p className="problem-figure">题图信息：{status.figure}</p>}
            </section>
          )
        )}

        {failed && status && (
          <section className="card notice">
            <h2>没有生成成功</h2>
            <p>{FAILURE_REASONS[status.stage ?? ""] ?? "动画没有生成成功，可以回到首页重新提交这道题。"}</p>
            <details>
              <summary>查看技术细节</summary>
              <pre>{JSON.stringify(status.errors, null, 1)}</pre>
            </details>
          </section>
        )}

        {timeline ? (
          <VideoPlayer
            timeline={timeline}
            videoSrc={status?.video_ready ? videoUrl(id) : null}
            pending={pendingText(status)}
            solution={solutionCard}
          />
        ) : (
          <>
            {status && !failed && !awaiting && (
              <Progress status={status} solutionReady={solutionReady} workerOnline={workerOnline} />
            )}
            {solutionCard && <section className="below single">{solutionCard}</section>}
          </>
        )}
      </main>
    </>
  );
}
