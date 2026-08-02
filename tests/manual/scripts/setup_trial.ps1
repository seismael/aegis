# =============================================================================
# Aegis Scientific Validation — setup_trial.ps1
# Creates a fresh TaskFlow project, installs Aegis rules, configures the agent.
# Run from PowerShell 5.1: .\setup_trial.ps1 -Task T2 -Agent opencode -Rules L2 -Mode with
# =============================================================================
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("T1","T2","T3","T4","T5","T6","T7","T8")]
    [string]$Task,
    [Parameter(Mandatory=$true)]
    [ValidateSet("opencode","claude","aider","gemini")]
    [string]$Agent,
    [Parameter(Mandatory=$true)]
    [ValidateSet("L0","L1","L2","L3","L4")]
    [string]$Rules,
    [Parameter(Mandatory=$true)]
    [ValidateSet("with","without")]
    [string]$Mode,
    [int]$Run = 0
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$manualRoot = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent (Split-Path -Parent $manualRoot)
$sourceProject = Join-Path $manualRoot "projects\taskflow"
$targetDir = Join-Path $repoRoot "taskflow"

# Determine trial number
if ($Run -eq 0) {
    $existing = Get-ChildItem (Join-Path $manualRoot "trials") -Directory -Filter "run_*" -ErrorAction SilentlyContinue
    $maxNum = 0
    if ($existing) {
        foreach ($e in $existing) {
            $num = [int]($e.Name -replace "run_", "")
            if ($num -gt $maxNum) { $maxNum = $num }
        }
    }
    $Run = $maxNum + 1
}
$trialId = "run_" + $Run.ToString("000")
$trialDir = Join-Path $manualRoot "trials\$trialId"
New-Item -ItemType Directory -Force -Path $trialDir | Out-Null

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " AEGIS MANUAL TESTING - SETUP $trialId" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Task:   $Task"
Write-Host "  Agent:  $Agent"
Write-Host "  Rules:  $Rules"
Write-Host "  Mode:   $Mode (aegis)"
Write-Host "================================================================" -ForegroundColor Cyan

# Step 1: Purge old project
if (Test-Path $targetDir) {
    Remove-Item -Recurse -Force $targetDir -ErrorAction SilentlyContinue
}

# Step 2: Copy fresh project template
Copy-Item -Recurse $sourceProject $targetDir

# Step 3: Initialize git
$gitDir = Join-Path $targetDir ".git"
if (Test-Path $gitDir) { Remove-Item -Recurse -Force $gitDir -ErrorAction SilentlyContinue }
Push-Location $targetDir
git -c user.name="AegisTester" -c user.email="test@aegis.local" init 2>$null | Out-Null
git -c user.name="AegisTester" -c user.email="test@aegis.local" add -A 2>$null | Out-Null
git -c user.name="AegisTester" -c user.email="test@aegis.local" commit -m "Initial TaskFlow project" 2>$null | Out-Null
Pop-Location

# Step 4: Write trial config
$config = @{
    trial_id = $trialId
    task = $Task
    agent = $Agent
    rules_level = $Rules
    mode = $Mode
    started_at = (Get-Date -Format "o")
    project_source = $sourceProject
    project_target = $targetDir
}
$config | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $trialDir "config.json")

