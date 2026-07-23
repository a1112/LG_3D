#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [string]$LG3DRoot
)

$ErrorActionPreference = "Stop"
if (-not $LG3DRoot) {
    $LG3DRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$pidPath = Join-Path $LG3DRoot "var\ServiceMonitor\service-monitor.pid.json"
if (-not (Test-Path -LiteralPath $pidPath)) {
    Write-Output "ServiceMonitor is not running"
    exit 0
}
$record = Get-Content -LiteralPath $pidPath -Raw | ConvertFrom-Json
$processId = [int]$record.pid
$expectedRoot = [IO.Path]::GetFullPath(
    (Join-Path $LG3DRoot "deploy\ServiceMonitor\releases"))
$process = Get-CimInstance Win32_Process -Filter "ProcessId=$processId"
if (-not $process) {
    Remove-Item -LiteralPath $pidPath -Force
    exit 0
}
$actual = [IO.Path]::GetFullPath([string]$process.ExecutablePath)
if (-not $actual.StartsWith($expectedRoot, [StringComparison]::OrdinalIgnoreCase) -or
    [IO.Path]::GetFileName($actual) -ne "LG3DServiceMonitor.exe") {
    throw "Refusing to stop unexpected process $processId at $actual"
}
Stop-Process -Id $processId -Force
Wait-Process -Id $processId -Timeout 20 -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
Write-Output "Stopped ServiceMonitor PID $processId"
