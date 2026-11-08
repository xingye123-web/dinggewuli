import Link from "next/link";
import { PauseIcon } from "./Icons";
import ServiceStatus from "./ServiceStatus";

/** 顶栏。首页显示页内导航，讲解页显示返回首页的链接。 */
interface Props {
  page: "home" | "job";
  hasExamples?: boolean;
  /** 从讲解页点反馈时带上这道题的地址。 */
  feedbackFrom?: string;
}

export default function TopBar({ page, hasExamples = false, feedbackFrom }: Props) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <Link className="brand" href="/">
          <span className="brand-mark vf">
            <PauseIcon />
          </span>
          <span className="brand-words">
            定格物理
            <small>PHYSICS, PAUSED</small>
          </span>
        </Link>
        <span className="topbar-divider" aria-hidden="true" />
        {page === "home" ? (
          <nav className="nav">
            {hasExamples && <a href="#examples">例题</a>}
            <a href="#how">怎么用</a>
          </nav>
        ) : (
          <Link className="back" href="/">
            ← 再问一道题
          </Link>
        )}
        <span className="spacer" />
        <Link className="feedback-link" href={feedbackFrom ? `/feedback?from=${encodeURIComponent(feedbackFrom)}` : "/feedback"}>
          反馈建议
        </Link>
        <ServiceStatus />
      </div>
    </header>
  );
}
