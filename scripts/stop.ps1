# 停止 dev.ps1 启动的全部服务。只匹配这个项目的进程
$patterns = '*service.laptop_worker*', '*service.api*', '*dingge-physics\web*', '*dingge-physics\render\entrypoint.py*'
Get-CimInstance Win32_Process |
    Where-Object { $command = $_.CommandLine; $command -and ($patterns | Where-Object { $command -like $_ }) -and $_.ProcessId -ne $PID } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        "已停止 $($_.Name) $($_.ProcessId)"
    }
