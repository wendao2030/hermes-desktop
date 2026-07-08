param(
    [string]$HermesHome = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)),
    [string]$ShortcutName = "Hermes Desktop"
)

$ErrorActionPreference = "Stop"

$hermesRoot = [System.IO.Path]::GetFullPath($HermesHome)
$desktopDir = [Environment]::GetFolderPath("Desktop")

$target = Join-Path $hermesRoot "runtime\python311\pythonw.exe"
$script = Join-Path $hermesRoot "tools\launch_hermes.py"
$icon = Join-Path $hermesRoot "desktop-client\static\hermes_pony.ico"
if (-not (Test-Path -LiteralPath $icon)) {
    $icon = Join-Path $hermesRoot "desktop-client\static\hermes.ico"
}
if (-not (Test-Path -LiteralPath $icon)) {
    $icon = $target
}

if (-not (Test-Path -LiteralPath $target)) {
    throw "Python launcher not found: $target"
}
if (-not (Test-Path -LiteralPath $script)) {
    throw "Hermes launcher script not found: $script"
}

$link = Join-Path $desktopDir ($ShortcutName + ".lnk")
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($link)
$shortcut.TargetPath = $target
$shortcut.Arguments = "`"$script`""
$shortcut.WorkingDirectory = $hermesRoot
$shortcut.IconLocation = $icon
$shortcut.Description = "Start Hermes Desktop"
$shortcut.Save()

Write-Host "Shortcut created: $link"
Write-Host "Target: $target"
Write-Host "Arguments: $script"
Write-Host "Icon: $icon"
