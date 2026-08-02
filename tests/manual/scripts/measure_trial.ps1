# =============================================================================
# Aegis Scientific Validation — measure_trial.ps1
# Captures violations before/after, code diff, and token data.
# Runs AFTER the human has completed an agent interaction.
# =============================================================================
param(
    [Parameter(Mandatory=$true)]
    [string]$TrialId
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$manualRoot = Split-Path -Parent $scriptDir
$trialDir = Join-Path $manualRoot "trials" $TrialId

if (-not (Test-Path $trialDir)) {
    Write-Host "ERROR: Trial directory not found: $trialDir" -ForegroundColor Red
    exit 1
}

$configPath = Join-Path $trialDir "config.json"
if (-not (Test-Path $configPath)) {
    Write-Host "ERROR: config.json not found in $trialDir" -ForegroundColor Red
    exit 1
}

$config = Get-Content $configPath -Raw | ConvertFrom-Json
$projectDir = $config.project_target

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " AEGIS MANUAL TESTING — MEASURE $TrialId" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# 1. Check if agent output file exists
$agentOutputPath = Join-Path $trialDir "agent_output.txt"
if (-not (Test-Path $agentOutputPath)) {
    Write-Host "  WARN: agent_output.txt not found. Create it by pasting agent terminal output." -ForegroundColor Yellow
    Write-Host "  Create file at: $agentOutputPath" -ForegroundColor Yellow
} else {
    $outputSize = (Get-Item $agentOutputPath).Length
    Write-Host "  agent_output.txt: $outputSize bytes" -ForegroundColor Green
}

# 2. Run aegis headless-check to get current violations
Push-Location $projectDir
try {
    Write-Host "  Running: aegis run --headless-check"
    $checkOutput = aegis run --headless-check 2>&1
    $violationCount = 0
    if ($LASTEXITCODE -ne 0) {
        $violationCount = [int]$LASTEXITCODE
    }

    $violationsData = @{
        measured_at = (Get-Date -Format "o")
        exit_code = $LASTEXITCODE
        violation_count = $violationCount
        full_output = $checkOutput | Out-String
    }
    $violationsData | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $trialDir "violations_after.json")

    Write-Host "  Violations remaining: $violationCount" -ForegroundColor $(if ($violationCount -eq 0) { "Green" } else { "Red" })

    # 3. Get git diff to see what the agent changed
    $diff = git diff HEAD 2>&1 | Out-String
    if ($diff.Trim().Length -eq 0) {
        $diff = git diff 2>&1 | Out-String
    }
    if ($diff.Trim().Length -gt 0) {
        $diff | Set-Content (Join-Path $trialDir "code_diff.patch")
        Write-Host "  code_diff.patch saved" -ForegroundColor Green
    } else {
        Write-Host "  WARN: No diff detected (agent may not have changed anything)" -ForegroundColor Yellow
    }

    # 4. Count changed files
    $changedFiles = git diff --name-only HEAD 2>&1
    if (-not $changedFiles) { $changedFiles = git diff --name-only 2>&1 }
    $fileCount = ($changedFiles | Where-Object { $_.Trim().Length -gt 0 } | Measure-Object).Count

    $measurement = @{
        measured_at = (Get-Date -Format "o")
        violation_count = $violationCount
        changed_files_count = $fileCount
        changed_files = if ($changedFiles) { @($changedFiles | Where-Object { $_.Trim().Length -gt 0 }) } else { @() }
    }
} catch {
    $measurement = @{
        measured_at = (Get-Date -Format "o")
        error = $_.Exception.Message
    }
    Write-Host "  ERROR during measurement: $($_.Exception.Message)" -ForegroundColor Red
}
Pop-Location

$measurement | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $trialDir "measurement.json")

# 5. Prompt for manual token recording
Write-Host ""
Write-Host "================================================================" -ForegroundColor Yellow
Write-Host " MANUAL DATA ENTRY REQUIRED" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Yellow
Write-Host "  Create file: $trialDir\tokens.json"
Write-Host ""
Write-Host "  Template:"
Write-Host @'
{
  "agent": "opencode",
  "source": "manual_from_ui",
  "recorded_at": "2026-08-03T14:30:00Z",
  "input_tokens": 2450,
  "output_tokens": 820,
  "total_tokens": 3270,
  "turns": 3,
  "notes": "Agent completed in 3 turns. Plan gate caught import issue on turn 1."
}
'@
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " MEASUREMENT COMPLETE" -ForegroundColor Cyan
Write-Host "  Next: Review code diff and score quality" -ForegroundColor Cyan
Write-Host "  Diff: $trialDir\code_diff.patch" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
