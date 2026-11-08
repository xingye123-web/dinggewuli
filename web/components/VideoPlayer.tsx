"use client";

import { type CSSProperties, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { formatNumber } from "@/lib/format";
import type { Quantity, Timeline } from "@/lib/types";
import { DownloadIcon, ExitFullscreenIcon, FullscreenIcon, NextFrameIcon, PauseIcon, PlayIcon, PrevFrameIcon } from "./Icons";
import Markup from "./Markup";

const SNAP_FRAMES = 5; // 松手时离关键时刻这么近，就吸过去，读数正好是题目的值
const SLOT = /\{(\w+)\}/;
const STEP_BOUNDARY = 1e-3;

interface Props {
  timeline: Timeline;
  /** 视频还没生成时为 null，此时面板和讲解仍然可用。 */
  videoSrc: string | null;
  /** 视频没出来时画面位置显示的进度，比如「正在渲染视频 2 / 4 段」。 */
  pending?: string;
  /** 放在讲解原文右边的内容，也就是文字解析。 */
  solution?: ReactNode;
}

function clockText(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${(seconds - minutes * 60).toFixed(1).padStart(4, "0")}`;
}

function isTyping(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false;
  if (target.isContentEditable || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) return true;
  return target instanceof HTMLInputElement && target.type !== "range";
}

export default function VideoPlayer({ timeline, videoSrc, pending, solution }: Props) {
  const video = useRef<HTMLVideoElement>(null);
  const consoleBox = useRef<HTMLElement>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [frame, setFrame] = useState(0);
  const [paused, setPaused] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [tab, setTab] = useState<"values" | "formulas">("values");
  const lastFrame = Math.max(Math.round(timeline.duration * timeline.fps) - 1, 0);

  const quantityById = useMemo(
    () => new Map(timeline.quantities.map((quantity) => [quantity.id, quantity])),
    [timeline],
  );

  // 代入计算里只有会随画面变化的量标黄，F = 100 N 这种不变的量不标
  const changing = useMemo(() => {
    const ids = new Set<string>();
    for (const [id, values] of Object.entries(timeline.frames)) {
      if (values.some((value) => value !== values[0])) ids.add(id);
    }
    return ids;
  }, [timeline]);

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

  const togglePlay = useCallback(() => {
    const element = video.current;
    if (!element || !element.src) return;
    if (element.paused) {
      if (frame >= lastFrame) element.currentTime = 0;
      void element.play();
    } else {
      element.pause();
    }
  }, [frame, lastFrame]);

  // 全屏的是整个台面，不只是视频：暂停后还能点物体、拖进度条、看读数。
  // iPhone 的 Safari 不支持把普通元素全屏，只能退回到系统自带的视频全屏
  const toggleFullscreen = useCallback(() => {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
      return;
    }
    const box = consoleBox.current;
    if (box && document.fullscreenEnabled) {
      void box.requestFullscreen().catch(() => undefined);
      return;
    }
    const element = video.current as (HTMLVideoElement & { webkitEnterFullscreen?: () => void }) | null;
    element?.webkitEnterFullscreen?.();
  }, []);

  useEffect(() => {
    const sync = () => setFullscreen(!!consoleBox.current && document.fullscreenElement === consoleBox.current);
    document.addEventListener("fullscreenchange", sync);
    return () => document.removeEventListener("fullscreenchange", sync);
  }, []);

  // 空格播放或暂停，左右方向键逐帧，F 全屏。正在输入文字、或焦点在按钮上按空格时交给浏览器处理
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.ctrlKey || event.metaKey || event.altKey || isTyping(event.target)) return;
      const onControl = event.target instanceof HTMLButtonElement || event.target instanceof HTMLAnchorElement;
      const onSlider = event.target instanceof HTMLInputElement;
      if (event.key === " " && !onControl && !onSlider) {
        event.preventDefault();
        togglePlay();
      } else if ((event.key === "f" || event.key === "F") && !onControl) {
        event.preventDefault();
        toggleFullscreen();
      } else if ((event.key === "ArrowLeft" || event.key === "ArrowRight") && !onSlider) {
        event.preventDefault();
        seekFrame(frame + (event.key === "ArrowLeft" ? -1 : 1));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [frame, togglePlay, seekFrame, toggleFullscreen]);

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
  const showPaused = paused && !!videoSrc;
  const clockQuantity = quantityById.get(timeline.clock.id);
  const allIds = timeline.quantities.map((quantity) => quantity.id);
  const selectedIds = selected ? timeline.objects[selected].quantities.filter((id) => quantityById.has(id)) : [];
  const otherIds = allIds.filter((id) => !selectedIds.includes(id));

  function row(quantity: Quantity | undefined, highlight: boolean) {
    if (!quantity) return null;
    const value = format(quantity.id, frame);
    return (
      <div className={highlight ? "q sel" : "q"} key={quantity.id}>
        <span className="sym">
          <Markup text={quantity.symbol} />
        </span>
        <span className="name">{quantity.name}</span>
        <span className="val">
          <Markup text={value} />
          {value !== "—" && <small>{quantity.unit}</small>}
        </span>
      </div>
    );
  }

  return (
    <>
      <section className={fullscreen ? "console is-fullscreen" : "console"} ref={consoleBox}>
        <div className="console-main">
          <div className="console-bar">
            {videoSrc &&
              (showPaused ? (
                <span className="paused">
                  <PauseIcon />
                  已定格
                </span>
              ) : (
                <span className="playing">
                  <PlayIcon />
                  播放中
                </span>
              ))}
            <span className="mono frame-no">第 {frame} 帧</span>
            <span className="clock">
              {timeline.clock.label}
              <b>
                <Markup text={clockQuantity?.symbol ?? timeline.clock.id} /> = <Markup text={format(timeline.clock.id, frame)} />{" "}
                {timeline.clock.unit}
              </b>
            </span>
          </div>

          <div className="stage" onClick={videoSrc ? onStageClick : undefined}>
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
              <div className="stage-waiting">
                <b>{pending ?? "视频生成中"}</b>
                <span>右边的物理量和下面的讲解已经可以看了，拖动进度条也能读数。</span>
              </div>
            )}
            {showPaused &&
              clickable.map((id) => {
                const [x, y, width, height] = timeline.regions[id][frame];
                const name = timeline.objects[id].name;
                return (
                  <button
                    key={id}
                    type="button"
                    className={id === selected ? "hitbox vf selected" : "hitbox vf"}
                    aria-label={`查看${name}的物理量`}
                    aria-pressed={id === selected}
                    style={{ left: `${x}%`, top: `${y}%`, width: `${width}%`, height: `${height}%` }}
                    onClick={(event) => {
                      event.stopPropagation();
                      setSelected(id === selected ? null : id);
                      setTab("values");
                    }}
                  >
                    <span className="tag">{name}</span>
                  </button>
                );
              })}
          </div>

          <div className="track">
            <div className="phase-labels" aria-hidden="true">
              {timeline.phases.map((phase) => (
                <span
                  key={`${phase.label}-${phase.t0}`}
                  className={phase.t0 <= seconds && seconds < phase.t1 ? "now" : ""}
                  style={{ flexGrow: phase.t1 - phase.t0, flexBasis: 0 }}
                >
                  {phase.label}
                </span>
              ))}
            </div>
            <div className="phase-bar" aria-hidden="true">
              {timeline.phases.map((phase) => {
                const share = phase.t1 > phase.t0 ? (seconds - phase.t0) / (phase.t1 - phase.t0) : 0;
                const fill = `${Math.min(Math.max(share, 0), 1) * 100}%`;
                return (
                  <span
                    key={`${phase.label}-${phase.t0}`}
                    style={{ flexGrow: phase.t1 - phase.t0, flexBasis: 0, "--p": fill } as CSSProperties}
                  />
                );
              })}
            </div>
            {timeline.events.map((event) => (
              <span
                key={`${event.label}-${event.t}`}
                className="event-tick"
                style={{ left: `${(event.t / timeline.duration) * 100}%` }}
              />
            ))}
            <input
              className="scrubber"
              type="range"
              aria-label="视频进度，按帧拖动"
              aria-valuetext={`${clockText(seconds)}，第 ${frame} 帧`}
              min={0}
              max={lastFrame}
              value={frame}
              onChange={(event) => seekFrame(Number(event.target.value))}
              onPointerUp={(event) => onSeekRelease(Number(event.currentTarget.value))}
            />
            <span className="playhead" style={{ left: `${(frame / Math.max(lastFrame, 1)) * 100}%` }} />
          </div>

          <div className="controls">
            <button type="button" className="ctl play" onClick={togglePlay} disabled={!videoSrc} aria-label={paused ? "播放" : "暂停"}>
              {paused ? <PlayIcon /> : <PauseIcon />}
            </button>
            <button type="button" className="ctl" onClick={() => seekFrame(frame - 1)} aria-label="上一帧">
              <PrevFrameIcon />
            </button>
            <button type="button" className="ctl" onClick={() => seekFrame(frame + 1)} aria-label="下一帧">
              <NextFrameIcon />
            </button>
            <span className="time mono">
              {clockText(seconds)} / {clockText(timeline.duration)}
            </span>
            {timeline.events.map((event) => {
              const index = Math.round(event.t * timeline.fps);
              return (
                <button
                  type="button"
                  key={`${event.label}-${event.t}`}
                  className={index === frame ? "moment on" : "moment"}
                  onClick={() => seekFrame(index)}
                >
                  {event.label}
                </button>
              );
            })}
            <span className="right">
              <span>
                <kbd>空格</kbd> 播放 <kbd>←</kbd>
                <kbd>→</kbd> 逐帧 <kbd>F</kbd> 全屏
              </span>
              {videoSrc && (
                <a href={videoSrc} download="定格物理讲解.mp4">
                  <DownloadIcon />
                  下载
                </a>
              )}
            </span>
            <button
              type="button"
              className="ctl fs"
              onClick={toggleFullscreen}
              aria-label={fullscreen ? "退出全屏" : "全屏"}
              title={fullscreen ? "退出全屏（F）" : "全屏（F）"}
            >
              {fullscreen ? <ExitFullscreenIcon /> : <FullscreenIcon />}
            </button>
          </div>
        </div>

        <aside className="readout">
          <div className="tabs" role="tablist">
            <button type="button" role="tab" aria-selected={tab === "values"} onClick={() => setTab("values")}>
              此刻的物理量
            </button>
            {timeline.formulas.length > 0 && (
              <button type="button" role="tab" aria-selected={tab === "formulas"} onClick={() => setTab("formulas")}>
                代入计算
              </button>
            )}
          </div>

          {tab === "values" ? (
            <div className="panel" role="tabpanel">
              {selected ? (
                <>
                  <div className="group sel">
                    {timeline.objects[selected].name}
                    <button type="button" onClick={() => setSelected(null)}>
                      × 看全部
                    </button>
                  </div>
                  {selectedIds.map((id) => row(quantityById.get(id), true))}
                  {otherIds.length > 0 && (
                    <div className="others">
                      <div className="group">其他物理量</div>
                      {otherIds.map((id) => row(quantityById.get(id), false))}
                    </div>
                  )}
                </>
              ) : (
                allIds.map((id) => row(quantityById.get(id), false))
              )}
            </div>
          ) : (
            <div className="panel" role="tabpanel">
              {timeline.formulas.map(({ expr }) => (
                <p className="formula" key={expr}>
                  {expr.split(SLOT).map((piece, index) =>
                    index % 2 === 0 ? (
                      <Markup key={index} text={piece} />
                    ) : (
                      <span key={index} className={changing.has(piece) ? "live" : ""}>
                        <Markup text={format(piece, frame)} />
                      </span>
                    ),
                  )}
                </p>
              ))}
            </div>
          )}
          <div className="panel-foot">
            {tab === "values"
              ? "暂停时点画面里框住的物体，它的物理量会排到最上面。"
              : "黄色数字是这一帧的值，会随画面变化。"}
          </div>
        </aside>
      </section>

      <section className={solution ? "below" : "below single"}>
        <div className="card">
          <h2>讲解</h2>
          <ol className="transcript">
            {timeline.steps.map((step, index) => (
              <li key={`${step.t}-${index}`}>
                <button
                  type="button"
                  className={index === activeStep ? "now" : ""}
                  onClick={() => seekFrame(Math.round(step.t * timeline.fps))}
                >
                  <time>{clockText(step.t).replace(/\.\d$/, "")}</time>
                  <span>
                    <span className="ph">{step.title}</span>
                    {step.text}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </div>
        {solution}
      </section>
    </>
  );
}
