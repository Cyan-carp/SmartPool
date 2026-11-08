# Open a local tunnel to the remote nginx, then browse http://127.0.0.1:18080
param(
    [string]$Remote = 'home-dev',
    [int]$LocalPort = 18080,
    [int]$RemotePort = 18080
)

Write-Host "[tunnel] http://127.0.0.1:$LocalPort -> ${Remote}:$RemotePort  (Ctrl+C to stop)"
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 `
    -L "127.0.0.1:${LocalPort}:127.0.0.1:${RemotePort}" $Remote
