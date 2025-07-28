# PowerShell script to restart Home Assistant and test the League of Legends integration

Write-Host "Restarting Home Assistant to load League of Legends integration updates..." -ForegroundColor Green

# For Home Assistant Core
try {
    # Try to restart Home Assistant service
    Restart-Service -Name "homeassistant" -ErrorAction Stop
    Write-Host "✓ Home Assistant service restarted successfully" -ForegroundColor Green
} catch {
    Write-Host "! Unable to restart via service. Please restart Home Assistant manually." -ForegroundColor Yellow
    Write-Host "  - For HASS.IO/Supervisor: Go to Settings > System > Host > Restart" -ForegroundColor Gray
    Write-Host "  - For Core: Restart the Home Assistant process" -ForegroundColor Gray
    Write-Host "  - For Docker: Restart the container" -ForegroundColor Gray
}

Write-Host ""
Write-Host "New features added:" -ForegroundColor Cyan
Write-Host "  • Match History sensor - Shows last 10 match IDs" -ForegroundColor White
Write-Host "  • Latest Match sensor - Detailed stats from your most recent game" -ForegroundColor White
Write-Host "  • Automatic match change detection for automations" -ForegroundColor White
Write-Host ""
Write-Host "Available entities:" -ForegroundColor Cyan
Write-Host "  • sensor.lol_stats_YOUR_RIOT_ID_match_history" -ForegroundColor White
Write-Host "  • sensor.lol_stats_YOUR_RIOT_ID_latest_match" -ForegroundColor White
Write-Host ""
Write-Host "The Latest Match sensor will change state when a new match is completed," -ForegroundColor Yellow
Write-Host "making it perfect for automation triggers!" -ForegroundColor Yellow
