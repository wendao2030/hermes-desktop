param(
    [string]$InstallPackage = "D:\AI\project\hermes-install",
    [switch]$Force,
    [switch]$SkipShortcut
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$homeDir = Split-Path -Parent $scriptDir
$runtimeDir = Join-Path $homeDir "runtime\python311"
$runtimePython = Join-Path $runtimeDir "python.exe"

$sourceRuntime = Join-Path $InstallPackage "offline\python\python311_runtime"
$sourcePython = Join-Path $sourceRuntime "python.exe"
$wheelsDir = Join-Path $InstallPackage "offline\wheels"
$requirements = Join-Path $InstallPackage "requirements-full.txt"

function Require-Path([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label not found: $Path"
    }
}

Write-Host "[INFO] Hermes home: $homeDir"
Write-Host "[INFO] Install package: $InstallPackage"

Require-Path $sourcePython "Bundled Python"
Require-Path $wheelsDir "Offline wheels"
Require-Path $requirements "Requirements file"

if ($Force -and (Test-Path -LiteralPath $runtimeDir)) {
    Write-Host "[INFO] Removing existing runtime because -Force was supplied"
    Remove-Item -LiteralPath $runtimeDir -Recurse -Force
}

if (-not (Test-Path -LiteralPath $runtimePython)) {
    Write-Host "[INFO] Copying private Python runtime"
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $runtimeDir) | Out-Null
    robocopy $sourceRuntime $runtimeDir /E /NFL /NDL /NJH /NJS /NP | Out-Null
    $code = $LASTEXITCODE
    if ($code -ge 8) {
        throw "Runtime copy failed with robocopy code $code"
    }
} else {
    Write-Host "[OK] Private Python runtime already exists"
}

Require-Path $runtimePython "Runtime Python"

Write-Host "[INFO] Python version"
& $runtimePython -c "import sys; print(sys.executable); print(sys.version)"
if ($LASTEXITCODE -ne 0) {
    throw "Runtime Python failed to start"
}

Write-Host "[INFO] Installing dependencies into runtime Python"
& $runtimePython -m pip install --no-index --find-links="$wheelsDir" -r "$requirements"
if ($LASTEXITCODE -ne 0) {
    throw "Offline dependency install failed"
}

Write-Host "[INFO] Verifying core imports"
& $runtimePython -c "import fastapi, uvicorn, webview, openai, win32com, pptx, PIL, yaml, requests, pyautogui, pywinauto; print('core imports ok')"
if ($LASTEXITCODE -ne 0) {
    throw "Core import verification failed"
}

Write-Host "[INFO] Running pip check"
& $runtimePython -m pip check
if ($LASTEXITCODE -ne 0) {
    throw "pip check failed"
}

if (-not $SkipShortcut) {
    $shortcutScript = Join-Path $scriptDir "create_desktop_shortcut.ps1"
    if (Test-Path -LiteralPath $shortcutScript) {
        Write-Host "[INFO] Creating desktop shortcut"
        & powershell -NoProfile -ExecutionPolicy Bypass -File $shortcutScript
    } else {
        Write-Host "[WARN] Shortcut script not found: $shortcutScript"
    }
}

Write-Host "[OK] Runtime bootstrap complete"
