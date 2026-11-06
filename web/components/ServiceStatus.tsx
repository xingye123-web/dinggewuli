"use client";

import { useEffect, useState } from "react";
import { fetchWorkerOnline } from "@/lib/api";

const CHECK_MS = 30000;

/** 顶栏右边的小牌子：笔记本最近来领过任务就是在线，否则提交的题会排队等它上线。 */
export default function ServiceStatus() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let stopped = false;
    const check = () => fetchWorkerOnline().then((next) => !stopped && setOnline(next));
    void check();
    const timer = setInterval(check, CHECK_MS);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, []);

  const text = online === null ? "正在连接" : online ? "生成服务在线" : "生成服务离线";
  return (
    <span className={`service ${online === null ? "" : online ? "on" : "off"}`} title={text} role="status">
      <i />
      {text}
    </span>
  );
}
