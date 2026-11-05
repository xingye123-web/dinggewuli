import ProblemForm from "@/components/ProblemForm";

export default async function HomePage({ searchParams }: { searchParams: Promise<{ text?: string | string[] }> }) {
  const { text } = await searchParams;
  return (
    <main className="narrow">
      <h1>定格物理</h1>
      <p>输入一道初中物理题或上传图片，生成可以随时暂停、查看物理量的讲解视频。</p>
      <ProblemForm initialText={typeof text === "string" ? text : ""} />
    </main>
  );
}
