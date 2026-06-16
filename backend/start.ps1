# 一键启动：启动服务 + 执行词根校验流水线
# 用法: .\start.ps1          (处理全部)
#       .\start.ps1 4,5,6    (处理指定ID)

$PORT = 8000
$API = "http://localhost:${PORT}/api/v1"

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "  词根校验流水线 - 一键启动" -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan

# 1. 清理旧进程和缓存
Write-Host "[1/4] 清理旧进程和缓存..." -ForegroundColor Yellow
$pids = (netstat -ano 2>$null | Select-String ":${PORT}.*LISTENING" | ForEach-Object { ($_ -split '\s+')[-1] } | Where-Object { $_ -match '^\d+$' })
foreach ($pid in $pids) {
    taskkill /F /PID $pid 2>$null
    Write-Host "  已停止 PID=$pid"
}
Get-ChildItem -Path "$PSScriptRoot\app" -Directory -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Write-Host "  完成"

# 2. 启动服务
Write-Host "[2/4] 启动 FastAPI 服务..." -ForegroundColor Yellow
$uvJob = Start-Job -ScriptBlock {
    param($dir, $port)
    Set-Location $dir
    uv run uvicorn app.main:app --host 0.0.0.0 --port $port 2>&1 | Out-Null
} -ArgumentList $PSScriptRoot, $PORT

# 等待服务就绪
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $null = Invoke-WebRequest -Uri "${API}/health" -UseBasicParsing -TimeoutSec 2
        $ready = $true
        break
    } catch { Start-Sleep 1 }
}
if (-not $ready) {
    Write-Host "  错误: 服务启动超时" -ForegroundColor Red
    exit 1
}
Write-Host "  服务已就绪"

# 3. 执行流水线
Write-Host "[3/4] 执行词根校验..." -ForegroundColor Yellow
if ($args.Count -gt 0) {
    $url = "${API}/root-word/process?root_word_ids=$($args[0])"
} else {
    $url = "${API}/root-word/process?limit=100"
}
$result = Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json"

# 4. 输出结果
Write-Host "[4/4] 结果:" -ForegroundColor Yellow
$result | ConvertTo-Json -Depth 5

Write-Host ""
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "  完成: 共 $($result.total) 条, 命中 $($result.matched), 未命中 $($result.unmatched)" -ForegroundColor Green
Write-Host "  服务运行中: http://localhost:${PORT}" -ForegroundColor Green
Write-Host "========================================"  -ForegroundColor Cyan
