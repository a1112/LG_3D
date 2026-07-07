param(
    [int]$ApiPort = 5011,
    [int]$ImagePort = 6013,
    [int]$WebPort = 3015,
    [string]$ImageConfigPath = "",
    [switch]$StrictWebPort,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$StartupLogDir = Join-Path $Root "debug_log\startup"
New-Item -ItemType Directory -Force -Path $StartupLogDir | Out-Null

function Test-PortListening {
    param([int]$Port)
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Find-FreePort {
    param([int]$PreferredPort)
    $port = $PreferredPort
    while (Test-PortListening -Port $port) {
        $port += 1
    }
    return $port
}

function Test-HttpOk {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Test-ServiceHealth {
    param(
        [string]$Url,
        [string]$ExpectedService
    )
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -ne 200) {
            return $false
        }
        $body = $response.Content | ConvertFrom-Json
        return $body.service -eq $ExpectedService -and $body.status -eq "ok"
    }
    catch {
        return $false
    }
}

function Test-WebUiHealthy {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200 -and $response.Content -like "*Motion Studio*"
    }
    catch {
        return $false
    }
}

function Resolve-ServicePort {
    param(
        [int]$PreferredPort,
        [string]$HealthPath,
        [string]$ExpectedService
    )
    if (-not (Test-PortListening -Port $PreferredPort)) {
        return $PreferredPort
    }
    $healthUrl = "http://127.0.0.1:$PreferredPort$HealthPath"
    if (Test-ServiceHealth -Url $healthUrl -ExpectedService $ExpectedService) {
        return $PreferredPort
    }
    return Find-FreePort -PreferredPort ($PreferredPort + 1)
}

function Resolve-WebPort {
    param(
        [int]$PreferredPort,
        [switch]$Strict
    )
    if (-not (Test-PortListening -Port $PreferredPort)) {
        return $PreferredPort
    }
    $webUrl = "http://127.0.0.1:$PreferredPort/"
    if (Test-WebUiHealthy -Url $webUrl) {
        return $PreferredPort
    }
    if ($Strict) {
        throw "Web port $PreferredPort is already in use by another service."
    }
    return Find-FreePort -PreferredPort ($PreferredPort + 1)
}

function Start-RustExecutable {
    param(
        [string]$Name,
        [string]$WorkDir,
        [string]$ExePath,
        [string]$BuildCommand,
        [string]$Arguments,
        [string]$HealthUrl,
        [string]$ExpectedService
    )
    if (Test-ServiceHealth -Url $HealthUrl -ExpectedService $ExpectedService) {
        Write-Host "$Name already healthy at $HealthUrl"
        return
    }

    if ($DryRun) {
        Write-Host "[dry-run] build: $BuildCommand"
        Write-Host "[dry-run] start: $ExePath $Arguments"
        return
    }

    Push-Location $WorkDir
    try {
        Invoke-Expression $BuildCommand
    }
    finally {
        Pop-Location
    }

    Start-Process `
        -FilePath $ExePath `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $StartupLogDir "$Name.out.log") `
        -RedirectStandardError (Join-Path $StartupLogDir "$Name.err.log") | Out-Null
}

$ResolvedApiPort = Resolve-ServicePort -PreferredPort $ApiPort -HealthPath "/health" -ExpectedService "rust_api_service"
$ResolvedImagePort = Resolve-ServicePort -PreferredPort $ImagePort -HealthPath "/health" -ExpectedService "rust_image_service"
$ResolvedWebPort = Resolve-WebPort -PreferredPort $WebPort -Strict:$StrictWebPort

$DatabaseUrl = [Environment]::GetEnvironmentVariable("COIL_DATABASE_URL", "User")
if (-not $DatabaseUrl) {
    throw "COIL_DATABASE_URL is not set for the current Windows user."
}

$RustApiDir = Join-Path $Root "app\Server\rust_api_service"
$RustApiExe = Join-Path $RustApiDir "target\debug\rust_api_service.exe"
$env:COIL_DATABASE_URL = $DatabaseUrl
Start-RustExecutable `
    -Name "rust_api_service" `
    -WorkDir $RustApiDir `
    -ExePath $RustApiExe `
    -BuildCommand "cargo build" `
    -Arguments "--host 127.0.0.1 --port $ResolvedApiPort" `
    -HealthUrl "http://127.0.0.1:$ResolvedApiPort/health" `
    -ExpectedService "rust_api_service"

