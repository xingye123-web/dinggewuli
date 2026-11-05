import type { NextConfig } from "next";

const apiUrl = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // 部署时只拷贝运行需要的文件，服务器上不用装全部依赖
  output: "standalone",
  // 查询状态和取结果不需要令牌，直接转发给后端。提交题目走 app/api/problems，令牌只留在服务端
  async rewrites() {
    return [
      { source: "/backend/renders/:path*", destination: `${apiUrl}/v1/renders/:path*` },
      { source: "/backend/healthz", destination: `${apiUrl}/healthz` },
    ];
  },
};

export default nextConfig;
