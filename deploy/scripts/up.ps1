# Sync, build and start the whole stack on home-dev.
# Usage: .\up.ps1 [-SkipSync] [-NoBuild]

param(
    [string]$Remote = 'home-dev',
    [string]$RemotePath = 'C:\home-dev\smartpool',
    [switch]$SkipSync,
    [switch]$NoBuild
)

$ErrorActionPreference = 'Stop'

if (-not $SkipSync) {
    & (Join-Path $PSScriptRoot 'sync.ps1') -Remote $Remote -RemotePath $RemotePath
}

# First run: generate random credentials once, stored only on the remote machine.
ssh $Remote "if exist $RemotePath\deploy\.env (exit 0) else (exit 9)"
if ($LASTEXITCODE -eq 9) {
    Write-Host '[up] deploy/.env missing on remote, generating random credentials'
    $chars = (48..57) + (65..90) + (97..122)
    $root = -join ($chars | Get-Random -Count 24 | ForEach-Object { [char]$_ })
    $pwd = -join ($chars | Get-Random -Count 24 | ForEach-Object { [char]$_ })
    $jwt = -join ($chars | Get-Random -Count 48 | ForEach-Object { [char]$_ })
    $envFile = Join-Path $env:TEMP 'smartpool.env'
    @(
        "MYSQL_ROOT_PASSWORD=$root"
        'MYSQL_DATABASE=smartpool'
        'MYSQL_USER=smartpool'
        "MYSQL_PASSWORD=$pwd"
        "JWT_SECRET=$jwt"
        'AI_DETECTOR_PROVIDER=mock'
        'AI_DEVICE=cpu'
    ) | Set-Content -LiteralPath $envFile -Encoding ASCII
    scp $envFile "${Remote}:C:/home-dev/smartpool-env.tmp"
    ssh $Remote "move /y C:\home-dev\smartpool-env.tmp $RemotePath\deploy\.env"
    [System.IO.File]::Delete($envFile)
}

$compose = 'docker compose -f deploy/compose.yaml --env-file deploy/.env'
if ($NoBuild) {
    ssh $Remote "cd /d $RemotePath && $compose up -d --wait"
} else {
    ssh $Remote "cd /d $RemotePath && $compose up -d --build --wait"
}
if ($LASTEXITCODE -ne 0) { throw 'compose up failed, check: .\logs.ps1 -Service backend' }

Write-Host '[up] container status'
ssh $Remote 'docker ps --filter name=smartpool'
Write-Host '[up] open http://127.0.0.1:18080 after running .\tunnel.ps1'
