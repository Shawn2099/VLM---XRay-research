# Upload the MedGemma 1.5 4B model, service code and wheels, then verify hashes.
#
#   .\medgemma\push.ps1                # everything (~8.1 GiB)
#   .\medgemma\push.ps1 -SkipModel     # code + wheels only

[CmdletBinding()]
param(
    [string]$Server = "icccserver",
    [string]$RemoteRoot = "/home/iccc/medgemma",
    [string]$ModelRoot = "/home/iccc/models/medgemma-1.5-4b-it",
    [switch]$SkipModel
)

$ErrorActionPreference = "Stop"

$deployDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $deployDir
$modelDir = Join-Path $projectDir "medgemma-1.5-4b-it"
$sshOpts = @("-o", "LogLevel=ERROR")

function Invoke-Step {
    param([string]$Label, [scriptblock]$Action)
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "$Label failed (exit $LASTEXITCODE)" }
}

Write-Host "== creating remote directories"
Invoke-Step "mkdir" {
    ssh @sshOpts $Server "mkdir -p '$RemoteRoot/deploy/wheels' '$RemoteRoot/deploy/samples' '$ModelRoot'"
}

$availGb = [int](ssh @sshOpts $Server "df -BG --output=avail /home | tail -1 | tr -dc '0-9'")
if (-not $SkipModel -and $availGb -lt 12) {
    throw "server has only ${availGb}G free under /home; need at least 12G for the 8.1 GiB model"
}
Write-Host "   free space: ${availGb}G"

Write-Host "== uploading service files"
foreach ($name in @("app.py", "ui.html", "Dockerfile", ".dockerignore",
                    "build_and_run.sh", "smoke_test.py")) {
    Invoke-Step "upload $name" {
        scp -q (Join-Path $deployDir $name) "${Server}:${RemoteRoot}/deploy/"
    }
}
foreach ($name in @("chest_xray_pa.png", "ATTRIBUTION.txt")) {
    Invoke-Step "upload sample $name" {
        scp -q (Join-Path $deployDir "samples\$name") "${Server}:${RemoteRoot}/deploy/samples/"
    }
}
Invoke-Step "upload switch.sh" {
    scp -q (Join-Path $deployDir "switch.sh") "${Server}:/home/iccc/switch.sh"
    ssh @sshOpts $Server "chmod +x /home/iccc/switch.sh"
}

Write-Host "== uploading wheels"
$wheels = Get-ChildItem (Join-Path $deployDir "wheels") -File
foreach ($wheel in $wheels) {
    Invoke-Step "upload $($wheel.Name)" {
        scp -q $wheel.FullName "${Server}:${RemoteRoot}/deploy/wheels/"
    }
}
Write-Host "   $($wheels.Count) wheels uploaded"

if (-not $SkipModel) {
    Write-Host "== uploading MedGemma model (8.1 GiB)"
    Get-ChildItem $modelDir -File | Sort-Object Length | ForEach-Object {
        Write-Host ("   {0,9:N1} MB  {1}" -f ($_.Length / 1MB), $_.Name)
        Invoke-Step "upload $($_.Name)" {
            scp $_.FullName "${Server}:${ModelRoot}/"
        }
    }

    Write-Host "== verifying SHA-256 of the two shards"
    $expected = @{}
    foreach ($name in @("model-00001-of-00002.safetensors",
                        "model-00002-of-00002.safetensors")) {
        $expected[$name] = (Get-FileHash (Join-Path $modelDir $name) -Algorithm SHA256).Hash.ToLower()
    }
    $remote = ssh @sshOpts $Server "cd '$ModelRoot' && sha256sum model-00001-of-00002.safetensors model-00002-of-00002.safetensors"
    $actual = @{}
    foreach ($line in $remote) {
        if ($line -match '^([0-9a-f]{64})\s+(.+)$') { $actual[$Matches[2].Trim()] = $Matches[1] }
    }
    foreach ($name in $expected.Keys) {
        if ($actual[$name] -ne $expected[$name]) {
            throw "hash mismatch for $name`n  local:  $($expected[$name])`n  remote: $($actual[$name])"
        }
        Write-Host "   OK  $name"
    }
}

Write-Host ""
Write-Host "Upload complete. Next:"
Write-Host "  ssh $Server 'bash $RemoteRoot/deploy/build_and_run.sh'"
Write-Host "  .\medgemma\switch.ps1 -Model medgemma"
Write-Host "  python test\evaluate_api.py --api-key <KEY> --temperature 0"
