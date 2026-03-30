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
    $procId = $parts[-1]
    if ($procId -match '^\d+$' -and $procId -ne '0') {
        Write-Host "  Killing PID $procId on port 8081" -ForegroundColor Yellow
        try {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        } catch {}
        taskkill /PID $procId /F 2>$null | Out-Null
    }
}
Start-Sleep -Milliseconds 500

# MCP Inspector (stdio mode) — Inspector spawns hr-mcp itself, no separate server process needed.
if (Get-Command npx -ErrorAction SilentlyContinue) {
    Write-Host "`nLaunching MCP Inspector (stdio mode)..." -ForegroundColor Cyan
    Write-Host "  Inspector UI will open in your browser automatically." -ForegroundColor White
    Write-Host "  Press Ctrl+C to stop`n" -ForegroundColor White
    npx @modelcontextprotocol/inspector uv run hr-mcp --stdio
} else {
    Write-Host "`n[!] npx not found — MCP Inspector not launched." -ForegroundColor Yellow
    Write-Host "    Install Node.js from https://nodejs.org/" -ForegroundColor Yellow
    Write-Host "`nFalling back to SSE mode on port 8081..." -ForegroundColor Yellow
    uv run hr-mcp
}
