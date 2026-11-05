"use client";

import { useRouter } from "next/navigation";
import { type ClipboardEvent, type FormEvent, useEffect, useRef, useState } from "react";
import { fetchWorkerOnline, submitProblem } from "@/lib/api";
import { imageToBase64 } from "@/lib/image";

const MAX_TEXT = 3000;

export default function ProblemForm({ initialText = "" }: { initialText?: string }) {
  const router = useRouter();
  const [text, setText] = useState(initialText);
  const [invite, setInvite] = useState("");
  const [workerOnline, setWorkerOnline] = useState<boolean | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void fetchWorkerOnline().then(setWorkerOnline);
  }, []);

  // 离开页面时释放预览图占用的内存
  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  function chooseFile(next: File | null) {
    setError(null);
    if (next && !next.type.startsWith("image/")) {
      setError("只能上传图片");
      return;
    }
    setFile(next);
    setPreview(next ? URL.createObjectURL(next) : null);
  }

  function clearFile() {
    chooseFile(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  function onPaste(event: ClipboardEvent) {
    const image = Array.from(event.clipboardData.files).find((item) => item.type.startsWith("image/"));
    if (image) chooseFile(image);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim() && !file) {
      setError("请输入题目或上传图片");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const imageBase64 = file ? await imageToBase64(file) : "";
      const job = await submitProblem(text.trim(), imageBase64, invite.trim());
      router.push(`/jobs/${job.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "提交失败");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} onPaste={onPaste} className="card">
      <label htmlFor="problem-text">题目文字</label>
      <textarea
        id="problem-text"
        rows={6}
        maxLength={MAX_TEXT}
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="输入一道初中物理题。上传图片时，这里可以留空，也可以补充说明。"
      />

      <label htmlFor="problem-image">题目图片（可以直接粘贴截图）</label>
      <input
        id="problem-image"
        ref={fileInput}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
      />
      {preview && (
        <div className="preview">
          {/* eslint-disable-next-line @next/next/no-img-element -- 本地预览图，不经过图片优化 */}
          <img src={preview} alt="题目图片预览" />
          <button type="button" onClick={clearFile}>
            移除图片
          </button>
        </div>
      )}

      <label htmlFor="invite">邀请码</label>
      <input id="invite" value={invite} onChange={(event) => setInvite(event.target.value)} autoComplete="off" />

      {workerOnline === false && (
        <p className="note">生成服务暂时离线，可以先提交，上线后会自动开始。</p>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <button type="submit" className="primary" disabled={submitting}>
        {submitting ? "提交中…" : "生成讲解视频"}
      </button>
      <p className="note">一道题通常需要 3 到 5 分钟。图片题读完后要你核对一次。文字解析会先出来，视频随后生成。</p>
    </form>
  );
}
