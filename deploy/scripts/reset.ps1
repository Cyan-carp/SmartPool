# Reset demo state: rotate the simulated world and clear risk windows (database kept).
# Requires the SSH tunnel to be running (see tunnel.ps1); talks to the backend through nginx.
param(
    [string]$Base = 'http://127.0.0.1:18080',
    [int]$Seed = 2026,
    [int]$Swimmers = 8
)

$ErrorActionPreference = 'Stop'

$login = Invoke-RestMethod -Method Post -Uri "$Base/api/v1/auth/login" `
    -ContentType 'application/json' `
    -Body (@{ username = 'manager'; password = 'demo1234' } | ConvertTo-Json)
$headers = @{ Authorization = "Bearer $($login.data.token)" }

$result = Invoke-RestMethod -Method Post -Headers $headers `
    -Uri "$Base/api/v1/demo/reset?seed=$Seed&swimmerCount=$Swimmers"

Write-Host "[reset] scenario=$($result.data.scenario) seed=$($result.data.seed) swimmers=$($result.data.swimmerCount)"
Write-Host '[reset] world reseeded, risk windows cleared, database kept'
