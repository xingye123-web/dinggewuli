import type { Metadata } from "next";
import type { ReactNode } from "react";
import SiteFooter from "@/components/SiteFooter";
import "./globals.css";

export const metadata: Metadata = {
  title: "定格物理",
  description: "输入初中物理题，生成可以暂停查看物理量的讲解视频",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        {children}
        <SiteFooter />
      </body>
    </html>
  );
}
