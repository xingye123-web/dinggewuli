# 在本机启动全部服务，只监听 127.0.0.1，别的设备访问不到。
# 和线上一样分成两部分：接口和网页模拟服务器，laptop_worker 模拟笔记本来领任务，代码在 Docker 容器里运行。
$root = Split-Path $PSScriptRoot -Parent
$dev = Join-Path $root '.dev'
New-Item -ItemType Directory -Force $dev | Out-Null
$python = Join-Path $root '.venv\Scripts\python.exe'
$env:Path = "$env:Path;C:\Program Files\Docker\Docker\resources\bin"

function Get-Token($name) {
    # 令牌每台机器生成一次，存在不提交的文件里
    $file = Join-Path $dev "$name.txt"
    if (-not (Test-Path $file)) { [guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N') | Set-Content $file -Encoding ascii }
    return (Get-Content $file -Raw).Trim()
}
$apiToken = Get-Token 'token'
$workerToken = Get-Token 'worker_token'
"API_URL=http://127.0.0.1:8000`nRENDER_API_TOKEN=$apiToken" | Set-Content (Join-Path $root 'web\.env.local') -Encoding ascii
$env:PYTHONIOENCODING = 'utf-8'
$env:WORKER_TOKEN = $workerToken

function Start-Hidden($name, $file, $arguments, $directory) {
    Start-Process -FilePath $file -ArgumentList $arguments -WorkingDirectory $directory -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $dev "$name.log") -RedirectStandardError (Join-Path $dev "$name.err.log")
}

# 模拟服务器：接口和网页
$env:ARTIFACTS_DIR = '.dev/artifacts'
$env:RENDER_API_TOKEN = $apiToken
Start-Hidden 'api' $python @('-m', 'uvicorn', 'service.api:app', '--host', '127.0.0.1', '--port', '8000') $root
$npm = (Get-Command npm.cmd).Source
Start-Hidden 'web' $npm @('run', 'dev', '--', '-H', '127.0.0.1', '-p', '3100') (Join-Path $root 'web')

# 模拟笔记本：工作目录和服务器分开，通过接口领任务
$env:ARTIFACTS_DIR = '.dev/work'
$env:HUB_URL = 'http://127.0.0.1:8000'
$env:RENDER_RUNNER = 'docker'
Start-Hidden 'worker' $python @('-m', 'service.laptop_worker') $root

Write-Output '已启动，打开 http://127.0.0.1:3100 。停止时运行 scripts\stop.ps1'