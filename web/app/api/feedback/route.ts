import { forwardPost } from "@/lib/backend";

export async function POST(request: Request) {
  return forwardPost("/v1/feedback", await request.text());
}
