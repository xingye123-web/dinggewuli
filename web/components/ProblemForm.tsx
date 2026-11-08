"use client";

import { useRouter } from "next/navigation";
import { type ClipboardEvent, type FormEvent, useEffect, useState } from "react";
import { fetchWorkerOnline, submitProblem } from "@/lib/api";
import { imageToBase64 } from "@/lib/image";
import { ArrowIcon } from "./Icons";
import ImagePicker, { useImages } from "./ImagePicker";

const MAX_TEXT = 3000;
// 题目文字和题图常常不在一页上，允许分几张拍
const MAX_IMAGES = 4;

export default function ProblemForm({ initialText = "" }: { initialText?: string }) {
  const router = useRouter();
  const [text, setText] = useState(initialText);
  const [invite, setInvite] = useState("");
  const [workerOnline, setWorkerOnline] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const images = useImages(MAX_IMAGES);

  useEffect(() => {
    void fetchWorkerOnline().then(setWorkerOnline);
  }, []);

  function onPaste(event: ClipboardEvent) {
    const pasted = Array.from(event.clipboardData.files).filter((item) => item.type.startsWith("image/"));
    if (pasted.length) setError(images.add(pasted));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim() && !images.picked.length) {
      setError("请输入题目或上传图片");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const imagesBase64 = await Promise.all(images.picked.map(({ file }) => imageToBase64(file)));
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

      <ImagePicker
        images={images}
        max={MAX_IMAGES}
        hint={`也可以直接粘贴截图。题目和题图不在一起时，可以传 ${MAX_IMAGES} 张以内`}
        moreHint={`题目文字和题图分开拍的，都传上来，最多 ${MAX_IMAGES} 张`}
        onError={setError}
      />

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
