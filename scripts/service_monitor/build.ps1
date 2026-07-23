[CmdletBinding()]
param(
    [string]$Version,
    [string]$PythonExe = "D:\python\py311\python.exe",
    [string]$OutputRoot,
    [switch]$Diagnostic,
    [switch]$UseCurrentEnvironment,
    [switch]$SkipTests,
    [switch]$SkipSelfCheck
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$project = Join-Path $root "app\UI\ServiceMonitor"
$spec = Join-Path $project "packaging\ServiceMonitor.spec"
if (-not $Version) {
    $Version = (git -C $root rev-parse --short HEAD).Trim()
}
if ($Version -notmatch "^[0-9A-Za-z._-]+$") {
    throw "Invalid version: $Version"
}
if (-not $OutputRoot) {
    $OutputRoot = Join-Path $root "artifacts\ServiceMonitor"
}

if ($UseCurrentEnvironment) {
    $runner = $PythonExe
} else {
    $venv = Join-Path $root ".venv-service-monitor"
    $runner = Join-Path $venv "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $runner)) {
        & $PythonExe -m venv $venv
    }
    & $runner -m pip install --disable-pip-version-check -e "$project[build]"
}
if (-not (Test-Path -LiteralPath $runner) -and $runner -ne "python") {
    throw "Python executable not found: $runner"
}

if (-not $SkipTests) {
    & $runner -m pytest (Join-Path $project "tests") -q
    if ($LASTEXITCODE -ne 0) {
        throw "ServiceMonitor tests failed"
    }
}

$versionRoot = Join-Path $OutputRoot $Version
$workRoot = Join-Path $OutputRoot "_build\$Version"
if (Test-Path -LiteralPath $versionRoot) {
    $resolvedOutput = [IO.Path]::GetFullPath($OutputRoot)
    $resolvedVersion = [IO.Path]::GetFullPath($versionRoot)
    if (-not $resolvedVersion.StartsWith($resolvedOutput, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean outside output root: $resolvedVersion"
    }
    Remove-Item -LiteralPath $versionRoot -Recurse -Force
}

$env:LG3D_MONITOR_DIAGNOSTIC = if ($Diagnostic) { "1" } else { "0" }
$env:LG3D_MONITOR_PROJECT_ROOT = $project
& $runner -m PyInstaller --noconfirm --clean `
    --distpath $versionRoot `
    --workpath $workRoot `
    $spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed"
}

$name = if ($Diagnostic) {
    "LG3DServiceMonitor-debug"
} else {
    "LG3DServiceMonitor"
}
$artifact = Join-Path $versionRoot $name
$exe = Join-Path $artifact "$name.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Built executable not found: $exe"
}

$manifest = [ordered]@{
    schemaVersion = 1
    version = $Version
    gitSha = (git -C $root rev-parse HEAD).Trim()
    builtAt = (Get-Date).ToUniversalTime().ToString("o")
    diagnostic = [bool]$Diagnostic
    executable = "$name.exe"
    sha256 = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
    python = (& $runner --version 2>&1 | Out-String).Trim()
    pyinstaller = (& $runner -c "import PyInstaller; print(PyInstaller.__version__)").Trim()
    pyside = (& $runner -c "import PySide6; print(PySide6.__version__)").Trim()
}
$manifest | ConvertTo-Json -Depth 4 |
    Set-Content -LiteralPath (Join-Path $artifact "manifest.json") -Encoding UTF8

if (-not $SkipSelfCheck) {
    $env:LG3D_ROOT = $root
    $env:LG3D_MONITOR_DATA_DIR = Join-Path $root "var\ServiceMonitor-build-check"
    $checkArguments = @(
        "--self-check",
        "--lg3d-root", "`"$root`"",
        "--data-dir", "`"$env:LG3D_MONITOR_DATA_DIR`""
    )
    $check = Start-Process -FilePath $exe -ArgumentList $checkArguments `
        -Verb RunAs -Wait -PassThru
    if ($check.ExitCode -ne 0) {
        throw "Built executable self-check failed: $($check.ExitCode)"
    }
}

Write-Output $artifact
