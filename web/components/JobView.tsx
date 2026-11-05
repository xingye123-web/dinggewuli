"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchSolution, fetchStatus, fetchTimeline, videoUrl } from "@/lib/api";
import type { JobStatus, Solution, Timeline } from "@/lib/types";
import ConfirmForm from "./ConfirmForm";
import SolutionPanel from "./SolutionPanel";
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
  queue: "任务队列没有启动。",
  model: "调用解题模型失败，请稍后再试。",
  narration: "配音失败，请稍后再试。",
};

function editableText(status: JobStatus) {
  const text = status.problem_text ?? "";
  return status.figure ? `${text}\n题图信息：${status.figure}` : text;
}

function stageText(status: JobStatus) {
  const name = STAGE_NAMES[status.status] ?? status.status;
  if (status.status === "narrating" && status.narration_total) {
    return `${name}（${status.narration_done ?? 0} / ${status.narration_total}）`;
  }
  if (status.status === "authoring" && status.attempt && status.attempt > 1) {
    return `${name}（第 ${status.attempt} 次）`;
  }
  return name;
}

export default function JobView({ id }: { id: string }) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [solution, setSolution] = useState<Solution | null>(null);
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [lostConnection, setLostConnection] = useState(false);

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

  return (
    <main>
      <p>
        <Link href="/">← 再问一道题</Link>
      </p>
      <h1>定格物理</h1>

      {!finished && (
        <p className={failed ? "error" : "status"} role="status">
          {status ? stageText(status) : "正在读取任务…"}
        </p>
      )}
      {lostConnection && (
        <p className="error" role="alert">
          连接不上渲染服务，正在重试。
        </p>
      )}
      {failed && status && (
        <div className="card">
          <p>{FAILURE_REASONS[status.stage ?? ""] ?? "动画没有生成成功，可以回到首页重新提交这道题。"}</p>
          <details>
            <summary>查看技术细节</summary>
            <pre>{JSON.stringify(status.errors, null, 1)}</pre>
          </details>
        </div>
      )}

      {awaiting && status ? (
        <ConfirmForm id={id} initialText={status.problem_text ?? ""} initialFigure={status.figure ?? ""} />
      ) : (
        status?.problem_text && (
          <section className="card">
            <h2>题目</h2>
            <p>{status.problem_text}</p>
            {status.figure && <p className="note">题图信息：{status.figure}</p>}
            {(finished || failed) && (
              <p>
                <Link href={`/?text=${encodeURIComponent(editableText(status))}`}>题目读错了？修改后重新生成</Link>
              </p>
            )}
          </section>
        )
      )}

      {timeline ? (
        <VideoPlayer timeline={timeline} videoSrc={status?.video_ready ? videoUrl(id) : null} />
      ) : (
        !failed && !awaiting && <div className="stage waiting">视频生成中</div>
      )}

      {solution && <SolutionPanel solution={solution} />}
    </main>
  );
}
