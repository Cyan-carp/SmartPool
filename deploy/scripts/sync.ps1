# Sync source to home-dev (tar -> scp -> extract).
# Usage: .\sync.ps1 [-Remote home-dev] [-RemotePath C:\home-dev\smartpool]
# NOTE: keep all console output ASCII; Windows PowerShell 5.1 reads this file as ANSI.

param(
    [string]$Remote = 'home-dev',
    [string]$RemotePath = 'C:\home-dev\smartpool'
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$archive = Join-Path $env:TEMP 'smartpool-src.tgz'

Write-Host "[sync] repo: $repoRoot"
Write-Host "[sync] archive: $archive"

if ([System.IO.File]::Exists($archive)) {
    [System.IO.File]::Delete($archive)
}

Push-Location $repoRoot
try {
    tar -czf $archive --exclude=node_modules --exclude=target --exclude=dist --exclude=.git `
        --exclude=artifacts --exclude=backups --exclude=.env --exclude=deploy/.env --exclude=__pycache__ .
    if ($LASTEXITCODE -ne 0) { throw 'tar failed' }
} finally {
    Pop-Location
}

$size = [math]::Round((Get-Item $archive).Length / 1MB, 2)
Write-Host "[sync] package size: $size MB"

ssh $Remote "if not exist $RemotePath mkdir $RemotePath"
scp $archive "${Remote}:C:/home-dev/smartpool-src.tgz"
ssh $Remote "tar -xzf C:\home-dev\smartpool-src.tgz -C $RemotePath"
if ($LASTEXITCODE -ne 0) { throw 'remote extract failed' }

Write-Host '[sync] done'
