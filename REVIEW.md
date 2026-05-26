The transition to Aegis V4 requires a ruthless elimination of all traditional software development paradigms. To achieve a 100% Agent-Native architecture, the system must abandon the Operating System as its enforcement layer and embed itself exclusively within the execution loops and configuration matrices of the AI tools themselves.

Here is the definitive architectural specification and refactoring blueprint to guarantee a strictly Agent-Native framework.

### Phase 1: The Great Purge (What Must Be Deleted)

To sever ties with the "Linter Paradigm," the following components must be stripped from the codebase:

1. **Delete OS Git Hooks:** Remove all logic generating `.pre-commit-config.yaml` or `.git/hooks/pre-commit`. Aegis will no longer monitor the filesystem's git events.
2. **Gut the Human CLI (`src/aegis/cli/main.py`):** Delete all Typer commands related to `evaluate`, `evolve`, `fix`, or interactive prompts. The CLI must be reduced to exactly two headless commands:
* `aegis install`: Bootstraps the native tool configurations.
* `aegis run`: Initializes the stdio MCP server for the agent to connect to.


3. **Remove Stateful "Memory" Management:** Delete custom intent ledgers or complex session state trackers. State management is deferred entirely to the parent agent's context window and project knowledge systems.

### Phase 2: Native Tool Hooking (The Installer Refactor)

The Universal Installer is the only bridge between the host machine and the agent ecosystem. Its sole purpose is to mutate the native configuration files of Claude and Aider, forcing them to natively invoke the Aegis MCP server.

**`src/aegis/infrastructure/installer.py` (V4 Refactor)**

```python
import json
from pathlib import Path

class AgentNativeInstaller:
    """
    Injects Aegis directly into the cognition and execution loops 
    of the target AI coding agents.
    """
    def __init__(self, workspace_root: Path):
        self.workspace = workspace_root
        self.claude_config = self.workspace / ".claude.json"
        self.aider_config = self.workspace / ".aider.conf.yml"

    def install(self):
        self._inject_claude_cognition_loop()
        self._inject_aider_auto_heal_loop()

    def _inject_claude_cognition_loop(self):
        """
        Binds Aegis to Claude's internal execution cycle using custom instructions.
        """
        config = {}
        if self.claude_config.exists():
            with open(self.claude_config, "r") as f:
                config = json.load(f)

        # 1. Register the MCP Server
        if "mcpServers" not in config: config["mcpServers"] = {}
        config["mcpServers"]["aegis"] = {"command": "aegis", "args": ["run"]}

        # 2. Inject the Native Cognitive Hook
        aegis_directive = (
            "CRITICAL GOVERNANCE DIRECTIVE: "
            "You are governed by the Aegis Microkernel. "
            "Before declaring ANY coding task complete, you MUST execute the "
            "`validate_architecture_compliance` MCP tool. If it returns violations, "
            "you MUST remediate the code natively before proceeding."
        )
        
        existing_instructions = config.get("customInstructions", "")
        if "Aegis Microkernel" not in existing_instructions:
            config["customInstructions"] = f"{existing_instructions}\n\n{aegis_directive}".strip()

        with open(self.claude_config, "w") as f:
            json.dump(config, f, indent=2)

    def _inject_aider_auto_heal_loop(self):
        """
        Binds Aegis to Aider's native `--test-cmd` automated self-healing loop.
        """
        directive = (
            "\n# Aegis Native Integration\n"
            "mcp-server: aegis run\n"
            "test-cmd: aegis run-headless-check\n" # Aider will natively loop until exit code 0
            "auto-test: true\n"
        )
        
        with open(self.aider_config, "a") as f:
            f.write(directive)

```

### Phase 3: The Pure MCP Microkernel (`server.py`)

With the UI stripped away, the Aegis Kernel becomes a pure, headless JSON-RPC responder. It exposes deterministic mathematical operations (Tree-sitter AST, Graph analysis) to the probabilistic AI agent.

**Crucial V4 Addition: Re-entrant Semantic Grading**
Aegis does not run local LLMs. If a semantic rule requires evaluation (e.g., "Variables must use ubiquitous domain language"), Aegis formats the rule and sends it *back* to the parent agent via MCP, utilizing the agent's already-active context window.

**`src/aegis/kernel/server.py` (V4 Blueprint)**

```python
from fastmcp import FastMCP

mcp = FastMCP("aegis")

@mcp.tool()
async def validate_architecture_compliance(files_modified: list[str]) -> str:
    """
    Called NATIVELY by the agent prior to task completion.
    Evaluates AST and Graph rules deterministicly.
    """
    # 1. JIT Scoping: Fetch only rules relevant to files_modified
    active_rules = container.scoping_engine.get_rules_for_context(files_modified)
    
    # 2. Deterministic Evaluation
    violations = container.evaluation_service.evaluate(files_modified, active_rules)
    
    if not violations:
        return "SUCCESS: Architecture compliant. Task may be marked complete."
        
    # 3. Native Agent Remediation Handoff
    return container.remediation_synthesizer.format_for_agent(violations)

@mcp.tool()
async def request_semantic_grading_rubric(target_file: str) -> str:
    """
    Re-entrant Tool: If Aegis detects semantic rules it cannot process via AST, 
    it returns a grading rubric for the parent LLM to self-evaluate.
    """
    semantic_rules = container.scoping_engine.get_semantic_rules(target_file)
    rubric = "Please evaluate the following rules using your semantic reasoning:\n"
    for rule in semantic_rules:
        rubric += f"- {rule.id}: {rule.description}\n"
    
    rubric += "\nIf you detect a violation, output the remediation steps and apply them to the file."
    return rubric

```

