param(
    [Parameter(Mandatory = $true)]
    [string]$SuperPassword,

    [Parameter(Mandatory = $true)]
    [string]$AppPassword,

    [string]$Version = "18",
    [string]$InstallDir = "",
    [string]$DataDir = "",
    [string]$ServiceName = "",
    [string]$DatabaseName = "Coil",
    [string]$AppUser = "lg3d_app",
    [string]$AllowedSubnet = "192.168.0.0/24",
    [switch]$SetMachineEnv
)

$ErrorActionPreference = "Stop"

if (-not $InstallDir) {
    $InstallDir = "D:\PostgreSQL\$Version"
}
if (-not $DataDir) {
    $DataDir = Join-Path $InstallDir "data"
}
if (-not $ServiceName) {
    $ServiceName = "postgresql-x64-$Version"
}

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script from an elevated PowerShell session."
    }
}

function Assert-SafeIdentifier([string]$Name, [string]$Value) {
    if ($Value -notmatch "^[A-Za-z_][A-Za-z0-9_]*$") {
        throw "$Name must match ^[A-Za-z_][A-Za-z0-9_]*$"
    }
}

function Set-ConfigLine([string]$Path, [string]$Key, [string]$Value) {
    $content = Get-Content -LiteralPath $Path
    $line = "$Key = $Value"
    $pattern = "^\s*#?\s*$([regex]::Escape($Key))\s*="
    if ($content -match $pattern) {
        $content = $content | ForEach-Object {
            if ($_ -match $pattern) { $line } else { $_ }
        }
    } else {
        $content += $line
    }
    Set-Content -LiteralPath $Path -Value $content -Encoding UTF8
}

function Add-HbaLine([string]$Path, [string]$Line) {
    $content = Get-Content -LiteralPath $Path
    if ($content -notcontains $Line) {
        Add-Content -LiteralPath $Path -Value $Line -Encoding UTF8
    }
}

Assert-Administrator
Assert-SafeIdentifier "DatabaseName" $DatabaseName
Assert-SafeIdentifier "AppUser" $AppUser

if (-not (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget is required to install PostgreSQL automatically."
    }

    $override = @(
        "--mode unattended",
        "--unattendedmodeui none",
        "--superpassword `"$SuperPassword`"",
        "--servicename `"$ServiceName`"",
        "--serverport 5432",
        "--prefix `"$InstallDir`"",
        "--datadir `"$DataDir`""
    ) -join " "

    winget install `
        --id PostgreSQL.PostgreSQL `
        --source winget `
        --silent `
        --accept-source-agreements `
        --accept-package-agreements `
        --override $override
}

$psql = Join-Path $InstallDir "bin\psql.exe"
if (-not (Test-Path -LiteralPath $psql)) {
    $psqlCommand = Get-Command psql -ErrorAction SilentlyContinue
    if (-not $psqlCommand) {
        throw "psql.exe was not found. Check PostgreSQL installation path: $InstallDir"
    }
    $psql = $psqlCommand.Source
}

$localLanAddresses = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -like "192.168.0.*" } |
    Select-Object -ExpandProperty IPAddress -Unique
$listenAddresses = @("localhost") + $localLanAddresses
$listenValue = "'" + ($listenAddresses -join ",") + "'"

$postgresqlConf = Join-Path $DataDir "postgresql.conf"
$pgHbaConf = Join-Path $DataDir "pg_hba.conf"
Set-ConfigLine -Path $postgresqlConf -Key "listen_addresses" -Value $listenValue
Set-ConfigLine -Path $postgresqlConf -Key "password_encryption" -Value "'scram-sha-256'"
Add-HbaLine -Path $pgHbaConf -Line "host all all 127.0.0.1/32 scram-sha-256"
Add-HbaLine -Path $pgHbaConf -Line "host all all $AllowedSubnet scram-sha-256"

Restart-Service -Name $ServiceName

$env:PGPASSWORD = $SuperPassword
$escapedAppPassword = $AppPassword.Replace("'", "''")
$roleSql = @"
DO `$`$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$AppUser') THEN
        CREATE ROLE "$AppUser" LOGIN PASSWORD '$escapedAppPassword';
    ELSE
        ALTER ROLE "$AppUser" WITH LOGIN PASSWORD '$escapedAppPassword';
    END IF;
END
`$`$;
"@
& $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c $roleSql

$dbExists = & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$DatabaseName'"
if (-not $dbExists) {
    & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE `"$DatabaseName`" OWNER `"$AppUser`";"
}
& $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -c "GRANT ALL PRIVILEGES ON DATABASE `"$DatabaseName`" TO `"$AppUser`";"

$ruleName = "LG_3D PostgreSQL 5432"
if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule `
        -DisplayName $ruleName `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort 5432 `
        -RemoteAddress $AllowedSubnet `
        -Action Allow | Out-Null
}

$encodedPassword = [System.Uri]::EscapeDataString($AppPassword)
$databaseUrl = "postgresql+psycopg://${AppUser}:${encodedPassword}@127.0.0.1:5432/${DatabaseName}"
if ($SetMachineEnv) {
    [Environment]::SetEnvironmentVariable("COIL_DATABASE_URL", $databaseUrl, "Machine")
}

Write-Host "PostgreSQL setup complete."
Write-Host "Service: $ServiceName"
Write-Host "Allowed subnet: $AllowedSubnet"
Write-Host "COIL_DATABASE_URL: postgresql+psycopg://${AppUser}:****@127.0.0.1:5432/${DatabaseName}"
