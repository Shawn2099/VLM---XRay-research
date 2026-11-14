# Send one chest X-ray to the service through the SSH tunnel.
#
#   .\deploy\test_client.ps1
#   .\deploy\test_client.ps1 -Mode ask -Question "Is there cardiomegaly?"
#   .\deploy\test_client.ps1 -Mode differential -Image .\some_cxr.png

[CmdletBinding()]
param(
    [string]$BaseUrl = "http://127.0.0.1:8010",
    [string]$ApiKey = $env:CXR_API_KEY,
    [string]$Image,
    [ValidateSet("report", "differential", "ask")]
    [string]$Mode = "report",
    [string]$Question = "What are the possible differential diagnoses?",
    [double]$Temperature = 0.2,
    [double]$TopP = 0.8
)

$ErrorActionPreference = "Stop"

$deployDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Image) { $Image = Join-Path $deployDir "samples\chest_xray_pa.png" }
if (-not (Test-Path $Image)) { throw "image not found: $Image" }

$health = & curl.exe -sS --max-time 5 "$BaseUrl/health"
if ($LASTEXITCODE -ne 0) {
    throw "cannot reach $BaseUrl - start .\deploy\tunnel.ps1 in another window first"
}
Write-Host "health: $health"

$curlArgs = @("-sS", "--max-time", "600", "-X", "POST", "$BaseUrl/$Mode")
if ($ApiKey) { $curlArgs += @("-H", "X-API-Key: $ApiKey") }
$curlArgs += @(
    "-F", "file=@$Image",
    "-F", "temperature=$Temperature",
    "-F", "top_p=$TopP"
)
if ($Mode -eq "ask") { $curlArgs += @("-F", "question=$Question") }

$response = & curl.exe @curlArgs
if ($LASTEXITCODE -ne 0) { throw "request failed (exit $LASTEXITCODE)" }

$result = $response | ConvertFrom-Json
if ($result.detail) { throw "server error: $($result.detail)" }

Write-Host ""
switch ($Mode) {
    "report"       { Write-Host $result.report }
    "differential" { Write-Host $result.differential }
    "ask"          { Write-Host "Q: $($result.question)"; Write-Host "A: $($result.answer)" }
}
Write-Host ""
Write-Host ("latency: {0}s" -f $result.latency_s)