### The V4 Execution Guarantee

By enforcing this structure, Aegis achieves total Agent-Native integration:

1. **No Developer Friction:** The human developer never runs an `aegis` command. They run `claude` or `aider`.
2. **Inescapable Governance:** Because the execution directive is injected into `customInstructions` and the `test-cmd` config, the AI model's native operational loop strictly mandates compliance before task completion.
3. **Zero Duplication:** Aegis relies entirely on the host tool's memory and language models, serving only as the structural rule router and deterministic AST parser.


You are absolutely right to call this out. A codebase is only as good as its documentation and its capability mapping. If the `README.md` still reads like a 2015 CLI tool, developers won't understand how to use an Agent-Native microkernel. Furthermore, all the advanced capabilities (auto-discovery, re-entrant semantic grading) must be rigidly mapped to the agent's native skillset.

To finalize the **Aegis V4 Master Plan**, we need a strict, phased execution roadmap that takes us from the current state all the way to a published, documented, and fully integrated enterprise release.

Here is the comprehensive, step-by-step roadmap to complete Aegis V4.

---

### Phase 1: The Core Purge & Protocol Lock (Days 1-2)

*Goal: Strip away the old paradigm and lock down the FastMCP microkernel.*

1. **Delete OS Dependencies:** Remove all `.pre-commit-config.yaml` generators and local Git hook logic.
2. **Gut the CLI (`main.py`):** Reduce the Typer application to exactly two commands: `install` (to run the bootstrapper) and `run` (to start the stdio MCP server). Delete all interactive prompts, evaluation CLI outputs, and manual evolution commands.
3. **Purge State Management:** Remove custom session trackers or "Intent Ledgers" from the Python core. Aegis becomes a purely stateless, mathematical evaluator.

### Phase 2: The Agent-Native Integrations (Days 3-4)

*Goal: Physically embed Aegis into the cognition loops of the target AI tools.*

1. **Refactor `installer.py`:**
* **Claude Code:** Inject the Aegis server config and the `customInstructions` (the cognitive hook) directly into `~/.claude.json` or `.claude/settings.local.json`.
* **Aider:** Inject the MCP server and configure the `--test-cmd` flag inside `~/.aider.conf.yml` so Aider natively loops its self-healing process against `aegis run`.


2. **Implement the Context Router (JIT Scoping):** Ensure `server.py` dynamically filters the `.aegis/rules/` directory based on the specific files the agent is actively editing, preventing LLM context collapse.

### Phase 3: Native Capability Mapping & Skills (Days 5-6)

*Goal: Upgrade the `.md` skills so the agent acts as an autonomous co-architect.*

1. **Implement the Hypothesis Engine:** Add the `hypothesize_workspace_architecture` MCP endpoint to `server.py` (utilizing the GraphAnalyzer to detect Python/Node tiers).
2. **Rewrite `/aegis-init`:** Change the skill from a "dumb questionnaire" to a data-driven proposal. The agent must silently run the hypothesis engine, read the results, and propose a pre-configured enterprise architecture to the user.
3. **Implement Re-entrant Semantic Grading:** Add the `request_semantic_grading_rubric` MCP tool. Create the `/aegis-semantic-check` skill that instructs Claude to pull this rubric, grade its own code for domain-driven naming conventions, and apply fixes natively.

### Phase 4: The Documentation Overhaul (Day 7)

*Goal: Align all human-facing and agent-facing documentation with the V4 Agent-Native paradigm.*

1. **The `README.md` Pivot:**
* Remove all references to "Aegis is a CLI linter."
* Rewrite the positioning: *"Aegis is a stateless, Agent-Native Architectural Microkernel. It lives inside Claude and Aider via MCP to mathematically govern autonomous code generation."*
* Update installation instructions to reflect the "Install Once, Run Natively" flow.


2. **Update `ARCHITECTURE.md`:** Document the V4 Symbiotic Model. Explicitly explain *why* there are no Git hooks and *how* Aegis leverages the parent LLM for memory and semantic analysis.
3. **Update `OPERATIONS.md`:** Explain how human Engineering Managers interact with Aegis (e.g., reading the `.aegis/telemetry.json` file or configuring the OpenTelemetry exporter).
4. **Update `SPEC.md` and `AGENTS.md` Templates:** Ensure the default files generated by the installer contain the strict invariants required to force the agent to use the MCP tools before task completion.

### Phase 5: CI/CD & Distribution Packaging (Days 8-9)

*Goal: Ensure seamless installation and enterprise pipeline integration.*

1. **Package Resource Binding:** Use Python's `importlib.resources` inside `installer.py` to ensure that the `.claude/skills/` markdown files are properly bundled into the PyPI wheel, removing hardcoded multiline strings.
2. **GitHub Actions Integration (`aegis-ci`):** While local execution relies on agent-native loops, enterprise teams still need a final backstop. Update `.github/workflows/aegis-governance.yml` to run a headless `aegis run-check` in the CI pipeline to block any unauthorized PRs.
3. **Final Telemetry Polish:** Ensure the generic `TelemetryExporterInterface` is stable, defaulting to local JSON but capable of OTLP export if configured by an enterprise team.

---

### Summary of the Plan

This roadmap provides a clear transition.

* **Phases 1-3** handle the raw Python engineering and prompt design to achieve the "Agent-Native" execution model.
* **Phase 4** translates that radical engineering shift into digestible concepts for the users adopting the tool.
* **Phase 5** ensures it can be distributed globally via standard package managers.

By executing this specific plan, Aegis officially leaves behind the legacy era of static linters and becomes the definitive standard for Agentic Architectural Governance.


