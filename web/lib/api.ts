import type { JobStatus, Solution, StepImage, Timeline } from "./types";

const jobUrl = (id: string) => `/backend/renders/${id}`;

export const videoUrl = (id: string) => `${jobUrl(id)}/video.mp4`;

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`请求失败（${response.status}）`);
  return response.json() as Promise<T>;
}

export const fetchStatus = (id: string) => getJson<JobStatus>(jobUrl(id));
export const fetchSolution = (id: string) => getJson<Solution>(`${jobUrl(id)}/solution.json`);
export const fetchTimeline = (id: string) => getJson<Timeline>(`${jobUrl(id)}/timeline.json`);

/** 第 index 张题目图片，从 0 开始。 */
export const fetchSteps = (id: string) => getJson<StepImage[]>(`${jobUrl(id)}/steps.json`);
export const stepImageUrl = (id: string, step: number) => `${jobUrl(id)}/step/${step}.jpg`;

export const imageUrl = (id: string, index = 0) => `${jobUrl(id)}/images/${index}`;

export const submitProblem = (text: string, imagesBase64: string[], invite: string) =>
  post("/api/problems", { text, images_base64: imagesBase64, invite });

/** 笔记本最近来领过任务，才能生成新题。 */
export async function fetchWorkerOnline(): Promise<boolean> {
  try {
    const health = await getJson<{ worker_online?: boolean }>("/backend/healthz");
    return !!health.worker_online;
  } catch {
    return false;
  }
}

export const submitFeedback = (feedback: { text: string; contact: string; page: string; images_base64: string[] }) =>
  post("/api/feedback", feedback);

export const confirmProblem = (id: string, text: string, figure: string) =>
  post(`/api/problems/${id}/confirm`, { text, figure });

async function post(url: string, payload: unknown): Promise<JobStatus> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : `提交失败（${response.status}）`;
    throw new Error(detail);
  }
  return body as JobStatus;
}
