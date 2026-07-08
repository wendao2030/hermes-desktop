param(
    [string]$HermesHome = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
)

$ErrorActionPreference = "Stop"

$hermesRoot = [System.IO.Path]::GetFullPath($HermesHome)
$pythonw = Join-Path $hermesRoot "runtime\python311\pythonw.exe"
$launcher = Join-Path $hermesRoot "tools\launch_hermes.py"
$shortcutScript = Join-Path $hermesRoot "tools\create_desktop_shortcut.ps1"
$workspace = Join-Path $hermesRoot "workspace"
$logs = Join-Path $hermesRoot "logs"

Write-Host ""
Write-Host "============================================"
Write-Host "  Hermes Desktop portable setup"
Write-Host "============================================"
Write-Host ""
Write-Host "Hermes folder:"
Write-Host "  $hermesRoot"
Write-Host ""

if (-not (Test-Path -LiteralPath $pythonw)) {
    throw "Private Python runtime was not found: $pythonw"
}
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "Hermes launcher was not found: $launcher"
}
if (-not (Test-Path -LiteralPath $shortcutScript)) {
    throw "Shortcut script was not found: $shortcutScript"
}

New-Item -ItemType Directory -Force -Path $workspace | Out-Null
New-Item -ItemType Directory -Force -Path $logs | Out-Null

Write-Host "[INFO] Workspace:"
Write-Host "  $workspace"
Write-Host ""

& powershell -NoProfile -ExecutionPolicy Bypass -File $shortcutScript -HermesHome $hermesRoot
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create desktop shortcut"
}

Write-Host ""
Write-Host "[OK] Hermes portable setup complete."
Write-Host "You can now start Hermes from the desktop icon, or run start.bat here."
Write-Host ""
