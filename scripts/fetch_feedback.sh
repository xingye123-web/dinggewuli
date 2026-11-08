#!/usr/bin/env bash
# 把网站上收到的反馈（文字和截图）下载到本机 .dev/feedback，并列出每一条。只读，不删服务器上的记录。
# 用法：bash scripts/fetch_feedback.sh
set -euo pipefail

SERVER="${SERVER:-ubuntu@43.132.151.127}"
KEY="${KEY:-$HOME/.ssh/dingge_server}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/.dev/feedback"
mkdir -p "$OUT"

ssh -i "$KEY" -o BatchMode=yes "$SERVER" \
  "sudo test -d /var/lib/dingge/artifacts/_feedback && sudo tar -czf - -C /var/lib/dingge/artifacts/_feedback . || true" \
  | tar -xzf - -C "$OUT" 2>/dev/null || true

PYTHONIOENCODING=utf-8 python - "$OUT" <<'EOF'
import json, sys
from pathlib import Path
root = Path(sys.argv[1])
items = sorted(p for p in root.iterdir() if (p / "feedback.json").exists())
print(f"共 {len(items)} 条反馈，存在 {root}")
for path in items:
    record = json.loads((path / "feedback.json").read_text(encoding="utf-8"))
    extra = []
    if record.get("images"):
        extra.append(f"{len(record['images'])} 张图")
    if record.get("page") and record["page"] != "/":
        extra.append(f"来自 {record['page']}")
    if record.get("contact"):
        extra.append(f"联系方式 {record['contact']}")
    print(f"\n[{path.name}] {'，'.join(extra)}")
    print("  " + record["text"].replace("\n", "\n  "))
EOF
