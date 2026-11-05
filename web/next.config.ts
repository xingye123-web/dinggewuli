import type { NextConfig } from "next";

const apiUrl = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // 查询状态和取结果不需要令牌，直接转发给渲染服务。提交题目走 app/api/problems，令牌只留在服务端
  async rewrites() {
    return [{ source: "/backend/renders/:path*", destination: `${apiUrl}/v1/renders/:path*` }];
  },
};

export default nextConfig;
