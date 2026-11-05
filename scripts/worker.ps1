# 比赛期间在笔记本上运行：向服务器领任务，生成讲解视频后传回去。
# 用法：先在 .dev\prod_worker_token.txt 放好和服务器一致的令牌（服务器的 /etc/dingge/api.env），然后运行这个脚本，窗口保持打开。
$root = Split-Path $PSScriptRoot -Parent
$tokenFile = Join-Path $root '.dev\prod_worker_token.txt'
if (-not (Test-Path $tokenFile)) { throw "缺少 $tokenFile" }
$env:Path = "$env:Path;C:\Program Files\Docker\Docker\resources\bin"
$env:WORKER_TOKEN = (Get-Content $tokenFile -Raw).Trim()
$env:HUB_URL = 'https://dinggell.cn/worker-api'
$env:ARTIFACTS_DIR = Join-Path $root '.dev\work'
$env:RENDER_RUNNER = 'docker'
$env:PYTHONIOENCODING = 'utf-8'
# 生成视频时不让电脑睡眠，脚本结束后恢复
Add-Type -Namespace Power -Name Sleep -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags);'
[Power.Sleep]::SetThreadExecutionState([uint32]2147483649) | Out-Null
try { & (Join-Path $root '.venv\Scripts\python.exe') -m service.laptop_worker }
finally { [Power.Sleep]::SetThreadExecutionState([uint32]2147483648) | Out-Null }