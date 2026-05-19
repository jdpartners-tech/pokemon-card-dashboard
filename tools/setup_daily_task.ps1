# Sets up a Windows Scheduled Task to run the daily price scraper at 9:00 AM.
# Run once from PowerShell (as Administrator is not required for current user tasks):
#   .\tools\setup_daily_task.ps1

$ProjectRoot = "C:\Users\derek\Documents\Project\pokemon-card-dashboard"
$PythonExe   = (Get-Command python).Source
$Script      = "$ProjectRoot\tools\daily_scrape.py"
$TaskName    = "PokemonCardDailyScrape"

$Action  = New-ScheduledTaskAction -Execute $PythonExe -Argument $Script -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -Daily -At "09:00AM"
$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1) -StartWhenAvailable

# Remove existing task if present
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Daily PSA 10 price scrape for Pokemon Card Dashboard"

Write-Host ""
Write-Host "Scheduled task '$TaskName' created — runs daily at 9:00 AM."
Write-Host "Logs will be written to: $ProjectRoot\tools\daily_scrape.log"
Write-Host ""
Write-Host "To run manually right now:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  # or just: python tools\daily_scrape.py"
