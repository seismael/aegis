# =============================================================================
# Aegis Scientific Validation — tear_down_trial.ps1
# Archives trial data and purges the project workspace.
# =============================================================================
param(
    [Parameter(Mandatory=$true)]
    [string]$TrialId
)

$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$manualRoot = Split-Path -Parent $scriptDir
$trialDir = Join-Path $manualRoot "trials" $TrialId

if (-not (Test-Path $trialDir)) {
    Write-Host "ERROR: Trial directory not found: $trialDir" -ForegroundColor Red
    exit 1
}

$configPath = Join-Path $trialDir "config.json"
$config = if (Test-Path $configPath) { Get-Content $configPath -Raw | ConvertFrom-Json } else { $null }
$projectDir = if ($config) { $config.project_target } else { $null }

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " AEGIS MANUAL TESTING — TEARDOWN $TrialId" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# 1. Record completion time
if ($config) {
    $config = Get-Content $configPath -Raw | ConvertFrom-Json
    $config | Add-Member -NotePropertyName "completed_at" -NotePropertyValue (Get-Date -Format "o") -Force
    $config | ConvertTo-Json -Depth 3 | Set-Content $configPath
}

# 2. Compute checksums of trial data files for tamper-proofing
$checksums = @{}
Get-ChildItem $trialDir -File | ForEach-Object {
    $hash = (Get-FileHash -Path $_.FullName -Algorithm SHA256).Hash
    $checksums[$_.Name] = $hash
}
$checksums | ConvertTo-Json | Set-Content (Join-Path $trialDir "checksums.json")
Write-Host "  Checksums recorded for all trial files" -ForegroundColor Green

# 3. Purge project directory
if ($projectDir -and (Test-Path $projectDir)) {
    try {
        Remove-Item -Recurse -Force $projectDir
        Write-Host "  Purged: $projectDir" -ForegroundColor Green
    } catch {
        Write-Host "  WARN: Could not fully purge $projectDir — $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# 4. Print summary
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host " TRIAL $TrialId COMPLETE — ARCHIVED" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Files in: $trialDir"
Get-ChildItem $trialDir -File | ForEach-Object {
    $size = "{0:N0}" -f $_.Length
    Write-Host "    $($_.Name) ($size bytes)"
}
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  READY FOR NEXT TRIAL" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
