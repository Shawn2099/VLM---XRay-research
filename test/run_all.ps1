# Run every API test against the deployed service.
#
#   .\test\run_all.ps1 -ApiKey <key>
#
# Requires the service to be reachable on the LAN (or through a tunnel) and
# test/data/openi/metadata.jsonl to exist (python test/fetch_openi.py).

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ApiKey,
    [string]$BaseUrl = "http://10.10.10.28:8000",
    [int]$Limit = 0
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$out = Join-Path $root "test\results"
New-Item -ItemType Directory -Force $out | Out-Null
$log = Join-Path $out "run.log"
"" | Set-Content $log -Encoding utf8

function Run($label, $script, $extra) {
    Write-Host "`n=== $label ==="
    "`n=== $label ===" | Add-Content $log
    $pyArgs = @($script, "--base-url", $BaseUrl, "--api-key", $ApiKey) + $extra
    & python @pyArgs 2>&1 | Tee-Object -FilePath $log -Append
    if ($LASTEXITCODE -ne 0) { throw "$label failed (exit $LASTEXITCODE)" }
}

Write-Host "health:"
Invoke-RestMethod "$BaseUrl/health" | ConvertTo-Json -Compress

$config = Invoke-RestMethod "$BaseUrl/config"
$backend = if ($config.model -match "medgemma") { "medgemma" } else { "cxr" }
if ($backend -eq "medgemma") {
    $t0Out = "test\results\medgemma_t0"
    $t02Out = "test\results\medgemma_t02"
    $qaOut = "test\results\medgemma_qa.json"
} else {
    $t0Out = "test\results\report_t0"
    $t02Out = "test\results\report_t02"
    $qaOut = "test\results\qa.json"
}
Write-Host "backend: $backend ($($config.model))"

Run "edge cases" "test\edge_cases.py" @()
if ($Limit -gt 0) {
    Run "report t=0" "test\evaluate_api.py" @(
        "--temperature", "0", "--limit", "$Limit",
        "--out", "${t0Out}_limited"
    )
} else {
    Run "report t=0" "test\evaluate_api.py" @(
        "--temperature", "0", "--out", $t0Out
    )
}
$subset = if ($Limit -gt 0) { $Limit } else { 30 }
$t02RunOut = if ($Limit -gt 0) { "${t02Out}_limited" } else { $t02Out }
Run "report t=0.2 (subset)" "test\evaluate_api.py" @(
    "--temperature", "0.2", "--limit", "$subset", "--out", $t02RunOut
)
Run "QA" "test\qa_test.py" @("--limit", "25", "--out", $qaOut)
Run "concurrency" "test\concurrency_test.py" @("--workers", "3")

Write-Host "`nAll test suites passed. Results in $out"