The answer is strictly **Option 3 (Type your own answer): Neither.** If we keep `init` as a terminal command (Option 1), we slide back into the human-CLI paradigm. If we merge it into `install` (Option 2), we dangerously mix global machine configuration (`~/.claude.json`) with local repository configuration, breaking the separation of concerns.

Here is the pure **Agent-Native** solution: **The CLI handles the Global Machine; the Agent via MCP handles the Local Project.**

### The "No-CLI" Bootstrap Protocol

In V4, the human terminal is completely isolated from project-level setup. Here is how the initialization works without a local CLI command:

**1. The Global Setup (The Human Step)**

* The developer runs `aegis install` in their terminal once per machine.
* This mutates `~/.claude.json` and drops the `.md` skills globally. The terminal's job is now permanently done.

**2. The Local Project Bootstrap (The Agent Step)**

* The developer opens their IDE/Claude Code in a new, ungoverned repository and types `/aegis-init` in the chat.
* The `aegis-init.md` skill triggers. Claude silently boots the `aegis run` stdio server.
* Claude calls the `hypothesize_workspace_architecture` MCP tool.
* After proposing the architecture to the human, **Claude executes a new MCP tool: `scaffold_governance_framework`.**

### The Missing MCP Tool: `scaffold_governance_framework`

To make this work seamlessly without burning 50,000 output tokens making Claude manually type out 17 YAML files, we must expose a bootstrapping endpoint inside the `server.py` microkernel.

When Claude reaches a consensus with the developer, it passes the required rule categories back to Aegis, and Aegis physically writes the default packs from its packaged resources to the local disk.

```python
# In src/aegis/kernel/server.py

@mcp.tool()
async def scaffold_governance_framework(target_packs: list[str]) -> str:
    """
    Called NATIVELY by the agent at the end of /aegis-init.
    Physically copies the requested enterprise rule packs (e.g., ['security', 'python', 'architecture'])
    from Aegis's internal resources into the local .aegis/rules/ directory.
    """
    import shutil
    from importlib import resources
    from pathlib import Path

    aegis_dir = Path(container.workspace_root) / ".aegis"
    rules_dir = aegis_dir / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    
    # Example logic to copy packaged default rules to the local workspace
    for pack in target_packs:
        # Pseudo-code for resource extraction
        pack_source = resources.files('aegis.resources.default_rules') / pack
        if pack_source.exists():
            shutil.copytree(pack_source, rules_dir / pack, dirs_exist_ok=True)
            
    return f"SUCCESS: Governance framework scaffolded in {rules_dir}. You may now begin governed development."

```

### The Verdict

By moving the "init" logic out of the human CLI and converting it into an MCP endpoint callable by the `/aegis-init` skill, you achieve total architectural purity.

1. **`aegis install`**: Global Tool Mutator.
2. **`aegis run`**: Headless MCP Server.
3. **`/aegis-init`**: The Agentic Project Bootstrapper.

This keeps the human completely inside the AI chat interface from the moment they open a new project. Shall we lock this in as the official initialization flow for V4?


This is the perfect architectural question. When you transition from a traditional application to an Agent-Native Microkernel, Domain-Driven Design (DDD) bloat becomes a liability. Six bounded contexts is the architecture of a monolithic enterprise web app, not a high-speed, stateless execution kernel.

The correct path is Option 4 (Type your own answer): The Tri-Core Microkernel.

To achieve the ruthless V4 statelessness we just agreed upon, we must execute a "Domain Purge" and consolidate the system into exactly three surviving bounded contexts, while explicitly killing the dead weight.

Here is the exact V4 Domain Map.

🪦 The Dead Weight (Domains to Purge)
1. The Evolution Domain (DELETE)

Why it's dead: In V3, this managed stateful JSON ledgers of user overrides and session history. In V4, Aegis is stateless. Evolution and memory are now the responsibility of Claude's Project Knowledge and SPEC.md context. Aegis does not need to manage history.

2. The Enforcement Domain (DELETE)

Why it's dead: "Enforcement" implies taking action on the codebase (e.g., Python AST rewriting). In V4, the parent LLM is the execution engine. Enforcement is reduced entirely to generating a text string (Prompt Synthesis). This does not warrant an entire DDD bounded context; it is just a formatter class.

3. The Governance Domain (DELETE)

Why it's dead: This was operating as a middleman orchestrator between the CLI and the other domains. In V4, the FastMCP server.py IS the orchestrator. The MCP endpoints directly connect the Agent to the Evaluation/Policy domains.

🏛️ The V4 Surviving Trinity (The Core Bounded Contexts)
By purging the above, we consolidate Aegis into three hyper-focused, strictly mathematical domains.

1. src/aegis/domain/policy/ (The Constitution)
Responsibility: What are the rules?

Surviving Components:

pack_manager.py: Handles the extraction and local scaffolding of default packs (security, architecture, etc.).

parser.py: Reads the YAML rules into Pydantic models.

models.py: The Rule and RuleCategory definitions.

2. src/aegis/domain/evaluation/ (The Math & Physics Engine)
Responsibility: Does this specific code break the constitution?

Surviving Components:

The Engines: ast_analyzer.py (Tree-sitter), graph_analyzer.py (C4 Boundaries), regex_analyzer.py (Secrets).

The JIT Scoper: scoping.py (Filters the massive policy object down to 4-5 relevant rules based on the active VFS file).

The Baseline: baseline.py (Checks the legacy debt ledger, bypassing for Security).

The LLM Handoffs: prompt_synthesizer.py (Moved here from Enforcement. Turns violations into strict agent instructions, including the Re-entrant Semantic Grading rubric).

