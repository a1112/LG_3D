[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$ArtifactPath,
    [string]$LG3DRoot,
    [switch]$Activate
)

$ErrorActionPreference = "Stop"
if (-not $LG3DRoot) {
    $LG3DRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}
$artifact = (Resolve-Path -LiteralPath $ArtifactPath).Path
$manifestPath = Join-Path $artifact "manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Artifact manifest not found: $manifestPath"
}
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$version = [string]$manifest.version
if ($version -notmatch "^[0-9A-Za-z._-]+$") {
    throw "Invalid artifact version: $version"
}
$sourceExe = Join-Path $artifact ([string]$manifest.executable)
if ((Get-FileHash -LiteralPath $sourceExe -Algorithm SHA256).Hash -ne $manifest.sha256) {
    throw "Artifact checksum mismatch"
}

$releaseRoot = Join-Path $LG3DRoot "deploy\ServiceMonitor\releases"
$release = Join-Path $releaseRoot $version
if (Test-Path -LiteralPath $release) {
    throw "Immutable release already exists: $release"
}
New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null
Copy-Item -LiteralPath $artifact -Destination $release -Recurse
$deployedExe = Join-Path $release ([string]$manifest.executable)
if ((Get-FileHash -LiteralPath $deployedExe -Algorithm SHA256).Hash -ne $manifest.sha256) {
    throw "Deployed checksum mismatch"
}

$dataRoot = Join-Path $LG3DRoot "var\ServiceMonitor"
$configRoot = Join-Path $dataRoot "config"
New-Item -ItemType Directory -Force -Path $configRoot,(Join-Path $dataRoot "logs") | Out-Null
$legacyRoots = @(
    (Join-Path (Split-Path $LG3DRoot -Parent) "bkvl_UI\dist\lis\config"),
    (Join-Path (Split-Path $LG3DRoot -Parent) "bkvl_UI\config")
)
foreach ($name in @("DiskMonitor.json", "SoftMonitor.json")) {
    $target = Join-Path $configRoot $name
    if (Test-Path -LiteralPath $target) {
        continue
    }
    foreach ($legacyRoot in $legacyRoots) {
        $source = Join-Path $legacyRoot $name
        if (Test-Path -LiteralPath $source) {
            Copy-Item -LiteralPath $source -Destination $target
            break
        }
    }
}

if ($Activate) {
    $activePath = Join-Path $dataRoot "active.json"
    $previous = $null
    if (Test-Path -LiteralPath $activePath) {
        $previous = (Get-Content -LiteralPath $activePath -Raw | ConvertFrom-Json).currentVersion
    }
    [ordered]@{
        schemaVersion = 1
        currentVersion = $version
        previousVersion = $previous
        activatedAt = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json | Set-Content -LiteralPath $activePath -Encoding UTF8
}

[PSCustomObject]@{
    Version = $version
    ReleasePath = $release
    Activated = [bool]$Activate
}
