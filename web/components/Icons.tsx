/** 界面用到的小图标，都是线条或实心的简单图形，颜色跟随文字颜色。 */

export function PauseIcon() {
  return (
    <svg viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
      <rect x="1" y="0" width="3.5" height="12" rx="1" />
      <rect x="7.5" y="0" width="3.5" height="12" rx="1" />
    </svg>
  );
}

export function PlayIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M4 2.5v11l9-5.5z" />
    </svg>
  );
}

export function PrevFrameIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <rect x="2" y="3" width="2" height="10" rx="0.5" />
      <path d="M13 3v10L6 8z" />
    </svg>
  );
}

export function NextFrameIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <rect x="12" y="3" width="2" height="10" rx="0.5" />
      <path d="M3 3v10l7-5z" />
    </svg>
  );
}

export function DownloadIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M8 2v8M4.5 6.5 8 10l3.5-3.5M3 13.5h10" />
    </svg>
  );
}

export function ArrowIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 8h10M9 4l4 4-4 4" />
    </svg>
  );
}

export function CameraIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 8h3l1.6-2.4h6.8L17 8h3v11H4z" />
      <circle cx="12" cy="13" r="3.6" />
    </svg>
  );
}
