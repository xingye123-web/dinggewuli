# 在本机启动全部服务，只监听 127.0.0.1，别的设备访问不到。
# 没有 Docker 时，模型写的代码没有容器隔离，所以只提交你自己的题目。
$root = Split-Path $PSScriptRoot -Parent
$dev = Join-Path $root '.dev'
New-Item -ItemType Directory -Force $dev | Out-Null
$python = Join-Path $root '.venv\Scripts\python.exe'

# 令牌每台机器生成一次，存在不提交的文件里
$tokenFile = Join-Path $dev 'token.txt'
if (-not (Test-Path $tokenFile)) { [guid]::NewGuid().ToString('N') | Set-Content $tokenFile -Encoding ascii }
$token = (Get-Content $tokenFile -Raw).Trim()
"API_URL=http://127.0.0.1:8000`nRENDER_API_TOKEN=$token" | Set-Content (Join-Path $root 'web\.env.local') -Encoding ascii

$env:CELERY_BROKER_URL = 'redis://127.0.0.1:6390/0'
$env:ARTIFACTS_DIR = '.dev/artifacts'
$env:RENDER_API_TOKEN = $token
$env:RENDER_RUNNER = 'local'
$env:ALLOW_UNSANDBOXED_RENDER = '1'
$env:PYTHONIOENCODING = 'utf-8'

function Start-Service-Hidden($name, $file, $arguments, $directory) {
    Start-Process -FilePath $file -ArgumentList $arguments -WorkingDirectory $directory -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $dev "$name.log") -RedirectStandardError (Join-Path $dev "$name.err.log")
}

# Redis 的本地替身，只用于开发。Docker 部署时用真正的 Redis
Start-Service-Hidden 'redis' $python @('-c', "`"from fakeredis import TcpFakeServer; TcpFakeServer(('127.0.0.1',6390),server_type='redis').serve_forever()`"") $root
Start-Sleep -Seconds 2
Start-Service-Hidden 'worker' $python @('-m', 'celery', '-A', 'service.tasks', 'worker', '--pool=solo', '--loglevel=info') $root
Start-Service-Hidden 'api' $python @('-m', 'uvicorn', 'service.api:app', '--host', '127.0.0.1', '--port', '8000') $root
$npm = (Get-Command npm.cmd).Source
Start-Service-Hidden 'web' $npm @('run', 'dev', '--', '-H', '127.0.0.1', '-p', '3100') (Join-Path $root 'web')

Write-Output '已启动，打开 http://127.0.0.1:3100 。停止时运行 scripts\stop.ps1'