# Step 5: Mode-specific setup
if ($Mode -eq "with") {
    Write-Host ""
    Write-Host "--- Installing Aegis ---" -ForegroundColor Cyan

    # 5a: Run aegis init to deploy AGENTS.md, MCP config, agent instructions
    # 5a: Deploy AGENTS.md with Aegis governance protocol
    $agentsTemplate = @"
# Aegis V4 Governance

You are governed by the Aegis Architectural Microkernel.

## Mandatory Protocol

Before declaring ANY coding task complete, you MUST:

1. Call ``check_architecture`` with the list of modified files.
2. If violations are returned, remediate the code natively.
3. Re-run validation until SUCCESS is returned.

## Available MCP Tools

| Tool | When to Use |
|------|-------------|
| ``check_architecture`` | Before every task completion |
| ``plan_architecture`` | Before editing a file |
| ``fetch_rubric`` | For domain language/naming checks |
| ``init_governance`` | Project initialization |
| ``query_graph`` | Dependency and architecture analysis |
| ``manage_rules`` | Add rules, suppress violations, manage packs |

Aegis is **stateless**. It does not remember your previous actions.
All state lives in your context window and ``.aegis/`` directory.

Do NOT disable or bypass Aegis governance for any reason.
"@
    $agentsMdPath = Join-Path $targetDir "AGENTS.md"
    Set-Content -Path $agentsMdPath -Value $agentsTemplate -Encoding UTF8
    Write-Host "  [OK] Created AGENTS.md" -ForegroundColor Green

    # 5b: Create .aegis/mcp.json for MCP config
    $mcpConfig = @{
        mcpServers = @{
            "aegis-kernel" = @{
                command = "uvx"
                args = @("aegis", "run")
            }
        }
    }
    $aegisDir = Join-Path $targetDir ".aegis"
    New-Item -ItemType Directory -Force -Path $aegisDir | Out-Null
    $mcpConfig | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $aegisDir "mcp.json")
    Write-Host "  [OK] Created .aegis/mcp.json" -ForegroundColor Green

    # 5b: Determine rule packs for this level
    $packs = @()
    if ($Rules -eq "L1") { $packs = @("architecture", "security") }
    if ($Rules -eq "L2") { $packs = @("architecture", "security", "best-practices", "style", "testing") }
    if ($Rules -eq "L3") { $packs = @("architecture", "security", "best-practices", "style", "testing", "design", "structure", "dependencies", "documentation") }
    if ($Rules -eq "L4") { $packs = @("architecture", "security", "best-practices", "style", "testing", "design", "structure", "dependencies", "documentation", "performance", "general", "infrastructure", "tools", "javascript-typescript", "go", "rust", "semantic") }

    if (($Rules -ne "L0") -and ($packs.Count -gt 0)) {
        $aegisRulesSrc = Join-Path $repoRoot "src\aegis\resources\default_rules"
        $rulesTarget = Join-Path $targetDir ".aegis" "rules"
        New-Item -ItemType Directory -Force -Path $rulesTarget | Out-Null

        $installedCount = 0
        foreach ($pack in $packs) {
            $packSrc = Join-Path $aegisRulesSrc $pack
            $packDst = Join-Path $rulesTarget $pack
            if (Test-Path $packSrc) {
                Copy-Item -Recurse $packSrc $packDst -ErrorAction SilentlyContinue
                $installedCount = $installedCount + 1
                Write-Host "  [OK] Installed pack: $pack" -ForegroundColor Green
            }
            else {
                Write-Host "  [WARN] Pack not found: $pack" -ForegroundColor Yellow
            }
        }
        $totalPacks = $packs.Count
        Write-Host "  Packs installed: $installedCount / $totalPacks" -ForegroundColor Cyan
    }

    # 5c: Verify
    Write-Host ""
    Write-Host "CHECKLIST - Verify BEFORE starting the agent:" -ForegroundColor Yellow
    $aegisDir = Join-Path $targetDir ".aegis"
    $agentsMd = Join-Path $targetDir "AGENTS.md"
    if (Test-Path $aegisDir) { Write-Host "  [X] .aegis/ directory exists" -ForegroundColor Green }
    else { Write-Host "  [ ] .aegis/ directory MISSING" -ForegroundColor Red }
    if (Test-Path $agentsMd) { Write-Host "  [X] AGENTS.md exists" -ForegroundColor Green }
    else { Write-Host "  [ ] AGENTS.md MISSING" -ForegroundColor Red }

    if ($Agent -eq "opencode") {
        Write-Host "  [ ] OpenCode: MCP tools (check_architecture, plan_architecture...) appear"
        Write-Host "  [ ] OpenCode: AGENTS.md governance protocol is followed"
    }
    if ($Agent -eq "claude") {
        Write-Host "  [ ] Claude Code: CLAUDE.md + MCP server 'aegis' in tool list"
    }
    if ($Agent -eq "aider") {
        Write-Host "  [ ] Aider: .aider.conf.yml has mcp-server and test-cmd"
    }
    if ($Agent -eq "gemini") {
        Write-Host "  [ ] Gemini: GEMINI.md + MCP server appears in tool list"
    }
}
else {
    Write-Host ""
    Write-Host "--- Removing Aegis traces ---" -ForegroundColor Cyan
    $toRemove = @(
        (Join-Path $targetDir ".aegis"),
        (Join-Path $targetDir "AGENTS.md"),
        (Join-Path $targetDir "CLAUDE.md"),
        (Join-Path $targetDir "GEMINI.md")
    )
    foreach ($path in $toRemove) {
        if (Test-Path $path) {
            Remove-Item -Recurse -Force $path -ErrorAction SilentlyContinue
            Write-Host "  Removed: $path"
        }
    }
    Write-Host ""
    Write-Host "CHECKLIST - Verify BEFORE starting the agent:" -ForegroundColor Yellow
    Write-Host "  [ ] NO .aegis/ directory"
    Write-Host "  [ ] NO AGENTS.md"
    Write-Host "  [ ] NO MCP server config"
    Write-Host "  [ ] Agent runs WITHOUT governance"
}

# Step 6: Print prompt
$promptsPath = Join-Path $manualRoot "prompts.json"
$promptText = ""
if (Test-Path $promptsPath) {
    $promptsContent = Get-Content $promptsPath -Raw
    $prompts = $promptsContent | ConvertFrom-Json
    if ($prompts.PSObject.Properties[$Task]) {
        $promptText = $prompts.$Task.prompt
    }
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host " PROMPT FOR $Task" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host $promptText -ForegroundColor White
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Trial:   $trialDir" -ForegroundColor Cyan
Write-Host "  Project: $targetDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "  NEXT STEPS:"
Write-Host "    1. cd $targetDir"
Write-Host "    2. $Agent"
Write-Host "    3. After agent finishes, copy terminal output to:"
Write-Host "       $trialDir\agent_output.txt"
Write-Host "    4. Record token counts in: $trialDir\tokens.json"
Write-Host "    5. Run: .\measure_trial.ps1 -TrialId $trialId"
Write-Host "================================================================" -ForegroundColor Green

$promptInfo = @{
    task = $Task
    prompt = $promptText
    prompted_at = (Get-Date -Format "o")
}
$promptInfo | ConvertTo-Json -Depth 2 | Set-Content (Join-Path $trialDir "prompt.json")
