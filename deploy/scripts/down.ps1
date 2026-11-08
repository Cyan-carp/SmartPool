# Stop this project's containers (keeps data volumes).
param(
    [string]$Remote = 'home-dev',
    [string]$RemotePath = 'C:\home-dev\smartpool'
)

$ErrorActionPreference = 'Stop'
ssh $Remote "cd /d $RemotePath && docker compose -f deploy/compose.yaml --env-file deploy/.env down"
Write-Host '[down] stopped, volumes kept (no -v)'
