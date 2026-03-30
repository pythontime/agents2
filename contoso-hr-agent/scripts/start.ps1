# Contoso HR Agent — Start (Windows)
# Starts the file watcher, MCP Inspector (stdio), and the FastAPI engine in the foreground.
# The engine kills port 8080 automatically on startup.

Set-StrictMode -Version Latest

Write-Host "`n=== Starting Contoso HR Agent ===" -ForegroundColor Cyan
Write-Host "  Web UI: http://localhost:8080/chat.html" -ForegroundColor White
Write-Host "  API:    http://localhost:8080/api/" -ForegroundColor White
Write-Host "  Press Ctrl+C to stop`n" -ForegroundColor White

# Kill any leftover MCP Inspector proxy port (5173 / 6274)
foreach ($port in @(5173, 6274)) {
    $netstatOutput = netstat -ano 2>$null | Select-String ":$port"
    foreach ($line in $netstatOutput) {
        $parts = $line.ToString().Trim() -split '\s+'
        $procId = $parts[-1]
        if ($procId -match '^\d+$' -and $procId -ne '0') {
            Write-Host "  Killing PID $procId on port $port" -ForegroundColor Yellow
            try { Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue } catch {}
            taskkill /PID $procId /F 2>$null | Out-Null
        }
    }
}

# Start watcher as background job
$watcherJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    uv run hr-watcher
}
Write-Host "[watcher] Started (Job ID: $($watcherJob.Id))" -ForegroundColor Green

# Start MCP Inspector (stdio) as background job if npx is available
$mcpJob = $null
if (Get-Command npx -ErrorAction SilentlyContinue) {
    $mcpJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        npx @modelcontextprotocol/inspector uv run hr-mcp --stdio
    }
    Write-Host "[mcp-inspector] Started (Job ID: $($mcpJob.Id))" -ForegroundColor Green
} else {
    Write-Host "[mcp-inspector] Skipped — npx not found (install Node.js to enable)" -ForegroundColor Yellow
}

# Open browser after a short delay
Start-Job -ScriptBlock {
    Start-Sleep 3
    Start-Process "http://localhost:8080/chat.html"
} | Out-Null

# Start engine (foreground — blocks until Ctrl+C)
try {
    uv run hr-engine
} finally {
    Write-Host "`nStopping background jobs..." -ForegroundColor Yellow
    Stop-Job $watcherJob -ErrorAction SilentlyContinue
    Remove-Job $watcherJob -ErrorAction SilentlyContinue
    if ($mcpJob) {
        Stop-Job $mcpJob -ErrorAction SilentlyContinue
        Remove-Job $mcpJob -ErrorAction SilentlyContinue
    }
}
