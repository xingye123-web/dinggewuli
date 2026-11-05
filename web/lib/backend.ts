const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

/** 转发提交请求并带上令牌，只在服务端运行。令牌不会发给浏览器。 */
export async function forwardPost(path: string, body: string): Promise<Response> {
  try {
    const response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${process.env.RENDER_API_TOKEN ?? ""}`,
      },
      body,
    });
    return new Response(await response.text(), {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch {
    return Response.json({ detail: "渲染服务没有启动" }, { status: 503 });
  }
}
