"use client";

import { type DragEvent, useCallback, useEffect, useRef, useState } from "react";
import { CameraIcon } from "./Icons";

export interface PickedImage {
  file: File;
  url: string;
}

/**
 * 管理选中的图片：选择、拖入、粘贴都走 add，超过上限或不是图片时返回错误文字。
 * 预览图的内存在移除和离开页面时释放。
 */
export function useImages(max: number) {
  const [picked, setPicked] = useState<PickedImage[]>([]);
  const urls = useRef<string[]>([]);

  useEffect(() => () => urls.current.forEach((url) => URL.revokeObjectURL(url)), []);

  const add = useCallback(
    (files: File[]): string | null => {
      const images = files.filter((file) => file.type.startsWith("image/"));
      const room = max - picked.length;
      const added = images.slice(0, Math.max(room, 0)).map((file) => {
        const url = URL.createObjectURL(file);
        urls.current.push(url);
        return { file, url };
      });
      if (added.length) setPicked((current) => [...current, ...added]);
      if (images.length < files.length) return "只能上传图片";
      if (images.length > room) return `最多 ${max} 张图片`;
      return null;
    },
    [max, picked.length],
  );

  const remove = useCallback((index: number) => {
    setPicked((current) => {
      URL.revokeObjectURL(current[index].url);
      return current.filter((_, position) => position !== index);
    });
  }, []);

  return { picked, add, remove };
}

interface Props {
  images: ReturnType<typeof useImages>;
  max: number;
  /** 还没有图片时，拖放区的说明。 */
  hint: string;
  /** 已经有图片时，拖放区的说明。 */
  moreHint: string;
  onError: (message: string | null) => void;
}

/** 缩略图列表加拖放区。粘贴截图由外层的表单处理，同样调用 images.add。 */
export default function ImagePicker({ images, max, hint, moreHint, onError }: Props) {
  const [dragging, setDragging] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  function addFiles(files: File[]) {
    onError(images.add(files));
    if (input.current) input.current.value = "";
  }

  function onDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    addFiles(Array.from(event.dataTransfer.files));
  }

  return (
    <>
      {images.picked.length > 0 && (
        <ul className="previews">
          {images.picked.map(({ file, url }, index) => (
            <li key={url}>
              {/* eslint-disable-next-line @next/next/no-img-element -- 本地预览图，不经过图片优化 */}
              <img src={url} alt={`第 ${index + 1} 张图片预览`} />
              <span className="mono">{index + 1}</span>
              <button
                type="button"
                onClick={() => {
                  onError(null);
                  images.remove(index);
                }}
                aria-label={`移除第 ${index + 1} 张图片 ${file.name}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}

      {images.picked.length < max && (
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
              {images.picked.length ? "再加一张，" : "拖入图片，或 "}
              <u>选择文件</u>
            </strong>
            <small>{images.picked.length ? moreHint : hint}</small>
          </div>
          <input
            ref={input}
            type="file"
            multiple
            accept="image/png,image/jpeg,image/webp"
            onChange={(event) => addFiles(Array.from(event.target.files ?? []))}
          />
        </label>
      )}
    </>
  );
}