$RustImageDir = Join-Path $Root "app\Server\rust_image_service"
$RustImageExe = Join-Path $RustImageDir "target\debug\rust_image_service.exe"
$ServerConfig = $ImageConfigPath
$hasExplicitServerConfig = [bool]$ServerConfig
if (-not $ServerConfig -and $env:RUST_IMAGE_CONFIG) {
    $ServerConfig = $env:RUST_IMAGE_CONFIG
    $hasExplicitServerConfig = $true
}
if ($ServerConfig) {
    $ServerConfig = [Environment]::ExpandEnvironmentVariables($ServerConfig)
    if (-not [IO.Path]::IsPathRooted($ServerConfig)) {
        $ServerConfig = Join-Path $Root $ServerConfig
    }
}
if (-not $ServerConfig) {
    $fallbackConfigCandidates = @(
        (Join-Path $Root "CONFIG_3D\configs\Server3D.json"),
        "D:\CONFIG_3D\configs\Server3D.json"
    )
    foreach ($candidate in $fallbackConfigCandidates) {
        if (Test-Path $candidate) {
            $ServerConfig = $candidate
            break
        }
    }
}
if (-not $ServerConfig -or -not (Test-Path $ServerConfig)) {
    $configuredSources = @($ImageConfigPath, $env:RUST_IMAGE_CONFIG) | Where-Object { $_ }
    if ($configuredSources.Count -gt 0 -or $hasExplicitServerConfig) {
        throw "Unable to locate image config at: $($configuredSources -join ', ')"
    }
    throw "Unable to locate Server3D.json. Set -ImageConfigPath or set RUST_IMAGE_CONFIG."
}
Start-RustExecutable `
    -Name "rust_image_service" `
    -WorkDir $RustImageDir `
    -ExePath $RustImageExe `
    -BuildCommand "cargo build" `
    -Arguments "--config `"$ServerConfig`" --host 127.0.0.1 --port $ResolvedImagePort" `
    -HealthUrl "http://127.0.0.1:$ResolvedImagePort/health" `
    -ExpectedService "rust_image_service"

$WebDir = Join-Path $Root "app\UI\MotionStudioWeb"
$webCommand = "`$env:VITE_API_BASE_URL='/api'; `$env:VITE_IMAGE_BASE_URL='/image-api'; `$env:VITE_API_PROXY_TARGET='http://127.0.0.1:$ResolvedApiPort'; `$env:VITE_IMAGE_PROXY_TARGET='http://127.0.0.1:$ResolvedImagePort'; npm run dev -- --host 127.0.0.1 --port $ResolvedWebPort"
$ResolvedWebUrl = "http://127.0.0.1:$ResolvedWebPort/"
if (Test-WebUiHealthy -Url $ResolvedWebUrl) {
    Write-Host "motion_studio_web already healthy at $ResolvedWebUrl"
}
elseif ($DryRun) {
    Write-Host "[dry-run] start web: $webCommand"
}
else {
    Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $webCommand) `
        -WorkingDirectory $WebDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $StartupLogDir "motion_studio_web.out.log") `
        -RedirectStandardError (Join-Path $StartupLogDir "motion_studio_web.err.log") | Out-Null
}

[PSCustomObject]@{
    ApiUrl = "http://127.0.0.1:$ResolvedApiPort"
    ImageUrl = "http://127.0.0.1:$ResolvedImagePort"
    WebUrl = $ResolvedWebUrl.TrimEnd("/")
    Logs = $StartupLogDir
}