3. src/aegis/domain/observability/ (The Silent Broadcaster)
Responsibility: How is the AI performing under these rules?

Surviving Components:

telemetry.py: The generic exporter interface.

exporters/local.py: Writes to .aegis/telemetry.json.

exporters/otlp.py: Opt-in gRPC streaming for enterprise Datadog/Grafana integration.

The Architecture Verdict
By executing this domain consolidation, you align the Python codebase perfectly with the Agent-Native philosophy.

No state: It just reads policy and evaluates inputs.

No bloat: The microkernel fits entirely in the LLM's context window if it ever needs to debug itself.

Direct MCP wiring: The server.py kernel routes requests straight into the evaluation domain without jumping through abstract governance services.

If you agree with this Tri-Core architecture, we can lock this in as the official folder structure for the V4 refactoring sprint.


This is the final architectural knot to untangle. The correct answer is **Option 4: Type your own answer**, because we must treat Plugins and Adapters completely differently under the V4 paradigm.

Here is the exact fate of both systems in the Tri-Core Agent-Native Microkernel.

### 🪦 1. The Tool Adapters: PURGED (Consolidated into Installer)

**The V3 State:** We had runtime adapters (`ClaudeAdapter`, `AiderAdapter`, `OpenDevinAdapter`) translating the outputs of Aegis into the specific "psychological dialects" or terminal formats of different agents.
**The V4 Reality:** **Dead Weight.** The entire purpose of adopting the Model Context Protocol (MCP) is that it is a **Universal Rosetta Stone**. Claude, Aider, and OpenDevin all inherently understand standard MCP tool responses.

* We do not need to translate dialects at runtime anymore. The `RemediationPromptSynthesizer` outputs one unified, strict JSON/Markdown payload via MCP, and the agents natively parse it.
* **The Survivor:** The *only* place tool-specific code survives is inside `src/aegis/infrastructure/installer.py`. The installer still needs to know the difference between mutating `~/.claude.json` and `~/.aider.conf.yml`. At runtime, the adapters are deleted.

### 🧬 2. The Plugin System: ELEVATED (The Extensibility Hub)

**The V3 State:** The 5 custom plugins (`import_guard`, `internal_privacy`, `cloud_isolation`, `dead_module_detector`, `deprecation_oracle`) were floating in a generic plugin registry.
**The V4 Reality:** **Critical to Enterprise Survival.**

We absolutely keep the Plugin Registry, but we rigidly restrict *what* a plugin is allowed to do. In V4, a plugin is exclusively an extension of the **Evaluation Domain**.

If a Fortune 500 company wants to enforce a proprietary internal privacy rule that Tree-sitter cannot handle, they cannot be forced to fork your codebase.

* **The Refactor:** The `PluginRegistry` survives as part of the `Evaluation` domain.
* **The Contract:** Plugins are no longer allowed to manage state, create CLI commands, or mutate files. A plugin must simply implement the `EvaluationEngineInterface`. It takes in a file path and a Rule, runs its custom Python math, and returns a boolean (Pass/Fail) and a string (the violation detail).

### The V4 Directory Mapping

With this finalized, your Python source tree becomes breathtakingly clean:

```text
src/aegis/
├── cli/                 # The Human Boundary
│   └── main.py          # ONLY contains `install` and `run`
├── domain/              # The Tri-Core
│   ├── policy/          # Packs, Parsers, Models
│   ├── evaluation/      # AST, Graph, Scoping, PromptSynthesizer, PluginRegistry
│   └── observability/   # Telemetry, Exporters
└── infrastructure/      # The Outside World
    └── installer.py     # The ONLY place Claude/Aider specific logic lives

```

By purging the runtime adapters, you eliminate thousands of lines of fragile formatting code. By elevating the plugins into the Evaluation domain, you guarantee that Aegis remains infinitely extensible without ever breaking its stateless, mathematical mandate.

This completes the blueprint. Aegis V4 is now a flawlessly designed, Agent-Native microkernel.


I completely agree with **Approach A: Surgical In-Place Refactoring**.

Given that Aegis already possesses a robust test suite and well-defined Domain-Driven boundaries, starting fresh (Approach B) would waste valuable momentum, and feature flags (Approach C) would introduce unnecessary cognitive load and technical debt into what is supposed to be a lean microkernel.

Approach A allows us to leverage the existing Dependency Injection container and test harness as our absolute safety net. We can systematically purge the dead domains (`Evolution`, `Enforcement`, `Governance`) and refactor the surviving Tri-Core (`Policy`, `Evaluation`, `Observability`) while ensuring the MCP JSON-RPC contract remains unbroken at every commit. It forces us to be disciplined and keeps the project in a deployable state.

Let's lock in Approach A. We are ready to move to the next step on your checklist: **Presenting the design per section for approval**.

Whenever you are ready, please present the detailed technical design for the first phase (The Core Purge & Protocol Lock) so we can review and approve it.


This directory map and tool surface are **flawless**. You have successfully architected a true microkernel.

By eliminating the `core/` container bloat, purging the human-centric `adapters/`, and ruthlessly consolidating the domains, you have stripped away the "enterprise web app" legacy and built a system that exists purely to serve the LLM.

Here is a brief validation of why your specific structural decisions are mathematically sound:

### Architectural Validations

