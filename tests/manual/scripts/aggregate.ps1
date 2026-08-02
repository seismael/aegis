# =============================================================================
# Aegis Scientific Validation — aggregate.ps1
# Combines all trial data into experiment_results.csv
# =============================================================================
param(
    [string]$TrialsDir = $null
)

$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$manualRoot = Split-Path -Parent $scriptDir
if (-not $TrialsDir) {
    $TrialsDir = Join-Path $manualRoot "trials"
}

if (-not (Test-Path $TrialsDir)) {
    Write-Host "ERROR: Trials directory not found: $TrialsDir" -ForegroundColor Red
    exit 1
}

$trials = Get-ChildItem $TrialsDir -Directory -Filter "run_*" | Sort-Object Name

if ($trials.Count -eq 0) {
    Write-Host "No trial data found in $TrialsDir" -ForegroundColor Yellow
    exit 0
}

$results = @()

foreach ($trial in $trials) {
    $trialPath = $trial.FullName
    $configPath = Join-Path $trialPath "config.json"
    $tokensPath = Join-Path $trialPath "tokens.json"
    $measPath = Join-Path $trialPath "measurement.json"
    $checksumsPath = Join-Path $trialPath "checksums.json"

    $row = @{
        trial_id = $trial.Name
    }

    # Config
    if (Test-Path $configPath) {
        $cfg = Get-Content $configPath -Raw | ConvertFrom-Json
        $row.agent = $cfg.agent
        $row.task = $cfg.task
        $row.rules_level = $cfg.rules_level
        $row.mode = $cfg.mode
        $row.run_number = $cfg.run_number
        $row.started_at = $cfg.started_at
        $row.completed_at = if ($cfg.PSObject.Properties['completed_at']) { $cfg.completed_at } else { "" }
    }

    # Tokens
    if (Test-Path $tokensPath) {
        $tok = Get-Content $tokensPath -Raw | ConvertFrom-Json
        $row.input_tokens = $tok.input_tokens
        $row.output_tokens = $tok.output_tokens
        $row.total_tokens = $tok.total_tokens
        $row.turns = $tok.turns
        $row.token_source = $tok.source
    } else {
        $row.input_tokens = ""
        $row.output_tokens = ""
        $row.total_tokens = ""
        $row.turns = ""
        $row.token_source = "missing"
    }

    # Measurements
    if (Test-Path $measPath) {
        $meas = Get-Content $measPath -Raw | ConvertFrom-Json
        $row.violation_count = $meas.violation_count
        $row.changed_files = $meas.changed_files_count
        $row.measurement_error = if ($meas.PSObject.Properties['error']) { $meas.error } else { "" }
    } else {
        $row.violation_count = ""
        $row.changed_files = ""
        $row.measurement_error = "missing"
    }

    # Integrity
    if (Test-Path $checksumsPath) {
        $row.has_checksums = "true"
    } else {
        $row.has_checksums = "false"
    }

    $results += [PSCustomObject]$row
}

$outputPath = Join-Path $manualRoot "results\experiment_results.csv"
$results | Export-Csv -Path $outputPath -NoTypeInformation

Write-Host "================================================================" -ForegroundColor Green
Write-Host " AGGREGATION COMPLETE" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Trials processed: $($trials.Count)"
Write-Host "  Results saved to: $outputPath"
Write-Host "================================================================" -ForegroundColor Green

# Quick stats if we have token data
$withData = $results | Where-Object { $_.total_tokens -ne "" -and $_.mode -eq "with" }
$withoutData = $results | Where-Object { $_.total_tokens -ne "" -and $_.mode -eq "without" }

if ($withData.Count -gt 0 -and $withoutData.Count -gt 0) {
    $withAvg = ($withData | ForEach-Object { [int]$_.total_tokens } | Measure-Object -Average).Average
    $withoutAvg = ($withoutData | ForEach-Object { [int]$_.total_tokens } | Measure-Object -Average).Average

    if ($withoutAvg -gt 0) {
        $savings = (1 - ($withAvg / $withoutAvg)) * 100
        Write-Host ""
        Write-Host "  PRELIMINARY: Mean token savings: $([math]::Round($savings,1))%"
        Write-Host "  With Aegis avg:    $([math]::Round($withAvg,0)) tokens"
        Write-Host "  Without Aegis avg: $([math]::Round($withoutAvg,0)) tokens"
        Write-Host "  (Complete data collection for statistical significance)"
    }
}
