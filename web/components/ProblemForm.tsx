"use client";

import { useRouter } from "next/navigation";
import { type ClipboardEvent, type DragEvent, type FormEvent, useEffect, useRef, useState } from "react";
import { fetchWorkerOnline, submitProblem } from "@/lib/api";
import { imageToBase64 } from "@/lib/image";
import { ArrowIcon, CameraIcon } from "./Icons";

const MAX_TEXT = 3000;

export default function ProblemForm({ initialText = "" }: { initialText?: string }) {
  const router = useRouter();
  const [text, setText] = useState(initialText);
  const [invite, setInvite] = useState("");
  const [workerOnline, setWorkerOnline] = useState<boolean | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    void fetchWorkerOnline().then(setWorkerOnline);
  }, []);

  // 换图或离开页面时释放预览图占用的内存
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

  function onDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    const image = Array.from(event.dataTransfer.files).find((item) => item.type.startsWith("image/"));
    if (image) chooseFile(image);
    else if (event.dataTransfer.files.length) setError("只能上传图片");
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
    <form onSubmit={onSubmit} onPaste={onPaste} className="card ask">
      <label className="field-label" htmlFor="problem-text">
        题目
        <span className="mono">
          {text.length} / {MAX_TEXT}
        </span>
      </label>
      <textarea
        id="problem-text"
        rows={5}
        maxLength={MAX_TEXT}
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="例如：用滑轮组将重 240 N 的物体在 10 s 内匀速提升 2 m，绳子自由端的拉力为 100 N……"
      />

      {preview ? (
        <div className="preview">
          {/* eslint-disable-next-line @next/next/no-img-element -- 本地预览图，不经过图片优化 */}
          <img src={preview} alt="题目图片预览" />
          <span>{file?.name}</span>
          <button type="button" className="btn btn-quiet" onClick={clearFile}>
            移除图片
          </button>
        </div>
      ) : (
        <label
          className={dragging ? "drop vf over" : "drop vf"}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <CameraIcon />
          <div>
            <strong>
              拖入题目照片，或 <u>选择文件</u>
            </strong>
            <small>也可以直接粘贴截图。拍照时让文字和题图都在画面里</small>
          </div>
          <input
            ref={fileInput}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
          />
        </label>
      )}

      <div className="submit-row">
        <input
          aria-label="邀请码"
          placeholder="邀请码"
          value={invite}
          onChange={(event) => setInvite(event.target.value)}
          autoComplete="off"
        />
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "提交中…" : "生成讲解视频"}
          {!submitting && <ArrowIcon />}
        </button>
      </div>

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <p className="hint">
        {workerOnline === false
          ? "生成服务暂时离线，可以先提交，上线后会自动开始。"
          : "一道题通常要 3 到 5 分钟。文字解析先出来，视频随后生成。"}
      </p>
    </form>
  );
}
