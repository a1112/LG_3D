[CmdletBinding()]
param(
    [string]$LG3DRoot,
    [string]$Version,
    [switch]$ReadOnly
)

$ErrorActionPreference = "Stop"
if (-not $LG3DRoot) {
    $LG3DRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$dataRoot = Join-Path $LG3DRoot "var\ServiceMonitor"
if (-not $Version) {
    $active = Get-Content -LiteralPath (Join-Path $dataRoot "active.json") -Raw |
        ConvertFrom-Json
    $Version = [string]$active.currentVersion
}
$release = Join-Path $LG3DRoot "deploy\ServiceMonitor\releases\$Version"
$exe = Join-Path $release "LG3DServiceMonitor.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "ServiceMonitor executable not found: $exe"
}

$env:LG3D_ROOT = $LG3DRoot
$env:LG3D_MONITOR_DATA_DIR = $dataRoot
$env:LG3D_SERVICE_LAUNCHER_DIR = Join-Path $LG3DRoot "scripts\service_control\launchers"
$arguments = @(
    "--lg3d-root", "`"$LG3DRoot`"",
    "--data-dir", "`"$dataRoot`""
)
if ($ReadOnly) {
    $arguments += "--read-only"
}
$process = Start-Process -FilePath $exe -ArgumentList $arguments -Verb RunAs -PassThru
Start-Sleep -Seconds 2
if ($process.HasExited) {
    throw "ServiceMonitor exited during startup: $($process.ExitCode)"
}
[PSCustomObject]@{
    Version = $Version
    ProcessId = $process.Id
    Executable = $exe
    ReadOnly = [bool]$ReadOnly
}
