#Requires -RunAsAdministrator
[CmdletBinding()]
param(
    [string]$LG3DRoot
)

$ErrorActionPreference = "Stop"
if (-not $LG3DRoot) {
    $LG3DRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$dataRoot = Join-Path $LG3DRoot "var\ServiceMonitor"
$activePath = Join-Path $dataRoot "active.json"
$active = Get-Content -LiteralPath $activePath -Raw | ConvertFrom-Json
if (-not $active.previousVersion) {
    throw "No previous ServiceMonitor release is recorded"
}
$current = [string]$active.currentVersion
$previous = [string]$active.previousVersion
& (Join-Path $PSScriptRoot "stop.ps1") -LG3DRoot $LG3DRoot
[ordered]@{
    schemaVersion = 1
    currentVersion = $previous
    previousVersion = $current
    activatedAt = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content -LiteralPath $activePath -Encoding UTF8
& (Join-Path $PSScriptRoot "start.ps1") -LG3DRoot $LG3DRoot -Version $previous
