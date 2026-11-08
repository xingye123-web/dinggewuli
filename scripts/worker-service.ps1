# dingge worker supervisor
# Single instance -> wait for Docker -> run laptop_worker -> restart on exit.
# Started by scheduled task "dingge-worker" at logon. Logs to .dev\worker-service.log
$ErrorActionPreference = 'Continue'
$root = Split-Path $PSScriptRoot -Parent
$log = Join-Path $root '.dev\worker-service.log'
$errLog = Join-Path $root '.dev\worker-service.err.log'
$tokenFile = Join-Path $root '.dev\prod_worker_token.txt'

function Write-Log([string]$message) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $message"
    try { Add-Content -Path $log -Value $line -Encoding utf8 } catch {}
}

try {
    $mutex = New-Object System.Threading.Mutex($false, 'dingge-worker-lock')
    $acquired = $false
    try {
        $acquired = $mutex.WaitOne(0)
    } catch [System.Threading.AbandonedMutexException] {
        $acquired = $true
    }
    if (-not $acquired) {
        Write-Log 'another wrapper is already running, exit'
        exit 0
    }

    Set-Location $root
    $env:Path = "$env:Path;C:\Program Files\Docker\Docker\resources\bin"
    if (Test-Path $tokenFile) {
        $env:WORKER_TOKEN = (Get-Content $tokenFile -Raw).Trim()
    }
    $env:HUB_URL = 'https://dinggell.cn/worker-api'
    $env:ARTIFACTS_DIR = Join-Path $root '.dev\work'
    $env:RENDER_RUNNER = 'docker'
    $env:PYTHONIOENCODING = 'utf-8'

    try {
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        $OutputEncoding = [System.Text.Encoding]::UTF8
    } catch {}

    Write-Log "wrapper start (pid $PID)"

    # Start Docker Desktop if the engine is down (its own auto-start is off); wait up to 3 min
    $ensureDocker = Join-Path $PSScriptRoot 'ensure-docker.ps1'
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ensureDocker -WaitSeconds 180
    if ($LASTEXITCODE -eq 0) { Write-Log 'docker ready' } else { Write-Log 'docker not ready after 3min, continue anyway' }

    # Re-check every 2 min so Docker is brought back if it quits; the job ends with this script
    Start-Job -Name 'dingge-docker-watch' -ArgumentList $ensureDocker -ScriptBlock {
        param($script)
        while ($true) {
            Start-Sleep -Seconds 120
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -WaitSeconds 170 | Out-Null
        }
    } | Out-Null

    Add-Type -Namespace Power -Name Sleep -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags);'
    [Power.Sleep]::SetThreadExecutionState([uint32]2147483649) | Out-Null

    while ($true) {
        Write-Log 'worker start'
        & (Join-Path $root '.venv\Scripts\python.exe') -m service.laptop_worker 2>&1 |
            ForEach-Object { Add-Content -Path $log -Value $_ -Encoding utf8 }
        Write-Log "worker exited (code $LASTEXITCODE), restart in 10s"
        Start-Sleep -Seconds 10
    }
} catch {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') FATAL: $($_.Exception.Message) $($_.ScriptStackTrace)" |
        Add-Content -Path $errLog -Encoding utf8
    throw
}
