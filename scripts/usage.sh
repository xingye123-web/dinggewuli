#!/usr/bin/env bash
# 看网站有没有人在用：最近几天提交了哪些题、有哪些网络打开过讲解页。只读，不改服务器上的任何东西。
# 用法：bash scripts/usage.sh [天数，默认 7]
set -euo pipefail

SERVER="${SERVER:-ubuntu@43.132.151.127}"
KEY="${KEY:-$HOME/.ssh/dingge_server}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

ssh -i "$KEY" -o BatchMode=yes "$SERVER" "sudo python3 - ${1:-7}" < "$ROOT/scripts/usage_report.py"
