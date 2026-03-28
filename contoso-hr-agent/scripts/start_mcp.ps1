# Contoso HR Agent — Start MCP Server + MCP Inspector (Windows)
# Force-kills port 8081 first (also done inside hr-mcp, but belt-and-suspenders).
# Opens MCP Inspector in the browser.

Set-StrictMode -Version Latest

Write-Host "`n=== Starting Contoso HR MCP Server ===" -ForegroundColor Cyan

# Belt-and-suspenders: kill port 8081 at script level too
Write-Host "Checking port 8081..." -ForegroundColor Yellow
$netstatOutput = netstat -ano 2>$null | Select-String ":8081"
foreach ($line in $netstatOutput) {
    $parts = $line.ToString().Trim() -split '\s+'
    $pid = $parts[-1]
    if ($pid -match '^\d+$' -and $pid -ne '0') {
        Write-Host "  Killing PID $pid on port 8081" -ForegroundColor Yellow
        taskkill /PID $pid /F 2>$null | Out-Null
    }
}
Start-Sleep -Milliseconds 500

# Start MCP server as background job
$mcpJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    uv run hr-mcp
}
Write-Host "[mcp-server] Started (Job ID: $($mcpJob.Id))" -ForegroundColor Green
Write-Host "  SSE endpoint: http://localhost:8081/sse" -ForegroundColor White

Start-Sleep 2

# Check if npx is available for MCP Inspector
if (Get-Command npx -ErrorAction SilentlyContinue) {
    Write-Host "`nLaunching MCP Inspector..." -ForegroundColor Cyan
    Write-Host "  Connect to: http://localhost:8081/sse" -ForegroundColor White
    Write-Host "  Press Ctrl+C to stop`n" -ForegroundColor White
    try {
        npx @modelcontextprotocol/inspector http://localhost:8081/sse
    } finally {
        Write-Host "`nStopping MCP server..." -ForegroundColor Yellow
        Stop-Job $mcpJob -ErrorAction SilentlyContinue
        Remove-Job $mcpJob -ErrorAction SilentlyContinue
    }
} else {
    Write-Host "`n[!] npx not found — MCP Inspector not launched." -ForegroundColor Yellow
    Write-Host "    Install Node.js from https://nodejs.org/" -ForegroundColor Yellow
    Write-Host "    Or connect manually to: http://localhost:8081/sse`n" -ForegroundColor White
    Write-Host "Press Ctrl+C to stop the MCP server."
    try {
        Wait-Job $mcpJob
    } finally {
        Stop-Job $mcpJob -ErrorAction SilentlyContinue
        Remove-Job $mcpJob -ErrorAction SilentlyContinue
    }
}
