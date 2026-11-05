import { forwardPost } from "@/lib/backend";

const JOB_ID = /^[0-9a-f]{32}$/;

export async function POST(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!JOB_ID.test(id)) return Response.json({ detail: "无效的任务" }, { status: 404 });
  return forwardPost(`/v1/problems/${id}/confirm`, await request.text());
}
