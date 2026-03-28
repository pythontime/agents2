# Contoso HR Agent — Start (Windows)
# Starts the file watcher as a background job and the FastAPI engine in the foreground.
# The engine kills port 8080 automatically on startup.

Set-StrictMode -Version Latest

Write-Host "`n=== Starting Contoso HR Agent ===" -ForegroundColor Cyan
Write-Host "  Web UI: http://localhost:8080/chat.html" -ForegroundColor White
Write-Host "  API:    http://localhost:8080/api/" -ForegroundColor White
Write-Host "  Press Ctrl+C to stop`n" -ForegroundColor White

# Start watcher as background job
$watcherJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    uv run hr-watcher
}
Write-Host "[watcher] Started (Job ID: $($watcherJob.Id))" -ForegroundColor Green

# Open browser after a short delay
Start-Job -ScriptBlock {
    Start-Sleep 3
    Start-Process "http://localhost:8080/chat.html"
} | Out-Null

# Start engine (foreground — blocks until Ctrl+C)
try {
    uv run hr-engine
} finally {
    Write-Host "`nStopping watcher..." -ForegroundColor Yellow
    Stop-Job $watcherJob -ErrorAction SilentlyContinue
    Remove-Job $watcherJob -ErrorAction SilentlyContinue
}
