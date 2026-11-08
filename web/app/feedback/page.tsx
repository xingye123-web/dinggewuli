import FeedbackForm from "@/components/FeedbackForm";
import TopBar from "@/components/TopBar";

export const metadata = { title: "反馈建议 · 定格物理" };

// 只接受站内的讲解页地址，别的一律当作首页
const JOB_PAGE = /^\/jobs\/[0-9a-f]{32}$/;

export default async function FeedbackPage({ searchParams }: { searchParams: Promise<{ from?: string | string[] }> }) {
  const { from } = await searchParams;
  const page = typeof from === "string" && JOB_PAGE.test(from) ? from : "/";
  return (
    <>
      <TopBar page="job" />
      <main className="wrap feedback">
        <h1 className="feedback-title">反馈建议</h1>
        <p className="lede">题目读错了、答案不对、动画画得别扭，或者有想要的功能，都可以告诉我们。附上截图会更快定位问题。</p>
        <FeedbackForm page={page} />
      </main>
    </>
  );
}
