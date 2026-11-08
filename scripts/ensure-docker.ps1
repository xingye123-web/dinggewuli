# 确保 Docker 在运行：引擎没响应就启动 Docker Desktop，并等它就绪，最多等 WaitSeconds 秒。
# worker-service.ps1 在登录时调用一次，之后每 2 分钟再查一次，所以开机和 Docker 中途退出都能自动拉起。
# 日志在 .dev\docker-watch.log。返回 0 表示引擎可用。
param([int]$WaitSeconds = 180)

$docker = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
$desktop = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
$log = Join-Path (Split-Path $PSScriptRoot -Parent) '.dev\docker-watch.log'

function Write-Log([string]$message) {
    try { Add-Content -Path $log -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $message" -Encoding utf8 } catch {}
}

function Test-Engine {
    & $docker version --format '{{.Server.Version}}' 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

if (Test-Engine) { exit 0 }

# Docker Desktop 已经在启动时只等着，不重复打开
if (Get-Process 'Docker Desktop' -ErrorAction SilentlyContinue) {
    Write-Log 'engine not responding, Docker Desktop is running, waiting'
} else {
    Write-Log 'engine not responding, starting Docker Desktop'
    Start-Process -FilePath $desktop
}

$deadline = (Get-Date).AddSeconds($WaitSeconds)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    if (Test-Engine) {
        Write-Log 'engine ready'
        exit 0
    }
}
Write-Log "engine still not ready after $WaitSeconds s"
exit 1
