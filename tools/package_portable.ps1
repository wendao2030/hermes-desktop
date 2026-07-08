param(
    [string]$OutputRoot = "",
    [string]$PackageName = "",
    [switch]$Force,
    [switch]$Zip,
    [switch]$IncludeEmployees,
    [switch]$IncludePersonalConfig
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$hermesRoot = Split-Path -Parent $scriptDir
$hermesRoot = [System.IO.Path]::GetFullPath($hermesRoot)

if (-not $OutputRoot) {
    $OutputRoot = Join-Path (Split-Path -Parent $hermesRoot) "hermes-portable-builds"
}
if (-not $PackageName) {
    $PackageName = "Hermes-Portable-" + (Get-Date -Format "yyyyMMdd-HHmmss")
}

$outputRootFull = [System.IO.Path]::GetFullPath($OutputRoot)
$packageDir = Join-Path $outputRootFull $PackageName
$zipPath = "$packageDir.zip"

function Require-Path {
    param(
        [string]$Path,
        [string]$Label
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label not found: $Path"
    }
}

function Remove-DirectoryRobust {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    $resolvedOutputRoot = [System.IO.Path]::GetFullPath($outputRootFull)
    if (-not $resolvedPath.StartsWith($resolvedOutputRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a directory outside output root: $resolvedPath"
    }

    $emptyDir = Join-Path $outputRootFull ("_empty_" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $emptyDir | Out-Null
    robocopy $emptyDir $Path /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    $code = $LASTEXITCODE
    Remove-Item -LiteralPath $emptyDir -Recurse -Force
    if ($code -ge 8) {
        throw "Failed to clean output directory with robocopy code $code"
    }
    Remove-Item -LiteralPath $Path -Recurse -Force
}

function Copy-DirectoryClean {
    param(
        [string]$RelativePath,
        [string[]]$ExtraExcludeDirs = @(),
        [string[]]$ExtraExcludeFiles = @()
    )

    $source = Join-Path $hermesRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        Write-Host "[SKIP] $RelativePath"
        return
    }

    $target = Join-Path $packageDir $RelativePath
    New-Item -ItemType Directory -Force -Path $target | Out-Null

    $excludeDirs = @(
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "venv",
        ".venv",
        "logs",
        "cache",
        "sessions",
        "memories",
        "workspace",
        "backups",
        "pairing",
        "hooks",
        "sandboxes",
        "execution_evidence",
        "temp_screenshots"
    ) + $ExtraExcludeDirs

    $excludeFiles = @(
        "*.pyc",
        "*.pyo",
        "*.log",
        "state.db",
        "state.db-shm",
        "state.db-wal",
        ".env",
        "auth.json",
        "auth.lock",
        "processes.json",
        ".skills_prompt_snapshot.json",
        "models_dev_cache.json"
    ) + $ExtraExcludeFiles

    Write-Host "[COPY] $RelativePath"
    robocopy $source $target /E /NFL /NDL /NJH /NJS /NP /XD $excludeDirs /XF $excludeFiles | Out-Null
    $code = $LASTEXITCODE
    if ($code -ge 8) {
        throw "Failed to copy $RelativePath, robocopy code $code"
    }
}

function Copy-RootFile {
    param([string]$Name)
    $source = Join-Path $hermesRoot $Name
    if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $packageDir $Name) -Force
        Write-Host "[COPY] $Name"
    }
}

Write-Host ""
Write-Host "============================================"
Write-Host "  Hermes portable package builder"
Write-Host "============================================"
Write-Host ""
Write-Host "Source:"
Write-Host "  $hermesRoot"
Write-Host "Output:"
Write-Host "  $packageDir"
Write-Host ""

Require-Path (Join-Path $hermesRoot "desktop-client") "desktop-client"
Require-Path (Join-Path $hermesRoot "hermes-agent") "hermes-agent"
Require-Path (Join-Path $hermesRoot "runtime\python311\python.exe") "private Python runtime"
Require-Path (Join-Path $hermesRoot "runtime\python311\pythonw.exe") "private Python windowed runtime"
Require-Path (Join-Path $hermesRoot "tools\launch_hermes.py") "launcher"
Require-Path (Join-Path $hermesRoot "tools\portable_setup.ps1") "portable setup script"
Require-Path (Join-Path $hermesRoot "setup.bat") "setup.bat"
Require-Path (Join-Path $hermesRoot "start.bat") "start.bat"

if ((Test-Path -LiteralPath $packageDir) -or (Test-Path -LiteralPath $zipPath)) {
    if (-not $Force) {
        throw "Output already exists. Use -Force to replace it: $packageDir"
    }
    if (Test-Path -LiteralPath $packageDir) {
        Remove-DirectoryRobust $packageDir
    }
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
}

New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

Copy-RootFile "setup.bat"
Copy-RootFile "start.bat"
Copy-RootFile "RULES_FOR_AI.md"
Copy-RootFile "SOUL.md"

if ($IncludePersonalConfig) {
    Copy-RootFile "config.yaml"
} else {
    Write-Host "[SKIP] config.yaml (personal config)"
}

Copy-DirectoryClean "desktop-client"
Copy-DirectoryClean "hermes-agent"
if (Test-Path -LiteralPath (Join-Path $hermesRoot "hermes-agent\node_modules")) {
    Copy-DirectoryClean "hermes-agent\node_modules"
} else {
    Write-Host "[WARN] hermes-agent\\node_modules not found; browser-related agent tools may need npm install"
}
Copy-DirectoryClean "runtime"
Copy-DirectoryClean "tools" -ExtraExcludeDirs @("__pycache__")
Copy-DirectoryClean "skills" -ExtraExcludeDirs @(".curator_backups", ".hub")
Copy-DirectoryClean "scripts" -ExtraExcludeDirs @("wechat_monitor_shots")

if ($IncludeEmployees) {
    Copy-DirectoryClean "employees"
} else {
    Write-Host "[SKIP] employees (personal employee data)"
}

$runtimeDirs = @(
    "workspace",
    "logs",
    "cache",
    "cache\images",
    "cache\videos",
    "sessions",
    "memories",
    "skills",
    "employees",
    "backups\versions"
)
foreach ($dir in $runtimeDirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $packageDir $dir) | Out-Null
}

$readme = @"
Hermes Portable
===============

1. Copy this whole folder to the target computer.
2. Make sure Git for Windows and Node.js are installed on that computer.
3. Double-click setup.bat once. It will create the desktop shortcut.
4. Start Hermes from the desktop icon, or run start.bat in this folder.

This package intentionally does not include personal chat history, logs,
state.db, auth.json, .env, cache files, sessions, memories, or personal
employee data unless the package was built with -IncludeEmployees.
"@
$readme | Set-Content -LiteralPath (Join-Path $packageDir "PORTABLE_README.txt") -Encoding UTF8

$manifest = [ordered]@{
    built_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    source = $hermesRoot
    package = $packageDir
    includes_runtime = $true
    includes_personal_config = [bool]$IncludePersonalConfig
    includes_employees = [bool]$IncludeEmployees
    requires_system_git = $true
    requires_system_node = $true
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $packageDir "portable-manifest.json") -Encoding UTF8

if ($Zip) {
    Write-Host "[ZIP] $zipPath"
    Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $zipPath -Force
}

Write-Host ""
Write-Host "[OK] Portable package created:"
Write-Host "  $packageDir"
if ($Zip) {
    Write-Host "  $zipPath"
}
Write-Host ""
