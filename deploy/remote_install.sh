#!/usr/bin/env bash
# 在服务器上执行：安装运行环境，部署新版本，重启服务。由 scripts/deploy.sh 上传后调用。
set -euo pipefail

BUNDLE="$1"
RELEASE="/opt/dingge/releases/$(date +%Y%m%d%H%M%S)"
NODE_MAJOR=22

# 运行服务的专用账户，没有登录权限
id dingge >/dev/null 2>&1 || sudo useradd --system --no-create-home --shell /usr/sbin/nologin dingge
sudo mkdir -p /opt/dingge/releases /var/lib/dingge/artifacts /etc/dingge
sudo chown -R dingge:dingge /var/lib/dingge

# Node.js：Next.js 16 需要 20.9 以上，从官网下载并校验
if ! /opt/node/bin/node --version 2>/dev/null | grep -q "^v${NODE_MAJOR}\."; then
  base="https://nodejs.org/dist/latest-v${NODE_MAJOR}.x"
  file=$(curl -fsSL "$base/SHASUMS256.txt" | awk '/linux-x64.tar.xz$/ {print $2}')
  expected=$(curl -fsSL "$base/SHASUMS256.txt" | awk '/linux-x64.tar.xz$/ {print $1}')
  curl -fsSL -o "/tmp/$file" "$base/$file"
  echo "$expected  /tmp/$file" | sha256sum -c -
  sudo rm -rf /opt/node && sudo mkdir -p /opt/node
  sudo tar -xJf "/tmp/$file" -C /opt/node --strip-components=1
  rm -f "/tmp/$file"
fi

# Python 环境：服务器只装接口需要的包
if [ ! -x /opt/dingge/venv/bin/python ]; then
  sudo apt-get update -qq && sudo apt-get install -y -qq python3-venv >/dev/null
  sudo python3 -m venv /opt/dingge/venv
fi

sudo mkdir -p "$RELEASE"
sudo tar --no-same-owner -xzf "$BUNDLE" -C "$RELEASE"
sudo /opt/dingge/venv/bin/pip install -q -r "$RELEASE/service/requirements-server.txt"

# 令牌和邀请码只在第一次生成，之后保持不变
if [ ! -f /etc/dingge/api.env ]; then
  api_token=$(openssl rand -hex 32)
  worker_token=$(openssl rand -hex 32)
  # 先取有限长度的随机字节再过滤，避免 tr 读无限流时被 head 截断触发 SIGPIPE
  invite=$(head -c 256 /dev/urandom | tr -dc 'A-HJ-NP-Z2-9' | cut -c1-6)
  printf 'ARTIFACTS_DIR=/var/lib/dingge/artifacts\nRENDER_API_TOKEN=%s\nWORKER_TOKEN=%s\nINVITE_CODES=%s\nMAX_JOBS_PER_DAY=30\nPYTHONIOENCODING=utf-8\n' \
    "$api_token" "$worker_token" "$invite" | sudo tee /etc/dingge/api.env >/dev/null
  printf 'API_URL=http://127.0.0.1:8000\nRENDER_API_TOKEN=%s\n' "$api_token" | sudo tee /etc/dingge/web.env >/dev/null
fi
sudo chown root:dingge /etc/dingge/*.env
sudo chmod 640 /etc/dingge/*.env

sudo ln -sfn "$RELEASE" /opt/dingge/current
sudo cp "$RELEASE/deploy/dingge-api.service" "$RELEASE/deploy/dingge-web.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dingge-api dingge-web >/dev/null 2>&1
sudo systemctl restart dingge-api dingge-web

sudo cp "$RELEASE/deploy/Caddyfile" /etc/caddy/Caddyfile
sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null
sudo systemctl reload caddy

# 只保留最近 3 个版本，按目录名排序（名字就是部署时间），解压出的文件时间不可靠
ls -1d /opt/dingge/releases/* | sort -r | tail -n +4 | xargs -r sudo rm -rf
rm -f "$BUNDLE"

for _ in $(seq 1 30); do
  curl -fs http://127.0.0.1:8000/healthz >/dev/null && curl -fs -o /dev/null http://127.0.0.1:3000/ && break
  sleep 1
done
echo "api: $(curl -s http://127.0.0.1:8000/healthz)"
echo "web: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/)"
