import Link from "next/link";
import { PauseIcon } from "./Icons";
import ServiceStatus from "./ServiceStatus";

/** 顶栏。首页显示页内导航，讲解页显示返回首页的链接。 */
export default function TopBar({ page, hasExamples = false }: { page: "home" | "job"; hasExamples?: boolean }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <Link className="brand" href="/">
          <span className="brand-mark vf">
            <PauseIcon />
          </span>
          定格物理
        </Link>
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
        <ServiceStatus />
      </div>
    </header>
  );
}
