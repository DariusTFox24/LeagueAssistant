# PowerShell script to restart Home Assistant

Write-Host "Restarting Home Assistant..." -ForegroundColor Green

try {
    Restart-Service -Name "homeassistant" -ErrorAction Stop
    Write-Host "✓ Home Assistant restarted successfully" -ForegroundColor Green
} catch {
    Write-Host "! Please restart Home Assistant manually." -ForegroundColor Yellow
}
