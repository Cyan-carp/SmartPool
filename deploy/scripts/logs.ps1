# Tail logs of one service.
param(
    [ValidateSet('backend', 'ai', 'simulator', 'nginx', 'mysql', 'redis')]
    [string]$Service = 'backend',
    [int]$Tail = 120,
    [string]$Remote = 'home-dev'
)

ssh $Remote "docker logs --tail $Tail smartpool-$Service"
