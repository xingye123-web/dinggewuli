"use client";

import Link from "next/link";
import { type ClipboardEvent, type FormEvent, useState } from "react";
import { submitFeedback } from "@/lib/api";
import { imageToBase64 } from "@/lib/image";
import { ArrowIcon } from "./Icons";
import ImagePicker, { useImages } from "./ImagePicker";

const MAX_TEXT = 2000;
const MAX_IMAGES = 4;

/** 意见和问题反馈。page 是从哪里点进来的，比如某道题的讲解页，方便我们对照着看。 */
export default function FeedbackForm({ page }: { page: string }) {
  const [text, setText] = useState("");
  const [contact, setContact] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const images = useImages(MAX_IMAGES);

  function onPaste(event: ClipboardEvent) {
    const pasted = Array.from(event.clipboardData.files).filter((item) => item.type.startsWith("image/"));
    if (pasted.length) setError(images.add(pasted));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) {
      setError("请写下你的建议或遇到的问题");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const imagesBase64 = await Promise.all(images.picked.map(({ file }) => imageToBase64(file)));
      await submitFeedback({ text: text.trim(), contact: contact.trim(), page, images_base64: imagesBase64 });
      setSent(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "提交失败");
      setSubmitting(false);
    }
  }

  if (sent) {
    return (
      <div className="card ask sent">
        <h2>收到了，谢谢</h2>
        <p>我们会逐条看，用来改进讲解和动画。</p>
        <Link href={page.startsWith("/jobs/") ? page : "/"}>{page.startsWith("/jobs/") ? "回到这道题" : "回到首页"}</Link>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} onPaste={onPaste} className="card ask">
      {page.startsWith("/jobs/") && <p className="hint about">关于这道题：{page.replace("/jobs/", "")}</p>}
      <label className="field-label" htmlFor="feedback-text">
        建议或问题
        <span className="mono">
          {text.length} / {MAX_TEXT}
        </span>
      </label>
      <textarea
        id="feedback-text"
        rows={6}
        maxLength={MAX_TEXT}
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="比如：第 2 问的答案不对；动画里绳子画错了；希望能调节播放速度……"
      />

      <ImagePicker
        images={images}
        max={MAX_IMAGES}
        hint={`附上截图更容易看懂，可以直接粘贴，最多 ${MAX_IMAGES} 张`}
        moreHint={`最多 ${MAX_IMAGES} 张`}
        onError={setError}
      />

      <div className="submit-row">
        <input
          aria-label="联系方式（选填）"
          placeholder="联系方式（选填）"
          value={contact}
          maxLength={100}
          onChange={(event) => setContact(event.target.value)}
          autoComplete="off"
        />
        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "提交中…" : "提交反馈"}
          {!submitting && <ArrowIcon />}
        </button>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <p className="hint">联系方式只用于回复你的问题，不填也可以。</p>
    </form>
  );
}
