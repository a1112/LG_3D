$ErrorActionPreference = "Stop"

function Assert-Equal {
    param(
        [object]$Actual,
        [object]$Expected,
        [string]$Message
    )

    if ($Actual -ne $Expected) {
        throw "$Message Expected '$Expected', got '$Actual'."
    }
}

function Assert-Contains {
    param(
        [string]$Source,
        [string]$Needle,
        [string]$Message
    )

    if (-not $Source.Contains($Needle)) {
        throw $Message
    }
}

$scriptPath = Join-Path $PSScriptRoot "start_rust_motion_studio_dev.ps1"
$source = Get-Content -Raw -Path $scriptPath
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($scriptPath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) {
    throw "Failed to parse $scriptPath"
}

$functionDefinitions = $ast.FindAll({
        param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst]
    }, $true)
foreach ($functionDefinition in $functionDefinitions) {
    Invoke-Expression $functionDefinition.Extent.Text
}

function Invoke-WebRequest {
    param(
        [string]$Uri,
        [switch]$UseBasicParsing,
        [int]$TimeoutSec
    )

    return [PSCustomObject]@{
        StatusCode = 200
        Content = '{"status":"error","service":"rust_api_service"}'
    }
}

$unhealthyService = Test-ServiceHealth -Url "http://127.0.0.1:5011/health" -ExpectedService "rust_api_service"
Assert-Equal $unhealthyService $false "Test-ServiceHealth must reject a matching service when its status is not ok."

function Test-PortListening {
    param([int]$Port)
    return $Port -eq 5011
}

function Find-FreePort {
    param([int]$PreferredPort)
    return $PreferredPort
}

$script:healthCall = $null
function Test-ServiceHealth {
    param(
        [string]$Url,
        [string]$ExpectedService
    )
    $script:healthCall = [PSCustomObject]@{
        Url = $Url
        ExpectedService = $ExpectedService
    }
    return $false
}

$resolvedConflictPort = Resolve-ServicePort -PreferredPort 5011 -HealthPath "/health" -ExpectedService "rust_api_service"
Assert-Equal $resolvedConflictPort 5012 "Resolve-ServicePort must skip a port occupied by a different healthy service."
Assert-Equal $script:healthCall.Url "http://127.0.0.1:5011/health" "Resolve-ServicePort must check the preferred health URL."
Assert-Equal $script:healthCall.ExpectedService "rust_api_service" "Resolve-ServicePort must pass the expected service identity."

function Test-ServiceHealth {
    param(
        [string]$Url,
        [string]$ExpectedService
    )
    return $ExpectedService -eq "rust_api_service"
}

$resolvedHealthyPort = Resolve-ServicePort -PreferredPort 5011 -HealthPath "/health" -ExpectedService "rust_api_service"
Assert-Equal $resolvedHealthyPort 5011 "Resolve-ServicePort should reuse the port only when the expected service is healthy."

function Invoke-Startup {
    param(
        [string]$ImageConfigPath = "",
        [bool]$UseEnvConfig = $false,
        [string]$EnvConfig = "",
        [int]$ImagePort = 6013,
        [int]$WebPort = 3015,
        [int]$ApiPort = 5011
    )
    $originalDb = [Environment]::GetEnvironmentVariable("COIL_DATABASE_URL", "User")
    $originalImageConfig = [Environment]::GetEnvironmentVariable("RUST_IMAGE_CONFIG", "User")
    [Environment]::SetEnvironmentVariable("COIL_DATABASE_URL", "mysql://127.0.0.1/test", "User")
    if ($UseEnvConfig) {
        [Environment]::SetEnvironmentVariable("RUST_IMAGE_CONFIG", $EnvConfig, "User")
    }
    elseif ($originalImageConfig -ne $null) {
        [Environment]::SetEnvironmentVariable("RUST_IMAGE_CONFIG", "", "User")
    }
    try {
        if ($ImageConfigPath) {
            & $scriptPath -ImagePort $ImagePort -WebPort $WebPort -ApiPort $ApiPort -ImageConfigPath $ImageConfigPath -DryRun | Out-Null
        }
        else {
            & $scriptPath -ImagePort $ImagePort -WebPort $WebPort -ApiPort $ApiPort -DryRun | Out-Null
        }
    }
    finally {
        [Environment]::SetEnvironmentVariable("COIL_DATABASE_URL", $originalDb, "User")
        [Environment]::SetEnvironmentVariable("RUST_IMAGE_CONFIG", $originalImageConfig, "User")
    }
}

$tmp = Join-Path $PSScriptRoot "temp_startup_test"
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
$candidate = Join-Path $tmp "Server3D.json"
Set-Content -Path $candidate -Value "{}"
try {
    Invoke-Startup -ImageConfigPath $candidate

    try {
        Invoke-Startup -UseEnvConfig $true -EnvConfig $candidate
    }
    catch {
        throw "start script should accept RUST_IMAGE_CONFIG env fallback."
    }

    try {
        $missingCandidate = Join-Path $tmp "missing_server3d.json"
        Invoke-Startup -ImageConfigPath $missingCandidate
        throw "start script should fail for missing ImageConfigPath."
    }
    catch {
        if (-not $_.Exception.Message.Contains("Unable to locate image config at")) {
            throw "start script should fail with missing image config message."
        }
    }

    Invoke-Startup
}
finally {
    Remove-Item -Path $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

Assert-Contains $source '-ExpectedService "rust_api_service"' "API startup must verify the rust_api_service health identity."
Assert-Contains $source '-ExpectedService "rust_image_service"' "Image startup must verify the rust_image_service health identity."

Write-Host "start_rust_motion_studio_dev tests passed"
