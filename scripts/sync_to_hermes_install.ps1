param(
    [string]$Source = "C:\Users\dtyao\AppData\Local\hermes",
    [string]$Target = "D:\AI\project\hermes-install"
)

$ErrorActionPreference = "Stop"

function Resolve-ExistingPath([string]$PathValue, [string]$Label) {
    if (-not (Test-Path -LiteralPath $PathValue)) {
        throw "$Label does not exist: $PathValue"
    }
    return (Resolve-Path -LiteralPath $PathValue).Path
}

function Invoke-RoboMirror {
    param(
        [string]$From,
        [string]$To,
        [string[]]$ExcludeDirs = @(),
        [string[]]$ExcludeFiles = @()
    )

    if (-not (Test-Path -LiteralPath $From)) {
        Write-Host "Skip missing: $From"
        return
    }

    New-Item -ItemType Directory -Force -Path $To | Out-Null
    $args = @(
        $From,
        $To,
        "/MIR",
        "/R:2",
        "/W:1",
        "/FFT",
        "/COPY:DAT",
        "/DCOPY:DAT",
        "/NP",
        "/NFL",
        "/NDL",
        "/NJH",
        "/NJS"
    )
    if ($ExcludeDirs.Count -gt 0) {
        $args += "/XD"
        $args += $ExcludeDirs
    }
    if ($ExcludeFiles.Count -gt 0) {
        $args += "/XF"
        $args += $ExcludeFiles
    }

    Write-Host "Sync: $From -> $To"
    & robocopy @args | Out-Null
    $code = $LASTEXITCODE
    if ($code -gt 7) {
        throw "robocopy failed with exit code $code for $From"
    }
}

function Copy-IfExists {
    param([string]$From, [string]$To)
    if (Test-Path -LiteralPath $From) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $To) | Out-Null
        Copy-Item -LiteralPath $From -Destination $To -Force
        Write-Host "Copy: $From -> $To"
    }
}

function Remove-TargetPath {
    param([string]$PathValue)
    if (Test-Path -LiteralPath $PathValue) {
        Write-Host "Remove runtime leftover: $PathValue"
        Remove-Item -LiteralPath $PathValue -Recurse -Force
    }
}

$Source = Resolve-ExistingPath $Source "Source"
$Target = Resolve-ExistingPath $Target "Target"

if ($Source.TrimEnd("\") -eq $Target.TrimEnd("\")) {
    throw "Source and target must be different."
}

Write-Host "Hermes source : $Source"
Write-Host "Install target: $Target"
Write-Host ""

$commonExcludeDirs = @(
    ".git",
    "venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache"
)

$commonExcludeFiles = @(
    "*.pyc",
    "*.pyo",
    "*.log",
    ".env"
)

Invoke-RoboMirror `
    -From (Join-Path $Source "desktop-client") `
    -To (Join-Path $Target "desktop-client") `
    -ExcludeDirs ($commonExcludeDirs + @("sessions", "uploads", "execution_evidence")) `
    -ExcludeFiles ($commonExcludeFiles + @("state.json", "state.db", "state.db-shm", "state.db-wal", "bubble_init_debug.json", "_test.bmp", "_bubble_*.bmp"))

Invoke-RoboMirror `
    -From (Join-Path $Source "hermes-agent") `
    -To (Join-Path $Target "hermes-agent") `
    -ExcludeDirs $commonExcludeDirs `
    -ExcludeFiles $commonExcludeFiles

Invoke-RoboMirror `
    -From (Join-Path $Source "skills") `
    -To (Join-Path $Target "skills") `
    -ExcludeDirs ($commonExcludeDirs + @(".cache", ".hub", ".curator_backups", "temp_screenshots")) `
    -ExcludeFiles ($commonExcludeFiles + @(".usage.json"))

Invoke-RoboMirror `
    -From (Join-Path $Source "lsp") `
    -To (Join-Path $Target "lsp") `
    -ExcludeDirs $commonExcludeDirs `
    -ExcludeFiles $commonExcludeFiles

Invoke-RoboMirror `
    -From (Join-Path $Source "patches") `
    -To (Join-Path $Target "patches") `
    -ExcludeDirs $commonExcludeDirs `
    -ExcludeFiles $commonExcludeFiles

Invoke-RoboMirror `
    -From (Join-Path $Source "tasks") `
    -To (Join-Path $Target "tasks") `
    -ExcludeDirs $commonExcludeDirs `
    -ExcludeFiles $commonExcludeFiles

Invoke-RoboMirror `
    -From (Join-Path $Source "scripts") `
    -To (Join-Path $Target "scripts") `
    -ExcludeDirs ($commonExcludeDirs + @("wechat_monitor_shots")) `
    -ExcludeFiles ($commonExcludeFiles + @("*_state.json", "*.tmp"))

Copy-IfExists (Join-Path $Source "config.yaml") (Join-Path $Target "config.yaml")
Copy-IfExists (Join-Path $Source "SOUL.md") (Join-Path $Target "SOUL.md")
Copy-IfExists (Join-Path $Source "RULES_FOR_AI.md") (Join-Path $Target "RULES_FOR_AI.md")
Copy-IfExists (Join-Path $Source "tools\launch_hermes.py") (Join-Path $Target "tools\launch_hermes.py")

@(
    "desktop-client\sessions",
    "desktop-client\__pycache__",
    "desktop-client\uploads",
    "desktop-client\execution_evidence",
    "hermes-agent\venv",
    "hermes-agent\node_modules",
    "test_install\venv",
    "employees",
    "venv",
    "cache",
    "audio_cache",
    "image_cache",
    "logs",
    "sessions"
) | ForEach-Object {
    Remove-TargetPath (Join-Path $Target $_)
}

@(
    "state.db",
    "state.db-shm",
    "state.db-wal",
    "auth.json",
    "auth.lock",
    ".env",
    "processes.json",
    "desktop-client\state.json",
    "desktop-client\state.db",
    "desktop-client\state.db-shm",
    "desktop-client\state.db-wal",
    "desktop-client\bubble_init_debug.json"
) | ForEach-Object {
    Remove-TargetPath (Join-Path $Target $_)
}

Write-Host ""
Write-Host "Kept install-only assets in target: install/update scripts, offline wheels, cua-driver, hermes_patches, tools."
Write-Host "Skipped local runtime/sensitive data: venv, caches, sessions, employees, state.db, auth files, logs, .env."
Write-Host "Sync complete."
