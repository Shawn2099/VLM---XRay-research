# Switch the active backend on icccserver.
#
#   .\medgemma\switch.ps1 -Model medgemma
#   .\medgemma\switch.ps1 -Model cxr
#
# Both share http://10.10.10.28:8000/ and the same API key/UI.

[CmdletBinding()]
param(
    [ValidateSet("cxr", "medgemma")]
    [string]$Model = "medgemma"
)

$ErrorActionPreference = "Stop"
Write-Host "switching active backend to: $Model"
ssh -o LogLevel=ERROR icccserver "bash /home/iccc/switch.sh $Model"
