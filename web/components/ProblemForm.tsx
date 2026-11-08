"use client";

import { useRouter } from "next/navigation";
import { type ClipboardEvent, type DragEvent, type FormEvent, useEffect, useRef, useState } from "react";
import { fetchWorkerOnline, submitProblem } from "@/lib/api";
import { imageToBase64 } from "@/lib/image";
import { ArrowIcon, CameraIcon } from "./Icons";

const MAX_TEXT = 3000;
// 题目文字和题图常常不在一页上，允许分几张拍
const MAX_IMAGES = 4;

interface Picked {
  file: File;
  url: string;
}

export default function ProblemForm({ initialText = "" }: { initialText?: string }) {
  const router = useRouter();
  const [text, setText] = useState(initialText);
  const [invite, setInvite] = useState("");
  const [workerOnline, setWorkerOnline] = useState<boolean | null>(null);
  const [picked, setPicked] = useState<Picked[]>([]);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const urls = useRef<string[]>([]);

  useEffect(() => {
    void fetchWorkerOnline().then(setWorkerOnline);
  }, []);

  // 离开页面时释放预览图占用的内存
  useEffect(() => () => urls.current.forEach((url) => URL.revokeObjectURL(url)), []);

  function addFiles(files: File[]) {
    setError(null);
    const images = files.filter((file) => file.type.startsWith("image/"));
    if (images.length < files.length) setError("只能上传图片");
    const room = MAX_IMAGES - picked.length;
    if (images.length > room) setError(`一道题最多 ${MAX_IMAGES} 张图片`);
    const added = images.slice(0, Math.max(room, 0)).map((file) => {
      const url = URL.createObjectURL(file);
      urls.current.push(url);
      return { file, url };
    });
    if (added.length) setPicked((current) => [...current, ...added]);
    if (fileInput.current) fileInput.current.value = "";
  }

  function removeImage(index: number) {
    setError(null);
    setPicked((current) => {
      URL.revokeObjectURL(current[index].url);
      return current.filter((_, position) => position !== index);
    });
  }

  function onPaste(event: ClipboardEvent) {
    const images = Array.from(event.clipboardData.files).filter((item) => item.type.startsWith("image/"));
    if (images.length) addFiles(images);
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    addFiles(Array.from(event.dataTransfer.files));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim() && !picked.length) {
      setError("请输入题目或上传图片");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const imagesBase64 = await Promise.all(picked.map(({ file }) => imageToBase64(file)));
      const job = await submitProblem(text.trim(), imagesBase64, invite.trim());
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

      {picked.length > 0 && (
        <ul className="previews">
          {picked.map(({ file, url }, index) => (
            <li key={url}>
              {/* eslint-disable-next-line @next/next/no-img-element -- 本地预览图，不经过图片优化 */}
              <img src={url} alt={`第 ${index + 1} 张题目图片预览`} />
              <span className="mono">{index + 1}</span>
              <button type="button" onClick={() => removeImage(index)} aria-label={`移除第 ${index + 1} 张图片 ${file.name}`}>
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      {picked.length < MAX_IMAGES && (
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
              {picked.length ? "再加一张，" : "拖入题目照片，或 "}
              <u>选择文件</u>
            </strong>
            <small>
              {picked.length
                ? `题目文字和题图分开拍的，都传上来，最多 ${MAX_IMAGES} 张`
                : `也可以直接粘贴截图。题目和题图不在一起时，可以传 ${MAX_IMAGES} 张以内`}
            </small>
          </div>
          <input
            ref={fileInput}
            type="file"
            multiple
            accept="image/png,image/jpeg,image/webp"
            onChange={(event) => addFiles(Array.from(event.target.files ?? []))}
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
