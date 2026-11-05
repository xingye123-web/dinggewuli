#!/usr/bin/env bash
# 把网页和接口部署到服务器。在开发机上运行：bash scripts/deploy.sh
set -euo pipefail

SERVER="${SERVER:-ubuntu@43.132.151.127}"
KEY="${KEY:-$HOME/.ssh/dingge_server}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$ROOT/.dev/bundle"
SSH=(ssh -i "$KEY" -o BatchMode=yes "$SERVER")

# 网页按服务器上的地址构建，standalone 模式只带运行需要的文件
(cd "$ROOT/web" && API_URL=http://127.0.0.1:8000 npm run build >/dev/null)

rm -rf "$STAGE" && mkdir -p "$STAGE/web/.next" "$STAGE/service" "$STAGE/render" "$STAGE/deploy"
cp -r "$ROOT/web/.next/standalone/." "$STAGE/web/"
cp -r "$ROOT/web/.next/static" "$STAGE/web/.next/static"
cp -r "$ROOT/web/public" "$STAGE/web/public"
rm -f "$STAGE/web/.env.local"
cp "$ROOT"/service/*.py "$ROOT/service/requirements-server.txt" "$STAGE/service/"
cp "$ROOT/render/__init__.py" "$ROOT/render/scene_check.py" "$ROOT/render/speech_text.py" "$STAGE/render/"
cp "$ROOT"/deploy/* "$STAGE/deploy/"
# Windows 上的换行符会让 systemd 和 bash 读错，统一成 Linux 换行
sed -i 's/\r$//' "$STAGE"/deploy/*

# 打包前确认没有把本机的令牌和密钥带上去
if grep -rqE "sk-[0-9a-f]{20,}|brz_[A-Za-z0-9_-]{20,}|RENDER_API_TOKEN=[0-9a-f]" "$STAGE"; then
  echo "部署包里有密钥，停止部署" >&2
  exit 1
fi

tar -czf "$ROOT/.dev/bundle.tgz" -C "$STAGE" .
scp -i "$KEY" -o BatchMode=yes -q "$ROOT/.dev/bundle.tgz" "$STAGE/deploy/remote_install.sh" "$SERVER:/tmp/"
"${SSH[@]}" "bash /tmp/remote_install.sh /tmp/bundle.tgz && rm -f /tmp/remote_install.sh"