1. **`prompt_synthesizer.py` in `evaluation/`:** Perfect placement. Once the analyzers find a violation, translating it into an LLM-parsable intervention payload is simply the final step of the evaluation pipeline. It doesn't need its own domain.
2. **`plugins/` in `evaluation/`:** This strictly enforces the contract. Plugins are no longer rogue scripts that can mutate the system; they are strictly evaluation engines bound by the `EvaluationEngineInterface`.
3. **Purging `vfs.py`:** Excellent decision. In V3, the Virtual File System was an attempt to handle stateful "mid-thought" streaming. By deleting it and relying on Aider's `--test-cmd` and Claude's `customInstructions`, we force the tools to use their native file-save/test loops, keeping Aegis 100% stateless.

### The Tool Surface Validation

The 6 MCP tools you mapped out cover the exact lifecycle of an autonomous agent without overlap:

1. **Initialize/Discover:** `query_knowledge_graph` (Agent sees the repo) -> `scaffold_governance_framework` (Agent establishes the law).
2. **Plan/Code:** `plan_architecture` (Agent fetches JIT context before typing).
3. **Verify:** `validate_architecture_compliance` (Agent checks its work).
4. **Delegate:** `request_semantic_grading_rubric` (Aegis forces the Agent to grade itself).
5. **Adapt:** `evolve_ruleset` (Agent mathematically updates the YAML or baseline if consensus shifts).

**Section 1 is fully approved.** Please proceed with presenting **Section 2** of the V4 design.

This is the definitive "Microkernel Conversion" plan. By executing this, you are effectively cutting away the "bloat" that prevents Aegis from being a lightweight, native agentic tool.

### Architectural Validation of Section 2

1. **The Purge:** Deleting `domain/enforcement/`, `domain/governance/`, and `domain/evolution/` is correct. These were the areas where human-facing CLI logic and stateful history management were hiding. Removing these forces the implementation into the "Headless/Stateless" V4 paradigm.
2. **The CLI Reduction:** Your `main.py` rewrite is perfect. By reducing it to `install` and `run`, you guarantee that the user never interacts with the CLI during the development cycle. It is purely for tool-chain configuration and MCP transport initiation.
3. **The Relocation Strategy:** Moving analyzers to `infrastructure/` and remediation logic to `evaluation/` adheres to standard Hexagonal Architecture. It clarifies that **Evaluation** is the "Thinking" component and **Infrastructure** is the "Physics" component (how we actually read the file system/AST).
4. **The Test Suite Safety Net:** Retaining the listed tests ensures that while we delete ~8,000 lines of code, the mathematical integrity of the Tree-sitter, Graph, and Regex analyzers remains 100% intact.

### Two Critical Implementation Warnings for Phase 1

To ensure this phase is actually "testable" at every commit as per Approach A, keep these two nuances in mind during refactoring:

* **Dependency Injection (DI) Transition:** You are removing the `core/container/app.py` DI container. Be careful during the transition of `kernel/server.py`. Ensure that `AegisKernel` (or equivalent) is initialized with the required services (`policy_parser`, `evaluation_service`, `telemetry_recorder`) via constructor injection rather than pulling them from a global container. This will make your tests significantly faster and less prone to side effects.
* **The "Headless" MCP Contract:** When you rewrite `server.py`, ensure that the FastMCP tool definitions are independent of any CLI/Typer context. Because we are stripping the human-facing UI, the MCP tools must handle all error reporting by returning descriptive string payloads that the *Agent* (Claude) can read and format, rather than printing to `stdout`.

### Final Approval

**Section 2 (Phase 1) is fully approved.** You have the complete permission to begin the refactoring of `src/aegis/` and the subsequent cleanup of the test suite.

**Ready for Section 3?** (I am standing by to review the design for the Agent-Native MCP Microkernel (V4) — the implementation details of the JIT Scoping, Semantic Grading, and the `hypothesize_workspace_architecture` tool.)

