"""在服务器上统计网站的使用情况，由 scripts/usage.sh 通过 SSH 运行，只读不写。

两类记录：
- 任务记录：每提交一道题，/var/lib/dingge/artifacts 下就多一个任务。
- 接口日志：有人打开讲解页，浏览器每 2 秒查一次进度，uvicorn 把请求记在 systemd 日志里。
首页的访问没有记录，Caddy 没开访问日志。
访客 IP 只显示前两段。
"""

import collections
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ARTIFACTS = Path("/var/lib/dingge/artifacts")
EXAMPLES = {
    "734a37a1bb4c64d3f0ef390aff702b65",
    "2a6ee8ace474374e0d6e7a6f9c1a4a0c",
    "8df85433a658c167a197ce5985b6b6cd",
    "ea9c65e237de622cc1cc9570dd1eb362",
}
BEIJING = datetime.timezone(datetime.timedelta(hours=8))
LOG_LINE = re.compile(r'^(\S+) .*INFO:\s+([\d.]+):\d+ - "(\w+) (\S+)')


def mask(ip):
    return ".".join(ip.split(".")[:2]) + ".*.*"


def jobs(since):
    rows = []
    for directory in ARTIFACTS.iterdir():
        status_file = directory / "status.json"
        if not status_file.exists() or directory.name in EXAMPLES:
            continue
        status = json.loads(status_file.read_text(encoding="utf-8"))
        created = datetime.datetime.fromtimestamp(status.get("created_at", 0), BEIJING)
        if created < since:
            continue
        problem_file = directory / "problem.json"
        problem = json.loads(problem_file.read_text(encoding="utf-8")) if problem_file.exists() else {}
        kind = "图片" if problem.get("image") else "文字" if problem_file.exists() else "代码"
        text = (status.get("problem_text") or problem.get("text") or "").replace("\n", " ")
        rows.append((created, directory.name, kind, status.get("status"), status.get("total_seconds"), text))
    return sorted(rows)


def visitors(days):
    log = subprocess.run(
        ["journalctl", "-u", "dingge-api", "--since", f"-{days} days", "--no-pager", "-o", "short-iso"],
        capture_output=True, text=True,
    ).stdout
    worker_ips, first_seen, pages = set(), {}, collections.defaultdict(set)
    for line in log.splitlines():
        match = LOG_LINE.match(line)
        if not match:
            continue
        time, ip, _method, path = match.groups()
        if path.startswith("/v1/worker"):
            worker_ips.add(ip)
            continue
        job = re.match(r"/v1/renders/([0-9a-f]{32})", path)
        if job and not ip.startswith("127."):
            first_seen.setdefault(ip, time[:16].replace("T", " "))
            pages[ip].add(job.group(1))
    return worker_ips, first_seen, pages


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    since = datetime.datetime.now(BEIJING) - datetime.timedelta(days=days)

    rows = jobs(since)
    print(f"== 最近 {days} 天提交的题目：{len(rows)} 道（不含首页例题）")
    per_day = collections.Counter(created.strftime("%m-%d") for created, *_ in rows)
    print("   每天：" + "，".join(f"{day} {count} 道" for day, count in sorted(per_day.items())) if per_day else "   没有")
    for created, job_id, kind, status, seconds, text in rows:
        took = f"{seconds:.0f}s" if seconds else "-"
        print(f"   {created:%m-%d %H:%M}  {job_id[:6]}  {kind}  {status:<9} {took:>5}  {text[:32]}")

    worker_ips, first_seen, pages = visitors(days)
    print(f"\n== 最近 {days} 天打开过讲解页的网络：{len(first_seen)} 个")
    print("   标「笔记本」的和 worker 在同一个网络，多半是你自己")
    for ip in sorted(first_seen, key=first_seen.get):
        own = "  笔记本" if ip in worker_ips else ""
        examples = len(pages[ip] & EXAMPLES)
        print(f"   {first_seen[ip]}  {mask(ip):<14} 看过 {len(pages[ip])} 个讲解页，其中例题 {examples} 个{own}")


if __name__ == "__main__":
    main()
