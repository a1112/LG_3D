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
    $legacyExecutable = [string]$active.legacyExecutable
    if (-not $legacyExecutable) {
        $legacyExecutable = Join-Path (Split-Path $LG3DRoot -Parent) "bkvl_UI\dist\lis\lis.exe"
    }
    if (-not (Test-Path -LiteralPath $legacyExecutable)) {
        throw "No previous release or legacy ServiceMonitor executable is available"
    }
    $current = [string]$active.currentVersion
    & (Join-Path $PSScriptRoot "stop.ps1") -LG3DRoot $LG3DRoot
    [ordered]@{
        schemaVersion = 1
        mode = "legacy"
        currentVersion = $current
        previousVersion = $null
        legacyExecutable = $legacyExecutable
        rolledBackAt = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json | Set-Content -LiteralPath $activePath -Encoding UTF8
    & (Join-Path $PSScriptRoot "start.ps1") -LG3DRoot $LG3DRoot
    exit 0
}
$current = [string]$active.currentVersion
$previous = [string]$active.previousVersion
& (Join-Path $PSScriptRoot "stop.ps1") -LG3DRoot $LG3DRoot
[ordered]@{
    schemaVersion = 1
    mode = "release"
    currentVersion = $previous
    previousVersion = $current
    legacyExecutable = $active.legacyExecutable
    activatedAt = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content -LiteralPath $activePath -Encoding UTF8
& (Join-Path $PSScriptRoot "start.ps1") -LG3DRoot $LG3DRoot -Version $previous
