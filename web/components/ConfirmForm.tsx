"use client";

import { type FormEvent, useState } from "react";
import { confirmProblem, imageUrl } from "@/lib/api";

interface Props {
  id: string;
  initialText: string;
  initialFigure: string;
}

/** 读图可能读错，尤其是绳子段数和电路连接。用户对照原图改好后，才开始解题。 */
export default function ConfirmForm({ id, initialText, initialFigure }: Props) {
  const [text, setText] = useState(initialText);
  const [figure, setFigure] = useState(initialFigure);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) {
      setError("题目不能为空");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await confirmProblem(id, text, figure);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "提交失败");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="card">
      <h2>请核对读到的题目</h2>
      <p>图片可能读错，特别是题图里的绳子段数、拉力方向和电路连接。请对照原图，有错就直接改。</p>
      {/* eslint-disable-next-line @next/next/no-img-element -- 用户上传的原图，不经过图片优化 */}
      <img className="source-image" src={imageUrl(id)} alt="上传的题目图片" />
      <label htmlFor="confirm-text">题目文字</label>
      <textarea id="confirm-text" rows={5} value={text} onChange={(event) => setText(event.target.value)} />
      <label htmlFor="confirm-figure">题图信息</label>
      <textarea id="confirm-figure" rows={4} value={figure} onChange={(event) => setFigure(event.target.value)} />
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <button type="submit" className="primary" disabled={submitting}>
        {submitting ? "提交中…" : "确认无误，开始生成"}
      </button>
    </form>
  );
}
