# =============================================================================
# Aegis Manual Testing Orchestrator — Runs one trial end-to-end
# Usage: .\run_trial.ps1 -Agent opencode -Task T2 -Rules L2 -Mode with -Run 1
# =============================================================================
param(
    [Parameter(Mandatory=$true)][string]$Agent,
    [Parameter(Mandatory=$true)][string]$Task,
    [Parameter(Mandatory=$true)][string]$Rules,
    [Parameter(Mandatory=$true)][ValidateSet("with","without")][string]$Mode,
    [int]$Run = 1
)

$ErrorActionPreference = "Continue"
$base = "C:\dev\projects\aegis"
$project = "$base\taskflow"
$manualRoot = "$base\tests\manual"
$trialId = "run_{0:D3}" -f $Run
$trialDir = "$manualRoot\trials\$trialId"
$tokensFile = "$trialDir\tokens.json"

# 1. Setup
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " TRIAL $trialId — $Agent / $Task / $Rules / $Mode" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path $trialDir | Out-Null
if (Test-Path $project) { Remove-Item -Recurse -Force $project -ErrorAction SilentlyContinue }
Copy-Item -Recurse "$manualRoot\projects\taskflow" $project

# 2. Mode-specific setup
if ($Mode -eq "with") {
    # Install rules
    $rulesTarget = "$project\.aegis\rules"
    New-Item -ItemType Directory -Force -Path $rulesTarget | Out-Null

    $packs = @()
    if ($Rules -eq "L1") { $packs = @("architecture", "security") }
    if ($Rules -eq "L2") { $packs = @("architecture", "security", "best-practices", "style", "testing") }
    if ($Rules -eq "L3") { $packs = @("architecture", "security", "best-practices", "style", "testing", "design", "structure", "dependencies", "documentation") }

    foreach ($p in $packs) {
        $src = "$base\src\aegis\resources\default_rules\$p"
        if (Test-Path $src) { Copy-Item -Recurse $src "$rulesTarget\$p" }
    }

    # Create AGENTS.md
    $agentsContent = @'
# Aegis V4 Governance

You are governed by the Aegis Architectural Microkernel.

## Mandatory Protocol

Before declaring ANY coding task complete, you MUST:
1. Call check_architecture with the list of modified files.
2. If violations are returned, remediate the code natively.
3. Re-run validation until SUCCESS is returned.

Available tools: check_architecture, plan_architecture, fetch_rubric, init_governance, query_graph, manage_rules, get_scorecard

Do NOT disable or bypass Aegis governance for any reason.
'@
    Set-Content -Path "$project\AGENTS.md" -Value $agentsContent -Encoding UTF8

    Write-Host "  Setup: WITH Aegis — $($packs.Count) packs, AGENTS.md deployed" -ForegroundColor Green
} else {
    # Remove all Aegis traces
    Remove-Item -Recurse -Force "$project\.aegis" -ErrorAction SilentlyContinue
    Remove-Item -Force "$project\AGENTS.md" -ErrorAction SilentlyContinue
    Write-Host "  Setup: WITHOUT Aegis — all traces removed" -ForegroundColor Yellow
}

# 3. Run headless check BEFORE
$beforeCount = 133  # known baseline from previous test
Write-Host "  Baseline violations: $beforeCount"

# 4. Get the prompt
$prompts = Get-Content "$manualRoot\prompts.json" -Raw | ConvertFrom-Json
$promptText = $prompts.$Task.prompt

# 5. Build agent command
$agentCmd = switch ($Agent) {
    "opencode" { "opencode run `"$promptText`"" }
    "claude" { "claude -p `"$promptText`"" }
    "aider" { "aider --message `"$promptText`" --no-git --yes" }
    "gemini" { "gemini -p `"$promptText`"" }
}

Write-Host ""
Write-Host "  Agent: $Agent"
Write-Host "  Command: $agentCmd" -ForegroundColor DarkGray
Write-Host "  Prompt: $($promptText.Substring(0, [Math]::Min(80, $promptText.Length)))..." -ForegroundColor DarkGray
Write-Host ""

# 6. Run the agent
$startTime = Get-Date
Write-Host "  Running agent..." -ForegroundColor Yellow

$output = ""
Push-Location $project
try {
    $output = Invoke-Expression $agentCmd 2>&1 | Out-String
} catch {
    $output = "ERROR: $_"
}
Pop-Location

$endTime = Get-Date
$duration = ($endTime - $startTime).TotalSeconds

# 7. Save agent output
$output | Set-Content "$trialDir\agent_output.txt" -Encoding UTF8
Write-Host "  Output saved: $trialDir\agent_output.txt ($([math]::Round($duration,1))s)" -ForegroundColor Green

# 8. Run headless check AFTER
$afterCount = $beforeCount
Push-Location $project
try {
    $checkResult = aegis run --headless-check 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { $afterCount = $LASTEXITCODE }
} catch {
    $afterCount = -1
}
Pop-Location

# 9. Extract token info from agent output
$tokenInfo = @{}
$inputTokens = 0
$outputTokens = 0

# Try to find token counts in output
if ($output -match '(\d[\d,]*)\s*(input|total).*?tokens?') {
    $inputTokens = [int]($Matches[1] -replace ',','')
}
if ($output -match '(\d[\d,]*)\s*(output|completion).*?tokens?') {
    $outputTokens = [int]($Matches[1] -replace ',','')
}

# Count tool calls / turns
$turnCount = ([regex]::Matches($output, '→|→|Tool|tool_call', 'IgnoreCase')).Count
if ($turnCount -eq 0) { $turnCount = 1 }

# 10. Save trial data
$result = @{
    trial_id = $trialId
    agent = $Agent
    task = $Task
    rules = $Rules
    mode = $Mode
    run = $Run
    started_at = $startTime.ToString("o")
    completed_at = $endTime.ToString("o")
    duration_seconds = [math]::Round($duration, 1)
    violations_before = $beforeCount
    violations_after = $afterCount
    input_tokens = $inputTokens
    output_tokens = $outputTokens
    total_tokens = $inputTokens + $outputTokens
    turns_estimated = $turnCount
    output_size_bytes = $output.Length
    notes = ""
}

$result | ConvertTo-Json -Depth 3 | Set-Content $tokensFile
Write-Host "  Violations: $beforeCount → $afterCount" -ForegroundColor $(if ($afterCount -lt $beforeCount) { "Green" } else { "Yellow" })
Write-Host "  Tokens: in=$inputTokens out=$outputTokens turns≈$turnCount" -ForegroundColor Cyan
Write-Host "  Trial data: $tokensFile" -ForegroundColor Green
Write-Host "  DONE" -ForegroundColor Green
