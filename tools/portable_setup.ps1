param(
    [string]$HermesHome = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
)

$ErrorActionPreference = "Stop"

$hermesRoot = [System.IO.Path]::GetFullPath($HermesHome)
$pythonw = Join-Path $hermesRoot "runtime\python311\pythonw.exe"
$launcher = Join-Path $hermesRoot "tools\launch_hermes.py"
$shortcutScript = Join-Path $hermesRoot "tools\create_desktop_shortcut.ps1"
$desktopClient = Join-Path $hermesRoot "desktop-client"
$hermesAgent = Join-Path $hermesRoot "hermes-agent"
$workspace = Join-Path $hermesRoot "workspace"
$logs = Join-Path $hermesRoot "logs"
$portableDirs = @(
    $workspace,
    $logs,
    (Join-Path $hermesRoot "cache"),
    (Join-Path $hermesRoot "cache\images"),
    (Join-Path $hermesRoot "cache\videos"),
    (Join-Path $hermesRoot "sessions"),
    (Join-Path $hermesRoot "memories"),
    (Join-Path $hermesRoot "skills"),
    (Join-Path $hermesRoot "employees"),
    (Join-Path $hermesRoot "backups\versions")
)

function Find-CommandPath {
    param([string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    return $null
}

function Require-Command {
    param(
        [string]$Name,
        [string]$DisplayName,
        [string]$InstallUrl
    )
    $path = Find-CommandPath $Name
    if (-not $path) {
        throw "$DisplayName was not found on this computer. Please install it first: $InstallUrl"
    }
    Write-Host "[OK] $DisplayName found:"
    Write-Host "  $path"
    return $path
}

function Find-GitBash {
    $git = Find-CommandPath "git.exe"
    $candidates = @()
    if ($git) {
        $gitCmdDir = Split-Path -Parent $git
        $gitRoot = Split-Path -Parent $gitCmdDir
        $candidates += Join-Path $gitRoot "bin\bash.exe"
        $candidates += Join-Path $gitRoot "usr\bin\bash.exe"
    }
    $candidates += Join-Path ${env:ProgramFiles} "Git\bin\bash.exe"
    $candidates += Join-Path ${env:ProgramFiles(x86)} "Git\bin\bash.exe"
    $candidates += Join-Path ${env:LOCALAPPDATA} "Programs\Git\bin\bash.exe"
    $bash = Find-CommandPath "bash.exe"
    if ($bash -and ($bash -match "\\Git\\")) {
        $candidates += $bash
    }

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }
    return $null
}

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
if (-not (Test-Path -LiteralPath $desktopClient)) {
    throw "desktop-client folder was not found: $desktopClient"
}
if (-not (Test-Path -LiteralPath $hermesAgent)) {
    throw "hermes-agent folder was not found: $hermesAgent"
}
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "Hermes launcher was not found: $launcher"
}
if (-not (Test-Path -LiteralPath $shortcutScript)) {
    throw "Shortcut script was not found: $shortcutScript"
}

Write-Host "[INFO] Checking system prerequisites..."
Require-Command -Name "git.exe" -DisplayName "Git for Windows" -InstallUrl "https://git-scm.com/download/win" | Out-Null
$gitBash = Find-GitBash
if (-not $gitBash) {
    throw "Git Bash was not found on this computer. Please install Git for Windows first: https://git-scm.com/download/win"
}
Write-Host "[OK] Git Bash found:"
Write-Host "  $gitBash"
Require-Command -Name "node.exe" -DisplayName "Node.js" -InstallUrl "https://nodejs.org/" | Out-Null
Write-Host ""

foreach ($dir in $portableDirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

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