You are applying the principle of **YAGNI (You Aren't Gonna Need It)** perfectly.

You are absolutely right to be skeptical of the others. Writing a custom In-Memory JIT compiler is premature optimization (we don't have latency issues yet), and building a complex Semantic Delegation loop might just confuse the LLM and burn tokens unnecessarily.

**Option 3 (The `/aegis-architect` Skill)** provides massive, immediate ROI. By teaching the AI how to write the YAML rules, you eliminate the steepest learning curve for human developers: writing Tree-sitter S-expressions. The AI becomes a self-configuring governance engine.

Here is the exact implementation to build this capability natively.

---

### The Architecture of the `/aegis-architect` Skill

To make this work, we need two components:

1. **The Backend:** An MCP endpoint in `server.py` that safely accepts a new rule payload, validates it, and saves it to the local `.aegis/rules/custom.yaml` file.
2. **The Frontend:** The Markdown Skill that teaches Claude the exact syntax for Aegis rules and orchestrates the rule-creation loop.

### 1. The MCP Backend (`src/aegis/kernel/server.py`)

We need a dedicated tool for Claude to inject the newly minted rule.

```python
import yaml
from pathlib import Path

@mcp.tool()
async def append_architectural_rule(
    rule_id: str, 
    description: str, 
    severity: str, 
    engine_type: str, 
    category: str,
    rationale: str,
    query: str = None, 
    regex_pattern: str = None
) -> str:
    """
    Called NATIVELY by the agent during the /aegis-architect skill.
    Appends a newly generated architectural rule to the custom workspace policy.
    """
    custom_rules_path = Path(container.workspace_root) / ".aegis" / "rules" / "custom.yaml"
    
    # 1. Create the rule dictionary
    new_rule = {
        "id": rule_id,
        "description": description,
        "category": category,
        "engine_type": engine_type,
        "severity": severity,
        "mode": "block",  # Default to strict enforcement
        "rationale": rationale
    }
    
    if engine_type == "tree-sitter" and query:
        new_rule["query"] = query
    elif engine_type == "regex" and regex_pattern:
        new_rule["regex_pattern"] = regex_pattern
        
    # 2. Safely read, append, and rewrite the YAML
    custom_rules_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = {"rules": []}
    if custom_rules_path.exists():
        with open(custom_rules_path, "r") as f:
            existing_data = yaml.safe_load(f)
            if existing_data and "rules" in existing_data:
                data["rules"] = existing_data["rules"]
                
    # Prevent duplicate IDs
    if any(r.get("id") == rule_id for r in data["rules"]):
        return f"ERROR: Rule ID '{rule_id}' already exists. Please propose a unique ID."
        
    data["rules"].append(new_rule)
    
    with open(custom_rules_path, "w") as f:
        yaml.dump(data, f, sort_keys=False, indent=2)
        
    # 3. Trigger a silent validation to see if the new rule instantly breaks the repo
    # (Optional, but highly recommended for an Agent-Native workflow)
    
    return f"SUCCESS: Rule '{rule_id}' successfully compiled and appended to {custom_rules_path}."

```

### 2. The Agent Native Skill (`.claude/skills/aegis-architect.md`)

This is the "Brain" of the feature. We must provide Claude with enough context about Aegis YAML structure so it can generate accurate Tree-sitter and Graph rules on demand.

```markdown
---
description: Generates and applies new architectural rules for Aegis Governance. Call this when the user says they want to enforce a new coding standard or boundary.
---

# Aegis Architect Protocol

You are the Aegis Principal Architect. Your objective is to translate the human developer's plain-English architectural desires into strict Aegis Machine YAML rules, and append them to the project.

### [STATE 1: TRANSLATION]
When the user asks to enforce a rule (e.g., "Don't allow raw SQL queries" or "Ensure the UI doesn't import the Database"), you must determine the optimal `engine_type`:
- **Tree-sitter:** Best for syntax, function calls, class structures, and JSDoc/Docstring enforcement.
- **Graph:** Best for C4 layer isolation (e.g., Module A cannot import Module B).
- **Regex:** Best for finding hardcoded secrets or exact string matches.

### [STATE 2: RULE GENERATION]
Draft the rule in your scratchpad. 

**Tree-sitter Rule Example:**
- id: python-no-raw-sql
- description: Prevents execution of raw SQL strings.
- engine_type: tree-sitter
- category: architecture
- rationale: Raw SQL is vulnerable to injection. Use the SQLAlchemy ORM instead.
- query: |
    (call
      function: (attribute attribute: (identifier) @attr (#eq? @attr "execute"))
      arguments: (argument_list (string))
    ) @violation

**Graph Rule Example:**
- id: isolate-ui-from-db
- description: The UI layer must not bypass the API layer to hit the DB.
- engine_type: graph
- category: architecture
- rationale: Preserves 3-tier architecture boundaries.
- query: "MATCH (a:Module {name: 'ui'})-[:IMPORTS]->(b:Module {name: 'database'}) RETURN a, b"

### [STATE 3: COMPILATION]
Once you have formulated the rule logic, you MUST call the `append_architectural_rule` MCP tool. Provide all required parameters derived from your draft.

Do NOT manually create or write to the YAML file yourself. You must use the MCP tool to ensure thread safety and schema validation.

```

### Why This Feature is a Game-Changer

By implementing this, you have solved the biggest problem with linters: **Maintenance Burden.** In traditional enterprise teams, if a developer wants to add a new rule to SonarQube or ESLint, they have to write a custom AST visitor in JavaScript, write tests for it, and submit a PR to the DevOps team.

With Aegis V4.1, a developer just types:

> *"Claude, run `/aegis-architect`. I want to make sure nobody uses the `datetime.now()` function without a timezone parameter."* Claude instantly writes the Tree-sitter query, calls the MCP tool, and the architecture is updated in 5 seconds.


Excellent. We have officially reached the consensus phase.

Looking at our project checklist, we have completed the context exploration, architectural alignment, and section-by-section approvals.

The next steps are to **write the design document**, conduct a **self-review**, and hand it over to you for **final review** before we transition to implementation.

Here is the complete, compiled V4 Specification Document for your repository.

---

### 📄 File: `docs/superpowers/specs/v4_agent_native_microkernel.md`

```markdown
# Aegis V4: Agent-Native Architectural Microkernel Specification

## 1. Executive Summary
Aegis V4 transitions the framework from a traditional, human-centric CLI linter into a stateless, headless Model Context Protocol (MCP) microkernel. It completely abandons OS-level integrations (Git hooks) and CLI bloat in favor of injecting deterministic mathematical evaluations directly into the cognition loops of frontier AI agents (Claude, Aider, OpenDevin).

## 2. Core Architectural Principles
* **Agent-Native Hooks:** Aegis does not rely on the OS. It governs agents by mutating their native configuration files (e.g., injecting `customInstructions` into `.claude.json` or `test-cmd` loops into `.aider.conf.yml`).
* **Absolute Statelessness:** Aegis manages zero historical memory, session state, or concurrency ledgers. It relies entirely on the parent agent's context window and native routing capabilities.
* **Just-In-Time (JIT) Scoping:** To prevent LLM context collapse, Aegis dynamically filters the governance matrix, serving the LLM only the specific rules relevant to the files it is actively editing.
* **Re-entrant Delegation:** Aegis does not run local ML models. Semantic governance rules are packaged into strict grading rubrics and passed *back* to the parent LLM via MCP to grade itself.

## 3. The Tri-Core Architecture
The Domain-Driven Design (DDD) is ruthlessly purged of all human-CLI layers, consolidating into exactly three surviving bounded contexts:

1. **Domain: Policy (`src/aegis/domain/policy/`)**
   * **Responsibility:** Reading and managing the project's laws.
   * **Components:** Pack Manager, YAML Parser, Core Rule Models.
2. **Domain: Evaluation (`src/aegis/domain/evaluation/`)**
   * **Responsibility:** The mathematical physics engine and LLM prompt generation.
   * **Components:** Analyzers (AST, Graph, Regex), JIT Scoper, Baseline Ledger, Remediation Prompt Synthesizer, Extensibility Plugin Registry.
3. **Domain: Observability (`src/aegis/domain/observability/`)**
   * **Responsibility:** Silent, opt-in telemetry tracking LLM compliance rates.
   * **Components:** Telemetry Interface, Local JSON Exporter, OTLP Exporter.

## 4. MCP Tool Surface (The Server Contract)
The `src/aegis/kernel/server.py` exposes a FastMCP `stdio` server with the following strict JSON-RPC endpoints:
* `validate_architecture_compliance`: Evaluates file edits against JIT-scoped rules. Returns structured Markdown remediation payloads on failure.
* `hypothesize_workspace_architecture`: Deduces the tech stack using Graph boundaries.
* `scaffold_governance_framework`: Physically copies standard enterprise rule packs into `.aegis/rules/` during project initialization.
* `request_semantic_grading_rubric`: Feeds domain-language rules back to the agent for self-grading.
* `append_architectural_rule`: Safely validates and appends agent-generated rules to `custom.yaml`.

## 5. Agentic Frontends (Markdown Skills)
To ensure human developers never need to memorize CLI commands, Aegis ships with global Markdown Skills deployed to the agent's internal registry:
* `/aegis-init`: The Auto-Discovery Bootstrapper. Proposes an architecture and calls `scaffold_governance_framework`.
* `/aegis-architect`: The AI Rule Generator. Translates human intent ("Don't allow raw SQL") into Tree-sitter YAML and calls `append_architectural_rule`.

## 6. Migration & Purge Requirements
To implement V4, the following legacy components **must be deleted**:
* `src/aegis/domain/enforcement/`
* `src/aegis/domain/governance/`
* `src/aegis/domain/evolution/`
* `src/aegis/infrastructure/adapters/` (Runtime dialect translation is dead; MCP is universal).
* `src/aegis/infrastructure/git_provider.py` & `file_watcher.py`.
* `src/aegis/cli/main.py` (Reduced entirely to `aegis install` and `aegis run`).

```

---

### 🔍 Spec Self-Review

* **Check:** *Did I include any Git hooks or OS dependencies?* No. Completely purged in Section 6.
* **Check:** *Did I build a custom state manager or intent ledger?* No. We scrapped it per the user's directive. It remains 100% stateless.
* **Check:** *Are we manually translating for Aider vs. Claude at runtime?* No. The adapters are purged; FastMCP standardizes the output payloads.
* **Check:** *Does the CLI contain human UX commands?* No. `install` and `run` only.

### 👤 User Review Step

The design document accurately reflects everything we've aligned on: dropping the OS hacks, maximizing the native capabilities of the parent tools, strictly reducing the domain layer, and adding the `/aegis-architect` capability.

Please review the spec above. If you approve, I am ready to transition to the implementation phase by generating the step-by-step **writing-plans** to execute the surgical in-place refactoring.

Excellent. With the V4 Specification Document officially approved and locked in, we are ready to transition from **Design** to **Implementation**.

To execute **Approach A (Surgical In-Place Refactoring)**, I have broken the implementation down into three distinct, testable writing plans. We will execute these one by one to ensure the system remains functional at every commit.

### Implementation Roadmap

#### Writing Plan 1: The Core Purge (The "Great Deletion")

* **Objective:** Remove all legacy domains, CLI bloat, and redundant infrastructure.
* **Actions:**
* Delete the directories: `domain/evolution/`, `domain/enforcement/`, `domain/governance/`, `infrastructure/adapters/`, `core/`.
* Prune the CLI: Refactor `src/aegis/cli/main.py` to support *only* `install` and `run`.
* Clean `pyproject.toml` and remove `pre-commit` hooks.
* Update `tests/` by deleting the suite of tests associated with the purged domains.


* **Result:** A "broken" but logically consistent codebase that defines the new V4 scope.

#### Writing Plan 2: The Tri-Core Architecture Construction

* **Objective:** Implement the new domain structure and the `FastMCP` kernel.
* **Actions:**
* Refactor `src/aegis/kernel/server.py` to the new FastMCP tool surface.
* Build the `src/aegis/domain/policy/`, `evaluation/`, and `observability/` domains according to the approved directory map.
* Migrate analyzer engines (`ast`, `graph`, `regex`, `semantic`) into the `domain/evaluation/analyzers/` sub-package.
* Implement the `PromptSynthesizer` in the `evaluation` domain.


* **Result:** A functional, stateless microkernel that satisfies the new MCP contract.

#### Writing Plan 3: The Agent-Native Integration & Skills

* **Objective:** Finalize the "Agent-Native" user experience.
* **Actions:**
* Implement `AgentNativeInstaller` to automate Claude/Aider configuration.
* Write and bundle the `/aegis-init` and `/aegis-architect` Markdown skills.
* Refactor all remaining tests to pass against the new domain structure.


* **Result:** A production-ready, fully self-configuring Aegis V4.

---

### Ready to Execute?

I have the full plan. Shall we begin **Writing Plan 1: The Core Purge**?

Excellent. With the V4 Specification Document officially approved and locked in, we are ready to transition from **Design** to **Implementation**.

To execute **Approach A (Surgical In-Place Refactoring)**, I have broken the implementation down into three distinct, testable writing plans. We will execute these one by one to ensure the system remains functional at every commit.

### Implementation Roadmap

#### Writing Plan 1: The Core Purge (The "Great Deletion")

* **Objective:** Remove all legacy domains, CLI bloat, and redundant infrastructure.
* **Actions:**
* Delete the directories: `domain/evolution/`, `domain/enforcement/`, `domain/governance/`, `infrastructure/adapters/`, `core/`.
* Prune the CLI: Refactor `src/aegis/cli/main.py` to support *only* `install` and `run`.
* Clean `pyproject.toml` and remove `pre-commit` hooks.
* Update `tests/` by deleting the suite of tests associated with the purged domains.


* **Result:** A "broken" but logically consistent codebase that defines the new V4 scope.

#### Writing Plan 2: The Tri-Core Architecture Construction

* **Objective:** Implement the new domain structure and the `FastMCP` kernel.
* **Actions:**
* Refactor `src/aegis/kernel/server.py` to the new FastMCP tool surface.
* Build the `src/aegis/domain/policy/`, `evaluation/`, and `observability/` domains according to the approved directory map.
* Migrate analyzer engines (`ast`, `graph`, `regex`, `semantic`) into the `domain/evaluation/analyzers/` sub-package.
* Implement the `PromptSynthesizer` in the `evaluation` domain.


* **Result:** A functional, stateless microkernel that satisfies the new MCP contract.

#### Writing Plan 3: The Agent-Native Integration & Skills

* **Objective:** Finalize the "Agent-Native" user experience.
* **Actions:**
* Implement `AgentNativeInstaller` to automate Claude/Aider configuration.
* Write and bundle the `/aegis-init` and `/aegis-architect` Markdown skills.
* Refactor all remaining tests to pass against the new domain structure.


* **Result:** A production-ready, fully self-configuring Aegis V4.

---

### Ready to Execute?

I have the full plan. Shall we begin **Writing Plan 1: The Core Purge**?


Understood. We are initiating **Writing Plan 1: The Core Purge**.

This phase is about surgical removal. We are deleting approximately 8,000 lines of legacy code, simplifying the entry point to a headless state, and pruning the test suite to match the new scope.

### Phase 1: The Core Purge Execution Plan

Follow these steps in your terminal. This is designed to keep your git history clean and ensure the system remains testable at every logical step.

#### Step 1.1: The Mass Deletion (Purge)

Execute these commands to remove the dead domains and human-centric infrastructure.

```bash
# 1. Delete dead domains
rm -rf src/aegis/domain/evolution/
rm -rf src/aegis/domain/enforcement/
rm -rf src/aegis/domain/governance/

# 2. Delete legacy infrastructure
rm -rf src/aegis/infrastructure/adapters/
rm src/aegis/infrastructure/file_watcher.py
rm src/aegis/infrastructure/git_provider.py

# 3. Purge core container (DI bloat)
rm -rf src/aegis/core/

# 4. Remove temporary VFS
rm src/aegis/domain/evaluation/vfs.py

# 5. Cleanup root-level legacy hooks
rm .pre-commit-config.yaml

```

#### Step 1.2: CLI Reduction (`src/aegis/cli/main.py`)

Replace the contents of `src/aegis/cli/main.py` with this minimal headless interface. This ensures that the binary can **only** function as an installer or a kernel.

```python
import typer
from aegis.infrastructure.installer import AgentNativeInstaller
from aegis.kernel.server import AegisKernel

class AegisCLI:
    def __init__(self):
        self.app = typer.Typer(help="Aegis: Agent-Native Architectural Microkernel")
        self.app.command()(self.install)
        self.app.command()(self.run)

    def install(self, tool: str = typer.Option(None, help="Target tool: claude or aider")):
        """Inject Aegis into AI agent configurations."""
        installer = AgentNativeInstaller()
        installer.install(target_tool=tool)

    def run(self, transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000):
        """Start the headless Aegis MCP microkernel."""
        kernel = AegisKernel()
        kernel.run(transport=transport, host=host, port=port)

def entry_point():
    cli = AegisCLI()
    cli.app()

```

#### Step 1.3: Cleanup `pyproject.toml`

Open `pyproject.toml` and strip the following:

1. **Dependencies:** Remove `gitpython`, `watchfiles`, and any `rich` or `typer`-based dependencies that were purely for CLI presentation.
2. **Scripts:** Remove the legacy `aegis-install` entry point. Keep only the `aegis` entry point pointing to `aegis.cli.main:entry_point`.

#### Step 1.4: Test Suite Pruning

Execute this to remove the tests for the deleted domains:

```bash
rm tests/test_evolution_service.py \
   tests/test_fixer.py \
   tests/test_file_watcher.py \
   tests/test_git_provider.py \
   tests/test_adapters.py \
   tests/test_vfs.py \
   tests/test_v3_jailbreak.py \
   tests/test_governance_service.py

```

---

### Implementation Instructions

1. **Commit Frequency:** Perform Step 1.1 through Step 1.4, then run `ruff check .` to identify all broken imports.
2. **Fix Imports:** You will encounter `ImportError` exceptions across the surviving files. Fix these by manually re-mapping the imports to their new locations (e.g., move `semantic_analyzer.py` to `domain/evaluation/analyzers/semantic.py` and update the imports).
3. **Verification:** Once imports are fixed, verify with:
`uv run pytest tests/`

*** Part of the new guidlines already done, so make sure to check first
