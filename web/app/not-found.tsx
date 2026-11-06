import Link from "next/link";
import TopBar from "@/components/TopBar";

export default function NotFound() {
  return (
    <>
      <TopBar page="job" />
      <main className="wrap missing">
        <h1>页面不存在</h1>
        <p>链接可能写错了。</p>
        <Link href="/">回到首页，输入一道题</Link>
      </main>
    </>
  );
}
