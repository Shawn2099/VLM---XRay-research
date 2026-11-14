# Upload the model, wheels and service code to icccserver, then verify hashes.
#
#   .\deploy\push.ps1                 # everything (~13 GiB)
#   .\deploy\push.ps1 -SkipModel      # only service code + wheels
#   .\deploy\push.ps1 -SkipWheels     # only model + service code

[CmdletBinding()]
param(
    [string]$Server = "icccserver",
    [string]$RemoteRoot = "/home/iccc/cxr-llava",
    [switch]$SkipModel,
    [switch]$SkipWheels
)

$ErrorActionPreference = "Stop"

$deployDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $deployDir
$modelDir = Join-Path $projectDir "model"
$sshOpts = @("-o", "LogLevel=ERROR")

function Invoke-Step {
    param([string]$Label, [scriptblock]$Action)
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Label failed (exit $LASTEXITCODE)" }
}

Write-Host "== creating remote directories"
Invoke-Step "mkdir" {
    ssh @sshOpts $Server "mkdir -p '$RemoteRoot/model' '$RemoteRoot/deploy/wheels' '$RemoteRoot/deploy/samples'"
}

$availGb = [int](ssh @sshOpts $Server "df -BG --output=avail '$RemoteRoot' | tail -1 | tr -dc '0-9'")
if (-not $SkipModel -and $availGb -lt 16) {
    throw "server has only ${availGb}G free under $RemoteRoot; need at least 16G for the 13 GiB model"
}
Write-Host "   free space: ${availGb}G"

Write-Host "== uploading service files"
foreach ($name in @("app.py", "Dockerfile", ".dockerignore", "build_and_run.sh", "smoke_test.py", "make_test_dicom.py", "ui.html", "PLAN.md")) {
    Invoke-Step "upload $name" {
        scp -q (Join-Path $deployDir $name) "${Server}:${RemoteRoot}/deploy/"
    }
}
foreach ($name in @("chest_xray_pa.png", "ATTRIBUTION.txt")) {
    Invoke-Step "upload sample $name" {
        scp -q (Join-Path $deployDir "samples\$name") "${Server}:${RemoteRoot}/deploy/samples/"
    }
}

if (-not $SkipWheels) {
    Write-Host "== uploading Python wheels"
    $wheels = Get-ChildItem (Join-Path $deployDir "wheels") -File
    foreach ($wheel in $wheels) {
        Invoke-Step "upload $($wheel.Name)" {
            scp -q $wheel.FullName "${Server}:${RemoteRoot}/deploy/wheels/"
        }
    }
    Write-Host "   $($wheels.Count) wheels uploaded"
}

if (-not $SkipModel) {
    Write-Host "== uploading model files (13.1 GiB)"
    Get-ChildItem $modelDir -File | Sort-Object Length | ForEach-Object {
        Write-Host ("   {0,9:N1} MB  {1}" -f ($_.Length / 1MB), $_.Name)
        Invoke-Step "upload $($_.Name)" {
            scp $_.FullName "${Server}:${RemoteRoot}/model/"
        }
    }

    Write-Host "== verifying remote SHA-256 (reads 13 GiB, takes about a minute)"
    $expected = [ordered]@{
        "model-00001-of-00003.safetensors" = "2a30a3337ea0e778627c417863e19621d3df385d2b843ac98c97fd23737f5053"
        "model-00002-of-00003.safetensors" = "6f34846c3dcbf1115a4ed3992fbd3325729a3991bae7ff6418fd6161c561a604"
        "model-00003-of-00003.safetensors" = "42a5c74885378cc22d42cd4d2159e648fd5a13821c22a7c7daef33cdf31c53e7"
        "tokenizer.model"                  = "9e556afd44213b6bd1be2b850ebbbd98f5481437a8021afaf58ee7fb1818d347"
    }
    $remote = ssh @sshOpts $Server "cd '$RemoteRoot/model' && sha256sum model-00001-of-00003.safetensors model-00002-of-00003.safetensors model-00003-of-00003.safetensors tokenizer.model"
    $actual = @{}
    foreach ($line in $remote) {
        if ($line -match '^([0-9a-f]{64})\s+(.+)$') { $actual[$Matches[2].Trim()] = $Matches[1] }
    }
    foreach ($name in $expected.Keys) {
        if (-not $actual.ContainsKey($name)) { throw "missing on server: $name" }
        if ($actual[$name] -ne $expected[$name]) {
            throw "hash mismatch for $name`n  local:  $($expected[$name])`n  remote: $($actual[$name])"
        }
        Write-Host "   OK  $name"
    }
}

Write-Host ""
Write-Host "Upload complete. Next:"
Write-Host "  ssh $Server 'bash $RemoteRoot/deploy/build_and_run.sh'"
Write-Host "  .\deploy\tunnel.ps1        # second terminal"
Write-Host "  .\deploy\test_client.ps1"
