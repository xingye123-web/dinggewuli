/** 任务状态，对应后端的 status.json。 */
export interface JobStatus {
  id: string;
  status: string;
  stage?: string;
  errors?: unknown[];
  problem_text?: string;
  figure?: string;
  attempt?: number;
  narration_done?: number;
  narration_total?: number;
  solution_ready?: boolean;
  timeline_ready?: boolean;
  video_ready?: boolean;
  total_seconds?: number;
  /** 图片题上传了几张图。 */
  image_count?: number;
  /** 已经完成的每一步用了多少秒，键是 status 的名字。 */
  stage_seconds?: Record<string, number>;
  /** 渲染时的进度，比如 { stage: "rendering", done: 2, total: 4 }。 */
  progress?: { stage?: string; done?: number; total?: number } | null;
}

/** 模型独立解题的结果。内容来自模型，字段都可能缺失。 */
export interface Solution {
  topic?: string;
  knowns?: { name?: string; symbol?: string; value?: number | string; unit?: string }[];
  steps?: { title?: string; explain?: string; formula?: string }[];
  answers?: { label?: string; value?: number | string; unit?: string }[];
  pitfall?: string;
}

export interface Quantity {
  id: string;
  symbol: string;
  name: string;
  unit: string;
  digits: number;
}

/** 视频每一帧的数据。播放器按帧号取值，所以读数和画面始终一致。 */
export interface Timeline {
  text: string;
  assumptions: string[];
  fps: number;
  duration: number;
  clock: { id: string; label: string; unit: string };
  quantities: Quantity[];
  constants: Record<string, number>;
  formulas: { expr: string }[];
  phases: { label: string; t0: number; t1: number }[];
  events: { t: number; label: string }[];
  steps: { t: number; title: string; text: string }[];
  answers: { id: string; label: string; value: number | null; unit: string }[];
  frames: Record<string, (number | null)[]>;
  objects: Record<string, { name: string; quantities: string[] }>;
  regions: Record<string, [number, number, number, number][]>;
}
