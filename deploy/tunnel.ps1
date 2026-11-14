# SSH tunnel: local 127.0.0.1:8000 -> icccserver's 127.0.0.1:8000
# Leave this window open while using test_client.ps1 or your app.

[CmdletBinding()]
param(
    [string]$Server = "icccserver",
    [int]$LocalPort = 8010
)

Write-Host "forwarding 127.0.0.1:$LocalPort -> $Server (Ctrl+C to stop)"
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 `
    -L "${LocalPort}:127.0.0.1:8000" $Server
