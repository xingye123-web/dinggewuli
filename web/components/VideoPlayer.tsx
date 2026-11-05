"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { formatNumber } from "@/lib/format";
import type { Timeline } from "@/lib/types";
import Markup from "./Markup";

const SNAP_FRAMES = 5; // 松手时离关键时刻这么近，就吸过去，读数正好是题目的值
const SLOT = /\{(\w+)\}/g;
const STEP_BOUNDARY = 1e-3;

interface Props {
  timeline: Timeline;
  /** 视频还没生成时为 null，此时面板和讲解仍然可用。 */
  videoSrc: string | null;
}

export default function VideoPlayer({ timeline, videoSrc }: Props) {
  const video = useRef<HTMLVideoElement>(null);
  const [frame, setFrame] = useState(0);
  const [paused, setPaused] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const lastFrame = Math.round(timeline.duration * timeline.fps) - 1;

  const quantityById = useMemo(
    () => new Map(timeline.quantities.map((quantity) => [quantity.id, quantity])),
    [timeline],
  );

  // 大的先放，小的盖在上面，水里的物块才点得到
  const clickable = useMemo(() => {
    const area = (id: string) => timeline.regions[id][0][2] * timeline.regions[id][0][3];
    return Object.keys(timeline.objects).sort((a, b) => area(b) - area(a));
  }, [timeline]);

  const format = useCallback(
    (id: string, index: number) => {
      if (id in timeline.constants) return String(timeline.constants[id]);
      const value = timeline.frames[id]?.[index];
      const quantity = quantityById.get(id);
      if (value === null || value === undefined || !quantity) return "—";
      return formatNumber(value, quantity.digits);
    },
    [timeline, quantityById],
  );

  const frameOf = useCallback(
    (seconds: number) => Math.min(Math.max(Math.floor(seconds * timeline.fps + 1e-4), 0), lastFrame),
    [timeline.fps, lastFrame],
  );

  // 停在帧的中间，避免落在两帧的边界上
  const seekFrame = useCallback(
    (index: number) => {
      const element = video.current;
      const target = Math.min(Math.max(index, 0), lastFrame);
      if (element && element.src) {
        element.pause();
        element.currentTime = (target + 0.5) / timeline.fps;
      }
      setFrame(target);
    },
    [timeline.fps, lastFrame],
  );

  // 播放时按视频实际呈现的帧更新面板
  useEffect(() => {
    const element = video.current;
    if (!element || paused) return;
    let handle: number;
    const follow = (_now: number, metadata: VideoFrameCallbackMetadata) => {
      setFrame(frameOf(metadata.mediaTime));
      handle = element.requestVideoFrameCallback(follow);
    };
    handle = element.requestVideoFrameCallback(follow);
    return () => element.cancelVideoFrameCallback(handle);
  }, [paused, frameOf]);

  function togglePlay() {
    const element = video.current;
    if (!element || !element.src) return;
    if (element.paused) {
      if (frame >= lastFrame) element.currentTime = 0;
      void element.play();
    } else {
      element.pause();
    }
  }

  function onStageClick() {
    if (selected) setSelected(null);
    else togglePlay();
  }

  function onSeekRelease(value: number) {
    const nearest = timeline.events
      .map((event) => Math.round(event.t * timeline.fps))
      .find((index) => Math.abs(index - value) <= SNAP_FRAMES);
    if (nearest !== undefined) seekFrame(nearest);
  }

  const seconds = frame / timeline.fps;
  let activeStep = -1;
  timeline.steps.forEach((step, index) => {
    if (step.t <= seconds + STEP_BOUNDARY) activeStep = index;
  });
  const shownIds = selected
    ? timeline.objects[selected].quantities
    : timeline.quantities.map((quantity) => quantity.id);

  return (
    <div className="player">
      <div>
        <div className="stage" onClick={onStageClick}>
          {videoSrc ? (
            <video
              ref={video}
              src={videoSrc}
              preload="auto"
              playsInline
              onPlay={() => setPaused(false)}
              onPause={() => setPaused(true)}
              onEnded={() => setPaused(true)}
              onSeeked={(event) => setFrame(frameOf(event.currentTarget.currentTime))}
            />
          ) : (
            <div className="waiting">视频生成中，右边的物理量和讲解已经可以看了</div>
          )}
          {paused &&
            videoSrc &&
            clickable.map((id) => {
              const [x, y, width, height] = timeline.regions[id][frame];
              return (
                <button
                  key={id}
                  type="button"
                  className={id === selected ? "hit selected" : "hit"}
                  aria-label={`查看${timeline.objects[id].name}的物理量`}
                  style={{ left: `${x}%`, top: `${y}%`, width: `${width}%`, height: `${height}%` }}
                  onClick={(event) => {
                    event.stopPropagation();
                    setSelected(id === selected ? null : id);
                  }}
                />
              );
            })}
        </div>

        <div className="phases">
          {timeline.phases.map((phase) => (
            <span key={`${phase.label}-${phase.t0}`} style={{ flexGrow: phase.t1 - phase.t0 }}>
              {phase.label}
            </span>
          ))}
        </div>
        <input
          type="range"
          aria-label="视频进度"
          min={0}
          max={lastFrame}
          value={frame}
          onChange={(event) => seekFrame(Number(event.target.value))}
          onPointerUp={(event) => onSeekRelease(Number(event.currentTarget.value))}
        />

        <div className="controls">
          <button type="button" onClick={togglePlay} disabled={!videoSrc}>
            {paused ? "播放" : "暂停"}
          </button>
          <button type="button" onClick={() => seekFrame(frame - 1)}>
            上一帧
          </button>
          <button type="button" onClick={() => seekFrame(frame + 1)}>
            下一帧
          </button>
          <span>
            {timeline.clock.label} <Markup text={format(timeline.clock.id, frame)} /> {timeline.clock.unit}
          </span>
          {videoSrc && (
            <a href={videoSrc} download="定格物理讲解.mp4">
              下载视频
            </a>
          )}
        </div>

        {timeline.events.length > 0 && (
          <div className="controls">
            <span>关键时刻：</span>
            {timeline.events.map((event) => (
              <button
                type="button"
                key={`${event.label}-${event.t}`}
                onClick={() => seekFrame(Math.round(event.t * timeline.fps))}
              >
                {event.label}
              </button>
            ))}
          </div>
        )}
        <p className="note">暂停后，点画面里虚线框住的物体，可以只看它的物理量。</p>
      </div>

      <aside>
        <section className="card">
          <h2>{selected ? `${timeline.objects[selected].name}的物理量` : "此刻的物理量"}</h2>
          <table>
            <tbody>
              {shownIds.map((id) => {
                const quantity = quantityById.get(id);
                if (!quantity) return null;
                const value = format(id, frame);
                return (
                  <tr key={id}>
                    <th>
                      <Markup text={quantity.symbol} />
                    </th>
                    <td>{quantity.name}</td>
                    <td className="value">
                      <Markup text={value} /> {value === "—" ? "" : quantity.unit}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>

        {timeline.formulas.length > 0 && (
          <section className="card">
            <h2>代入计算</h2>
            {timeline.formulas.map(({ expr }) => (
              <p className="formula" key={expr}>
                <Markup text={expr.replace(SLOT, (_, id: string) => format(id, frame))} />
              </p>
            ))}
          </section>
        )}

        <section className="card">
          <h2>视频讲解</h2>
          <ol className="steps">
            {timeline.steps.map((step, index) => (
              <li key={`${step.t}-${index}`}>
                <button
                  type="button"
                  className={index === activeStep ? "active" : ""}
                  onClick={() => seekFrame(Math.round(step.t * timeline.fps))}
                >
                  <small>
                    {step.title} · {step.t.toFixed(0)} 秒
                  </small>
                  <br />
                  {step.text}
                </button>
              </li>
            ))}
          </ol>
        </section>
      </aside>
    </div>
  );
}
