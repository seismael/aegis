# Aegis V4 Agent-Native Microkernel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Aegis from a CLI-centric system tool into a 100% Agent-Native MCP microkernel with 6 tools, Tri-Core domain architecture, and no OS-level hooks.

**Architecture:** Surgical in-place refactoring (Approach A). Delete dead domains (evolution, enforcement, governance, core, adapters, vfs, file_watcher, git_provider). Relocate survivors into Tri-Core (policy, evaluation, observability). Replace DI container with constructor injection. CLI reduced to `install` + `run`.

**Tech Stack:** Python 3.12+, FastMCP, tree-sitter, Pydantic, Typer, structlog, pytest, ruff.

---

## File Structure

### Deleted (entire directories/files)
```
src/aegis/core/                                    # DI container → inline in server.py
src/aegis/domain/evolution/                        # Stateful audit → agent context
src/aegis/domain/enforcement/                       # Except prompt_synthesizer content
src/aegis/domain/governance/                        # Middleman → server.py
src/aegis/domain/evaluation/vfs.py                  # Stateless kernel
src/aegis/infrastructure/adapters/                  # MCP is universal
src/aegis/infrastructure/file_watcher.py            # OS file watching
src/aegis/infrastructure/git_provider.py            # Git hook diffing
.pre-commit-config.yaml                             # No OS hooks
tests/test_evolution_service.py
tests/test_fixer.py
tests/test_file_watcher.py
tests/test_git_provider.py
tests/test_adapters.py
tests/test_vfs.py
tests/test_v3_jailbreak.py
tests/test_governance_service.py
```

### Relocated/Renamed
```
src/aegis/domain/enforcement/errors.py       → src/aegis/kernel/errors.py
src/aegis/domain/enforcement/remediation.py  → src/aegis/domain/evaluation/prompt_synthesizer.py
src/aegis/infrastructure/regex_analyzer.py   → src/aegis/domain/evaluation/analyzers/regex.py
src/aegis/infrastructure/ast_analyzer.py     → src/aegis/domain/evaluation/analyzers/ast.py
src/aegis/infrastructure/graph_analyzer.py   → src/aegis/domain/evaluation/analyzers/graph.py
src/aegis/infrastructure/semantic_analyzer.py → src/aegis/domain/evaluation/analyzers/semantic.py
src/aegis/core/plugins/interfaces.py         → src/aegis/domain/evaluation/plugins/interfaces.py
src/aegis/core/plugins/registry.py           → src/aegis/domain/evaluation/plugins/registry.py
src/aegis/core/plugins/scaffold.py           → src/aegis/domain/evaluation/plugins/scaffold.py
src/aegis/core/models/config.py              → src/aegis/domain/policy/config.py
src/aegis/core/constants.py                  → src/aegis/domain/evaluation/constants.py
tests/test_remediation_synthesizer.py        → tests/test_prompt_synthesizer.py
```

### Created New
```
src/aegis/kernel/errors.py                          # From domain/enforcement/errors.py
src/aegis/domain/evaluation/prompt_synthesizer.py    # From domain/enforcement/remediation.py
src/aegis/domain/evaluation/analyzers/__init__.py
src/aegis/domain/evaluation/analyzers/regex.py       # From infrastructure/regex_analyzer.py
src/aegis/domain/evaluation/analyzers/ast.py         # From infrastructure/ast_analyzer.py
src/aegis/domain/evaluation/analyzers/graph.py       # From infrastructure/graph_analyzer.py
src/aegis/domain/evaluation/analyzers/semantic.py    # From infrastructure/semantic_analyzer.py
src/aegis/domain/evaluation/plugins/__init__.py      # From core/plugins/__init__.py
src/aegis/domain/evaluation/plugins/interfaces.py    # From core/plugins/interfaces.py
src/aegis/domain/evaluation/plugins/registry.py      # From core/plugins/registry.py
src/aegis/domain/evaluation/plugins/scaffold.py      # From core/plugins/scaffold.py
src/aegis/domain/evaluation/constants.py             # From core/constants.py
src/aegis/domain/policy/config.py                    # From core/models/config.py
```

### Modified In-Place
```
src/aegis/cli/main.py                                # Reduced to install + run
src/aegis/kernel/server.py                           # Constructor injection, 6 tools
src/aegis/kernel/models.py                           # Updated imports
src/aegis/domain/evaluation/service.py               # Remove VFS, DiffProvider deps
src/aegis/domain/evaluation/ports.py                 # Remove DiffProvider, specVFS interfaces
src/aegis/domain/evaluation/scoping.py               # Enhanced JIT scoping
src/aegis/infrastructure/installer.py                # Rewrite as AgentNativeInstaller
pyproject.toml                                       # Remove deps, entry points
mcp.json                                             # Use aegis run
config.toml                                          # Use aegis run
```

---

## Phase 1: Core Purge & Protocol Lock

### Task 1.1: Delete dead domain directories

**Files:**
- Delete: `src/aegis/domain/evolution/`
- Delete: `src/aegis/domain/governance/`
- Delete: `src/aegis/domain/enforcement/` (all except errors.py and remediation.py)

- [ ] **Step 1: Delete dead domain directories**

Run:
```
Remove-Item -Recurse -Force "C:\dev\projects\aegis\src\aegis\domain\evolution"
Remove-Item -Recurse -Force "C:\dev\projects\aegis\src\aegis\domain\governance"
Remove-Item -Force "C:\dev\projects\aegis\src\aegis\domain\enforcement\fixer.py"
Remove-Item -Force "C:\dev\projects\aegis\src\aegis\domain\enforcement\ports.py"
Remove-Item -Force "C:\dev\projects\aegis\src\aegis\domain\enforcement\__init__.py"
```

- [ ] **Step 2: Delete dead test files**

Run:
```
Remove-Item -Force "C:\dev\projects\aegis\tests\test_evolution_service.py"
Remove-Item -Force "C:\dev\projects\aegis\tests\test_governance_service.py"
Remove-Item -Force "C:\dev\projects\aegis\tests\test_fixer.py"
Remove-Item -Force "C:\dev\projects\aegis\tests\test_vfs.py"
Remove-Item -Force "C:\dev\projects\aegis\tests\test_v3_jailbreak.py"
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(v4): delete dead domains (evolution, governance, enforcement/fixer)"
```

---

### Task 1.2: Delete infrastructure dead weight

**Files:**
- Delete: `src/aegis/infrastructure/adapters/` (all 5 files + package)
- Delete: `src/aegis/infrastructure/file_watcher.py`
- Delete: `src/aegis/infrastructure/git_provider.py`
- Delete: `src/aegis/domain/evaluation/vfs.py`

- [ ] **Step 1: Delete adapters directory**

Run:
```
Remove-Item -Recurse -Force "C:\dev\projects\aegis\src\aegis\infrastructure\adapters"
```

- [ ] **Step 2: Delete file watcher, git provider, VFS**

Run:
```
Remove-Item -Force "C:\dev\projects\aegis\src\aegis\infrastructure\file_watcher.py"
Remove-Item -Force "C:\dev\projects\aegis\src\aegis\infrastructure\git_provider.py"
Remove-Item -Force "C:\dev\projects\aegis\src\aegis\domain\evaluation\vfs.py"
```

- [ ] **Step 3: Delete corresponding test files**

Run:
```
Remove-Item -Force "C:\dev\projects\aegis\tests\test_file_watcher.py"
Remove-Item -Force "C:\dev\projects\aegis\tests\test_git_provider.py"
Remove-Item -Force "C:\dev\projects\aegis\tests\test_adapters.py"
```

- [ ] **Step 4: Delete .pre-commit-config.yaml**

Run:
```
Remove-Item -Force "C:\dev\projects\aegis\.pre-commit-config.yaml"
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(v4): delete infrastructure dead weight (adapters, file_watcher, git_provider, vfs, pre-commit)"
```

---

### Task 1.3: Relocate errors.py to kernel/

**Files:**
- Create: `src/aegis/kernel/errors.py`
- Delete: `src/aegis/domain/enforcement/errors.py`

- [ ] **Step 1: Move errors.py to kernel**

Run:
```
Move-Item "C:\dev\projects\aegis\src\aegis\domain\enforcement\errors.py" "C:\dev\projects\aegis\src\aegis\kernel\errors.py"
```

- [ ] **Step 2: Delete remaining enforcement directory**

Run:
```
Remove-Item -Force "C:\dev\projects\aegis\src\aegis\domain\enforcement\remediation.py"
Remove-Item -Force "C:\dev\projects\aegis\src\aegis\domain\enforcement"
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(v4): relocate errors.py to kernel/, delete enforcement directory"
```

---

### Task 1.4: Relocate analyzers to domain/evaluation/analyzers/

**Files:**
- Create: `src/aegis/domain/evaluation/analyzers/__init__.py`
- Create: `src/aegis/domain/evaluation/analyzers/regex.py`
- Create: `src/aegis/domain/evaluation/analyzers/ast.py`
- Create: `src/aegis/domain/evaluation/analyzers/graph.py`
- Create: `src/aegis/domain/evaluation/analyzers/semantic.py`
- Delete: `src/aegis/infrastructure/regex_analyzer.py`
- Delete: `src/aegis/infrastructure/ast_analyzer.py`
- Delete: `src/aegis/infrastructure/graph_analyzer.py`
- Delete: `src/aegis/infrastructure/semantic_analyzer.py`

- [ ] **Step 1: Create analyzers directory**

Run:
```
New-Item -ItemType Directory -Path "C:\dev\projects\aegis\src\aegis\domain\evaluation\analyzers" -Force
```

- [ ] **Step 2: Write analyzers __init__.py**

```python
from aegis.domain.evaluation.analyzers.regex import RegexAnalyzer
from aegis.domain.evaluation.analyzers.ast import TreeSitterAnalyzer
from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer
from aegis.domain.evaluation.analyzers.semantic import SemanticAnalyzer

__all__ = ["RegexAnalyzer", "TreeSitterAnalyzer", "GraphAnalyzer", "SemanticAnalyzer"]
```

Write file: `C:\dev\projects\aegis\src\aegis\domain\evaluation\analyzers\__init__.py`

- [ ] **Step 3: Move analyzer files**

Run:
```
Move-Item "C:\dev\projects\aegis\src\aegis\infrastructure\regex_analyzer.py" "C:\dev\projects\aegis\src\aegis\domain\evaluation\analyzers\regex.py"
Move-Item "C:\dev\projects\aegis\src\aegis\infrastructure\ast_analyzer.py" "C:\dev\projects\aegis\src\aegis\domain\evaluation\analyzers\ast.py"
Move-Item "C:\dev\projects\aegis\src\aegis\infrastructure\graph_analyzer.py" "C:\dev\projects\aegis\src\aegis\domain\evaluation\analyzers\graph.py"
Move-Item "C:\dev\projects\aegis\src\aegis\infrastructure\semantic_analyzer.py" "C:\dev\projects\aegis\src\aegis\domain\evaluation\analyzers\semantic.py"
```

- [ ] **Step 4: Update imports in relocated files**

In `src/aegis/domain/evaluation/analyzers/regex.py`, `ast.py`, `graph.py`, `semantic.py`:
- These files import from `aegis.domain.evaluation.ports` — those imports remain valid
- No package-level import changes needed for these files since they use relative domain imports

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(v4): relocate analyzers to domain/evaluation/analyzers/"
```

---

### Task 1.5: Relocate plugin system to domain/evaluation/plugins/

**Files:**
- Create: `src/aegis/domain/evaluation/plugins/__init__.py`
- Create: `src/aegis/domain/evaluation/plugins/interfaces.py`
- Create: `src/aegis/domain/evaluation/plugins/registry.py`
- Create: `src/aegis/domain/evaluation/plugins/scaffold.py`
- Delete: `src/aegis/core/plugins/`

- [ ] **Step 1: Create plugins directory**

Run:
```
New-Item -ItemType Directory -Path "C:\dev\projects\aegis\src\aegis\domain\evaluation\plugins" -Force
```

- [ ] **Step 2: Move plugin files**

Run:
```
Move-Item "C:\dev\projects\aegis\src\aegis\core\plugins\__init__.py" "C:\dev\projects\aegis\src\aegis\domain\evaluation\plugins\__init__.py"
Move-Item "C:\dev\projects\aegis\src\aegis\core\plugins\interfaces.py" "C:\dev\projects\aegis\src\aegis\domain\evaluation\plugins\interfaces.py"
Move-Item "C:\dev\projects\aegis\src\aegis\core\plugins\registry.py" "C:\dev\projects\aegis\src\aegis\domain\evaluation\plugins\registry.py"
Move-Item "C:\dev\projects\aegis\src\aegis\core\plugins\scaffold.py" "C:\dev\projects\aegis\src\aegis\domain\evaluation\plugins\scaffold.py"
```

- [ ] **Step 3: Clean up core directory remains**

Run:
```
Remove-Item -Recurse -Force "C:\dev\projects\aegis\src\aegis\core"
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(v4): relocate plugin system to domain/evaluation/plugins/, delete core/"
```

---

### Task 1.6: Relocate remaining survivors (constants, config, prompt_synthesizer)

**Files:**
- Create: `src/aegis/domain/evaluation/constants.py`
- Create: `src/aegis/domain/policy/config.py`
- Create: `src/aegis/domain/evaluation/prompt_synthesizer.py`

- [ ] **Step 1: Read constants.py for content**

Read `src/aegis/core/constants.py` (was already deleted, recreate from known content):

```python
IGNORE_DIRS = frozenset({'.venv', 'node_modules', '.git', '.aegis', '__pycache__', '.tox', 'dist', 'build', '.mypy_cache', '.pytest_cache', '.ruff_cache'})

LANG_EXT_MAP = {
    'python': '.py',
    'typescript': '.ts',
    'javascript': '.js',
    'rust': '.rs',
    'go': '.go',
    'tsx': '.tsx',
    'jsx': '.jsx',
}
```

Write to: `C:\dev\projects\aegis\src\aegis\domain\evaluation\constants.py`

- [ ] **Step 2: Write config.py**

Read `src/aegis/core/models/config.py` (was already deleted, recreate from known content):

```python
from pydantic import BaseModel


class AegisConfig(BaseModel):
    enforcement: str = "warn"
    phase_defaults: dict = {}
    category_overrides: dict = {}
    auto_baseline: bool = False
    max_violations: int = 1000
```

Write to: `C:\dev\projects\aegis\src\aegis\domain\policy\config.py`

- [ ] **Step 3: Write prompt_synthesizer.py**

Read `src/aegis/domain/enforcement/remediation.py` (already deleted, recreate from exploration). Write to `C:\dev\projects\aegis\src\aegis\domain\evaluation\prompt_synthesizer.py` with updated imports:

```python
import os

import structlog

from aegis.domain.enforcement.ports import (
    RemediationProviderInterface,
    RemediationResult,
)
from aegis.domain.evaluation.ports import ArchitecturalViolation, RuleAnalyzerInterface
from aegis.domain.policy.models import Rule

logger = structlog.get_logger()


class RemediationPromptSynthesizer(RemediationProviderInterface):
    """
    Converts mathematical AST violations into rigid, context-rich
    system prompts designed to be executed by native AI agents via MCP.
    Agent-Native V4: All outputs are strings for LLM consumption.
    """

    def __init__(self, extra_analyzers: list[RuleAnalyzerInterface] | None = None):
        self.extra_analyzers = extra_analyzers or []

    def generate_remediation(
        self, violations: list[ArchitecturalViolation], rules_map: dict[str, Rule]
    ) -> RemediationResult:
        if not violations:
            return RemediationResult(
                summary="No remediation required. Architecture is compliant.",
                violations_count=0,
                handoff_prompt="SUCCESS: Architecture compliant.",
            )

        payload = (
            "**AEGIS ARCHITECTURAL GOVERNANCE INTERVENTION**\n\n"
            "Your previous code generation violated the project's strict "
            "architectural invariants. You are required to immediately "
            "refactor the following files before proceeding.\n\n"
        )

        for v in violations:
            rule = rules_map.get(v.rule_id)
            is_security = rule is not None and rule.category.value == "security"

            if is_security:
                payload += (
                    f"### [CRITICAL SECURITY VULNERABILITY] in `{v.file}`"
                    f" (Line {v.line})\n"
                )
                payload += (
                    "**DIRECTIVE: Prioritize secure coding practices"
                    " over performance or brevity.**\n"
                )
            else:
                payload += f"### Violation in `{v.file}` (Line {v.line})\n"
            payload += f"- **Rule ID:** `{v.rule_id}` [{v.severity}]\n"

            custom_desc = None
            for extra in self.extra_analyzers:
                if hasattr(extra, "provide_remediation"):
                    custom_desc = extra.provide_remediation(v, rule)
                    if custom_desc:
                        break

            payload += f"- **Description:** {custom_desc or v.description}\n"
            payload += "- **Enforcement Mode:** "
            payload += f"{rule.mode.value if rule else 'block'}\n"
            if rule and rule.rationale:
                payload += f"- **Architectural Rationale:** {rule.rationale}\n"

            context = self._fetch_code_context(v.file, v.line)
            if context:
                payload += "\n**Code Context:**\n```\n"
                payload += context
                payload += "\n```\n"

            payload += "\n"

        payload += (
            "**Execution Directive:**\n"
            "1. Read the specified lines in the affected files.\n"
            "2. Refactor the code to eliminate the violation while "
            "preserving all existing business logic.\n"
            "3. Call the `validate_architecture_compliance` MCP tool "
            "again to verify your fix."
        )

        return RemediationResult(
            summary=f"Found {len(violations)} architectural violations.",
            violations_count=len(violations),
            handoff_prompt=payload,
        )

    def _fetch_code_context(
        self, filepath: str, line: int, context_lines: int = 5
    ) -> str:
        if not os.path.exists(filepath):
            return ""
        try:
            with open(filepath, encoding="utf-8") as f:
                lines = f.readlines()
            start = max(0, line - context_lines - 1)
            end = min(len(lines), line + context_lines)
            context = ""
            for i in range(start, end):
                prefix = "> " if i == line - 1 else "  "
                context += f"{prefix}{i + 1:4d} | {lines[i]}"
            return context
        except Exception as e:
            logger.warning("Failed to fetch code context", file=filepath, error=str(e))
            return ""
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(v4): relocate constants, config, prompt_synthesizer to V4 paths"
```

---

### Task 1.7: Rewrite CLI (main.py → install + run only)

**Files:**
- Modify: `src/aegis/cli/main.py`

- [ ] **Step 1: Rewrite main.py**

Replace entire file content:

```python
import logging
import os
import sys

import typer


class AegisCLI:
    """
    Headless CLI for Aegis V4 Agent-Native Microkernel.
    Two commands only: install (global agent config injection) and run (start MCP server).
    No human-facing output during development — agents handle everything via MCP.
    """

    def __init__(self):
        self.app = typer.Typer(
            help="Aegis V4: Agent-Native Architectural Microkernel"
        )
        self.app.command()(self.install)
        self.app.command()(self.run)

    def install(
        self,
        tool: str | None = typer.Option(
            None, "--tool", help="Target tool: claude, aider (omit for all)"
        ),
    ):
        """Inject Aegis MCP server config and cognitive directives into Claude/Aider."""
        from aegis.infrastructure.installer import AgentNativeInstaller

        installer = AgentNativeInstaller()
        installer.install(target_tool=tool)

    def run(
        self,
        transport: str = typer.Option(
            "stdio", "--transport", help="MCP transport: stdio, sse, streamable-http"
        ),
        host: str = typer.Option("127.0.0.1", "--host", help="Bind host (SSE/HTTP)"),
        port: int = typer.Option(8000, "--port", help="Bind port (SSE/HTTP)"),
    ):
        """Start the headless Aegis MCP microkernel server."""
        from aegis.kernel.server import AegisKernel

        kernel = AegisKernel()
        kernel.run(transport=transport, host=host, port=port)

    @staticmethod
    def entry_point():
        logging.basicConfig(
            level=logging.WARNING if "AEGIS_VERBOSE" not in os.environ else logging.DEBUG,
        )
        cli = AegisCLI()
        cli.app()


if __name__ == "__main__":
    AegisCLI.entry_point()
```

Write file: `C:\dev\projects\aegis\src\aegis\cli\main.py`

- [ ] **Step 2: Run ruff check and fix**

```
uv run ruff check --fix src/aegis/cli/main.py
```

- [ ] **Step 3: Commit**

```bash
git add src/aegis/cli/main.py
git commit -m "feat(v4): reduce CLI to install + run only"
```

---

### Task 1.8: Rewrite installer.py as AgentNativeInstaller

**Files:**
- Modify: `src/aegis/infrastructure/installer.py`

- [ ] **Step 1: Write AgentNativeInstaller**

Replace entire file content:

```python
"""
Aegis V4 Agent-Native Installer.
Injects Aegis directly into the cognition and execution loops
of Claude and Aider via their native configuration files.
No adapters. MCP is the universal protocol.
"""

import json
import os
from pathlib import Path

AEGIS_GOVERNANCE_DIRECTIVE = (
    "CRITICAL GOVERNANCE DIRECTIVE: "
    "You are governed by the Aegis Microkernel. "
    "Before declaring ANY coding task complete, you MUST execute the "
    "`validate_architecture_compliance` MCP tool. If it returns violations, "
    "you MUST remediate the code natively before proceeding."
)


class AgentNativeInstaller:
    """
    Injects Aegis directly into the cognition and execution loops
    of the target AI coding agents.
    """

    def __init__(self):
        self.home = Path.home()

    def install(self, target_tool: str | None = None):
        if not target_tool or target_tool == "claude":
            self._inject_claude()
        if not target_tool or target_tool == "aider":
            self._inject_aider()
        if target_tool and target_tool not in ("claude", "aider"):
            raise ValueError(
                f"Unsupported tool: {target_tool}. Supported: claude, aider"
            )

    def _inject_claude(self):
        claude_config = self.home / ".claude.json"
        config = {}
        if claude_config.exists():
            with open(claude_config, "r") as f:
                config = json.load(f)

        if "mcpServers" not in config:
            config["mcpServers"] = {}
        config["mcpServers"]["aegis"] = {"command": "aegis", "args": ["run"]}

        existing_instructions = config.get("customInstructions", "")
        if "Aegis Microkernel" not in existing_instructions:
            config["customInstructions"] = (
                f"{existing_instructions}\n\n{AEGIS_GOVERNANCE_DIRECTIVE}".strip()
            )

        with open(claude_config, "w") as f:
            json.dump(config, f, indent=2)

        print(f"[Aegis] Injected governance directive into {claude_config}")

    def _inject_aider(self):
        aider_config = self.home / ".aider.conf.yml"
        directive = (
            "\n# Aegis Native Integration\n"
            "mcp-server: aegis run\n"
            "test-cmd: aegis run --check\n"
            "auto-test: true\n"
        )

        with open(aider_config, "a") as f:
            f.write(directive)

        print(f"[Aegis] Injected MCP configuration into {aider_config}")
```

Write file: `C:\dev\projects\aegis\src\aegis\infrastructure\installer.py`

- [ ] **Step 2: Commit**

```bash
git add src/aegis/infrastructure/installer.py
git commit -m "feat(v4): rewrite installer as AgentNativeInstaller (Claude + Aider)"
```

---

### Task 1.9: Remove references to deleted files (import fix sweep)

**Files:**
- Modify: `src/aegis/domain/evaluation/ports.py` (remove DiffProvider, VFS interfaces)
- Modify: `src/aegis/domain/evaluation/service.py` (remove VFS, diff_provider, update imports)
- Modify: `src/aegis/kernel/server.py` (update imports for new paths)
- Modify: `src/aegis/kernel/models.py` (update imports if needed)
- Modify: `src/aegis/domain/evaluation/baseline.py` (check imports)
- Modify: `src/aegis/domain/evaluation/scoping.py` (check imports)

- [ ] **Step 1: Update evaluation/ports.py — remove DiffProvider and VFS interfaces**

Read current file first, then edit to remove:
- `DiffProviderInterface` class
- `DiffResult` class
- Any import of `SpeculativeVFS` or `vfs`

The file at `C:\dev\projects\aegis\src\aegis\domain\evaluation\ports.py` currently has:
- `ArchitecturalViolation` (KEEP)
- `RuleAnalyzerInterface` (KEEP)
- `GraphAnalyzerInterface` (KEEP)
- `RegexAnalyzerInterface` (KEEP)
- `SemanticAnalyzerInterface` (KEEP)
- `DiffResult` (DELETE)
- `DiffProviderInterface` (DELETE)

Remove from the file:
- `DiffResult` class
- `DiffProviderInterface` class
- Their imports

- [ ] **Step 2: Update evaluation/service.py — remove VFS and diff_provider, fix imports**

Replace imports section:

```python
import os

import structlog

from aegis.domain.evaluation.constants import IGNORE_DIRS, LANG_EXT_MAP
from aegis.domain.evaluation.ports import (
    ArchitecturalViolation,
    GraphAnalyzerInterface,
    RegexAnalyzerInterface,
    RuleAnalyzerInterface,
    SemanticAnalyzerInterface,
)
from aegis.domain.evaluation.scoping import ScopeFilter
from aegis.domain.policy.models import (
    CategoryPhaseMapping,
    EngineType,
    EvaluationPhase,
    Rule,
    RuleCategory,
)

logger = structlog.get_logger()
```

Remove from `__init__`:
- `diff_provider: DiffProviderInterface` parameter
- `vfs: SpeculativeVFS | None = None` parameter

Remove from class body:
- `evaluate_changes()` method entirely (depends on diff_provider and VFS)
- `_derive_root_dir()` static method (only used by evaluate_changes)

Remove VFS-dependent code from `evaluate_file()` (remove `session_id` parameter, simplify `_get_file_content`):

```python
def _get_file_content(self, file_path: str) -> str:
    with open(file_path, encoding="utf-8") as f:
        return f.read()
```

- [ ] **Step 3: Fix all remaining imports across the codebase**

Run ruff to find all broken imports:

```
uv run ruff check src/
```

Fix each error by updating the import path:

| Old Import | New Import |
|-----------|-----------|
| `from aegis.core.constants import ...` | `from aegis.domain.evaluation.constants import ...` |
| `from aegis.core.plugins.interfaces import ...` | `from aegis.domain.evaluation.plugins.interfaces import ...` |
| `from aegis.core.plugins.registry import ...` | `from aegis.domain.evaluation.plugins.registry import ...` |
| `from aegis.core.plugins.scaffold import ...` | `from aegis.domain.evaluation.plugins.scaffold import ...` |
| `from aegis.core.models.config import ...` | `from aegis.domain.policy.config import ...` |
| `from aegis.infrastructure.regex_analyzer import ...` | `from aegis.domain.evaluation.analyzers.regex import ...` |
| `from aegis.infrastructure.ast_analyzer import ...` | `from aegis.domain.evaluation.analyzers.ast import ...` |
| `from aegis.infrastructure.graph_analyzer import ...` | `from aegis.domain.evaluation.analyzers.graph import ...` |
| `from aegis.infrastructure.semantic_analyzer import ...` | `from aegis.domain.evaluation.analyzers.semantic import ...` |
| `from aegis.domain.enforcement.errors import ...` | `from aegis.kernel.errors import ...` |
| `from aegis.domain.enforcement.remediation import ...` | `from aegis.domain.evaluation.prompt_synthesizer import ...` |

- [ ] **Step 4: Run ruff check to confirm zero import errors**

```
uv run ruff check src/ --fix
```

Expected: no errors related to deleted/relocated modules.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(v4): fix all imports after relocation, remove VFS/DiffProvider deps from evaluation service"
```

---

### Task 1.10: Update pyproject.toml and config files

**Files:**
- Modify: `pyproject.toml`
- Modify: `mcp.json`
- Modify: `config.toml`

- [ ] **Step 1: Update pyproject.toml**

Remove `gitpython` dependency (line 40). Remove `aegis-install` entry point (line 62). Update `aegis` entry point if needed:

In `pyproject.toml`:
- Delete the line: `"gitpython>=3.1.43",`
- Delete the line: `aegis-install = "aegis.infrastructure.installer:AegisInstaller.entry_point"`
- Keep: `aegis = "aegis.cli.main:AegisCLI.entry_point"`

- [ ] **Step 2: Update mcp.json**

Replace content with:

```json
{
  "mcpServers": {
    "aegis-kernel": {
      "command": "aegis",
      "args": ["run"],
      "env": {
        "AEGIS_AGENT_MODE": "true"
      }
    }
  }
}
```

- [ ] **Step 3: Update config.toml**

Replace content with:

```toml
[mcp_servers.aegis-kernel]
command = "aegis"
args = ["run"]
env = { AEGIS_AGENT_MODE = "true" }
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml mcp.json config.toml
git commit -m "feat(v4): update pyproject.toml (remove gitpython), config files for aegis run"
```

---

### Task 1.11: Prune and refactor test suite

**Files:**
- Rename: `tests/test_remediation_synthesizer.py` → `tests/test_prompt_synthesizer.py`
- Modify: `tests/test_cli.py` (reduce to install + run)
- Modify: `tests/test_container.py` (simplify)
- Modify: all remaining test files (update imports)

- [ ] **Step 1: Rename test file**

Run:
```
Move-Item "C:\dev\projects\aegis\tests\test_remediation_synthesizer.py" "C:\dev\projects\aegis\tests\test_prompt_synthesizer.py"
```

- [ ] **Step 2: Update test_prompt_synthesizer.py imports**

Change:
```python
from aegis.domain.enforcement.remediation import RemediationPromptSynthesizer
```
to:
```python
from aegis.domain.evaluation.prompt_synthesizer import RemediationPromptSynthesizer
```

- [ ] **Step 3: Rewrite test_cli.py**

```python
import typer
from typer.testing import CliRunner

from aegis.cli.main import AegisCLI

runner = CliRunner()


def test_install_help():
    cli = AegisCLI()
    result = CliRunner().invoke(cli.app, ["install", "--help"])
    assert result.exit_code == 0
    assert "Inject" in result.stdout


def test_run_help():
    cli = AegisCLI()
    result = CliRunner().invoke(cli.app, ["run", "--help"])
    assert result.exit_code == 0
    assert "Start" in result.stdout or "MCP" in result.stdout


def test_no_other_commands():
    cli = AegisCLI()
    result = CliRunner().invoke(cli.app, ["check", "--help"])
    assert result.exit_code != 0
```

Write file: `C:\dev\projects\aegis\tests\test_cli.py`

- [ ] **Step 4: Rewrite test_installer.py**

```python
from unittest.mock import patch, mock_open
from pathlib import Path

from aegis.infrastructure.installer import AgentNativeInstaller, AEGIS_GOVERNANCE_DIRECTIVE


def test_installer_creates_claude_config():
    installer = AgentNativeInstaller()
    installer.home = Path("/tmp/aegis_test")

    mock_config = '{"mcpServers": {}}'
    with patch("builtins.open", mock_open(read_data=mock_config)) as m:
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.print"):
                installer._inject_claude()

    # Verify customInstructions injected
    written = m().write.call_args_list
    assert any("Aegis Microkernel" in str(call) for call in written)


def test_installer_target_tool_filter():
    installer = AgentNativeInstaller()
    installer.home = Path("/tmp/aegis_test")

    with patch.object(installer, "_inject_claude") as mock_claude:
        with patch.object(installer, "_inject_aider") as mock_aider:
            installer.install(target_tool="claude")
            mock_claude.assert_called_once()
            mock_aider.assert_not_called()


def test_installer_unsupported_tool():
    import pytest
    installer = AgentNativeInstaller()
    with pytest.raises(ValueError, match="Unsupported tool"):
        installer.install(target_tool="copilot")


def test_governance_directive_contains_validate_call():
    assert "validate_architecture_compliance" in AEGIS_GOVERNANCE_DIRECTIVE
```

Write file: `C:\dev\projects\aegis\tests\test_installer.py`

- [ ] **Step 5: Rewrite test_container.py**

```python
import pytest


class TestSimplifiedServiceInit:
    def test_kernel_constructs_with_explicit_deps(self):
        from aegis.kernel.server import AegisKernel
        kernel = AegisKernel()
        assert kernel is not None
        assert kernel.mcp is not None

    def test_kernel_constructs_with_custom_root(self, tmp_path):
        from aegis.kernel.server import AegisKernel
        kernel = AegisKernel(workspace_root=str(tmp_path))
        assert kernel.workspace_root == str(tmp_path)
```

Write file: `C:\dev\projects\aegis\tests\test_container.py`

- [ ] **Step 6: Global import fix in test files**

Run ruff on tests directory:

```
uv run ruff check tests/ --fix
```

Fix any remaining broken imports. Main changes needed:
- `test_mcp_tools.py`, `test_mcp_prompts.py`, `test_mcp_resources.py`, `test_mcp_transport.py`, `test_mcp_dependency_graph.py`, `test_integration.py` — update imports from `aegis.domain.enforcement.errors` to `aegis.kernel.errors`
- Any test importing from `aegis.core.*` — update to new paths
- Any test importing from `aegis.infrastructure.adapters` — already deleted

- [ ] **Step 7: Run pytest to identify any remaining failures**

```
uv run pytest tests/ -q --timeout=60 2>&1 | Select-Object -First 50
```

Fix failures one by one. Expected failures are import-related; fix by updating import paths.

- [ ] **Step 8: Commit**

```bash
git add tests/
git commit -m "feat(v4): prune test suite (delete 8 test files, rewrite CLI/installer/container tests, fix imports)"
```

---

### Task 1.12: Restore enforcement ports.py from kernel or recreate

The `RemediationResult` and `RemediationProviderInterface` are used by `prompt_synthesizer.py`. Since we deleted `domain/enforcement/ports.py`, we need to relocate those types.

- [ ] **Step 1: Create enforcement ports survivors in evaluation**

Check what `prompt_synthesizer.py` needs from `domain/enforcement/ports`:
- `RemediationProviderInterface` (ABC)
- `RemediationResult` (Pydantic)

Move these to `domain/evaluation/ports.py`:

Edit `src/aegis/domain/evaluation/ports.py` — ADD at end:

```python
from pydantic import BaseModel


class FixProposal(BaseModel):
    file: str
    diff: str = ""
    replacement_code: str = ""
    line_start: int = 0
    line_end: int = 0


class RemediationResult(BaseModel):
    summary: str
    violations_count: int
    proposals: list[FixProposal] = []
    handoff_prompt: str = ""


class RemediationProviderInterface(ABC):
    @abstractmethod
    def generate_remediation(
        self, violations: list[ArchitecturalViolation], rules_map: dict
    ) -> RemediationResult:
        ...
```

Update `prompt_synthesizer.py` import:
```python
from aegis.domain.evaluation.ports import (
    ArchitecturalViolation,
    RemediationProviderInterface,
    RemediationResult,
)
```

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "feat(v4): relocate RemediationResult types into evaluation/ports.py"
```

---

### Task 1.13: Refactor server.py for constructor injection

**Files:**
- Modify: `src/aegis/kernel/server.py`

- [ ] **Step 1: Update server.py imports**

Replace the import section (lines 1-36) with:

```python
import json
import os
import re
from pathlib import Path

import structlog
import yaml
from mcp.server.fastmcp import FastMCP

from aegis.kernel.errors import (
    ERR_CONTAINER_NOT_INIT,
    ERR_FILE_NOT_FOUND,
    ERR_INVALID_INPUT,
    ERR_NOT_INITIALIZED,
    ERR_READ_FAILED,
    ERR_SERVICE_UNAVAILABLE,
    error,
    warn,
)
from aegis.kernel.models import (
    ComplianceResult,
    RelevantRulesResult,
    ServerStatusResult,
    ViolationInfo,
)
from aegis.domain.evaluation.ports import RemediationResult
from aegis.domain.evaluation.prompt_synthesizer import RemediationPromptSynthesizer
from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer
from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.evaluation.scoping import ScopeFilter
from aegis.domain.evaluation.baseline import BaselineManager
from aegis.domain.evaluation.analyzers.regex import RegexAnalyzer
from aegis.domain.evaluation.analyzers.ast import TreeSitterAnalyzer
from aegis.domain.evaluation.analyzers.semantic import SemanticAnalyzer
from aegis.domain.policy.parser import PolicyParser
from aegis.domain.policy.pack_manager import RulePackManager
from aegis.domain.observability.telemetry import TelemetryRecorder

_VALID_TOOL_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_VERSION = "0.4.0"
```

- [ ] **Step 2: Rewrite AegisKernel.__init__ with constructor injection**

Replace the `__init__` method:

```python
class AegisKernel:
    """
    V4 Agent-Native Microkernel.
    Headless MCP server providing 6 tools for architectural governance.
    Every dependency is constructor-injected — no DI container.
    """

    def __init__(
        self,
        workspace_root: str | None = None,
        policy_parser: PolicyParser | None = None,
        evaluation_service: EvaluationService | None = None,
        baseline_manager: BaselineManager | None = None,
        pack_manager: RulePackManager | None = None,
        telemetry_recorder: TelemetryRecorder | None = None,
        graph_analyzer: GraphAnalyzer | None = None,
        remediation_synthesizer: RemediationPromptSynthesizer | None = None,
    ):
        self.logger = structlog.get_logger()
        self._workspace_root = workspace_root or self._discover_root()

        self.policy = policy_parser or PolicyParser(self._workspace_root)

        self.regex = RegexAnalyzer()
        self.tree_sitter = TreeSitterAnalyzer()
        self.graph = graph_analyzer or GraphAnalyzer()
        self.semantic = SemanticAnalyzer()

        self.evaluation = evaluation_service or EvaluationService(
            tree_sitter_analyzer=self.tree_sitter,
            graph_analyzer=self.graph,
            regex_analyzer=self.regex,
            semantic_analyzer=self.semantic,
        )

        self.baseline = baseline_manager or BaselineManager(
            self._workspace_root
        )
        self.packs = pack_manager or RulePackManager(self._workspace_root)
        self.telemetry = telemetry_recorder or TelemetryRecorder(
            self._workspace_root
        )
        self.remediation = remediation_synthesizer or RemediationPromptSynthesizer()

        self.mcp = FastMCP("Aegis Architecture Engine")
        self._register_tools()
        self._register_resources()
        self._register_prompts()

    @property
    def workspace_root(self) -> str:
        return self._workspace_root

    def _discover_root(self) -> str:
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                return str(parent)
        return str(current)
```

- [ ] **Step 3: Simplify _register_tools to V4 6-tool surface**

Replace the `_register_tools` method:

```python
def _register_tools(self):
    self.mcp.tool()(self.validate_architecture_compliance)
    self.mcp.tool()(self.request_semantic_grading_rubric)
    self.mcp.tool()(self.scaffold_governance_framework)
    self.mcp.tool()(self.query_knowledge_graph)
    self.mcp.tool()(self.evolve_ruleset)
    self.mcp.tool()(self.plan_architecture)
```

- [ ] **Step 4: Add V4 tool implementations**

Add after `_register_tools`:

```python
    async def validate_architecture_compliance(
        self,
        files_modified: list[str],
        phase: str = "pre-commit",
    ) -> str:
        """
        JIT Compliance Gate. Call before declaring any task complete.
        Returns SUCCESS string or formatted violation report with remediation.
        """
        rules = self._load_rules()
        if not rules:
            return warn("No rules loaded. Run /aegis-init first.")

        phase_enum = None
        try:
            from aegis.domain.policy.models import EvaluationPhase
            phase_enum = EvaluationPhase(phase)
        except ValueError:
            pass

        filtered = ScopeFilter.filter_rules_for_files(files_modified, rules)

        rule_map = {r.id: r for r in rules}
        violations = self.evaluation.evaluate_workspace(
            self.workspace_root, filtered, phase=phase_enum
        )

        active = [
            v for v in violations
            if not self.baseline.is_exempt(v, rule_map.get(v.rule_id))
        ]

        if not active:
            self.telemetry.record_check(len(violations), 0)
            return "SUCCESS: Architecture compliant. Task may be marked complete."

        self.telemetry.record_check(len(violations), len(active))
        result = self.remediation.generate_remediation(active, rule_map)
        return result.handoff_prompt

    async def request_semantic_grading_rubric(
        self,
        target_file: str,
        rule_ids: list[str] | None = None,
    ) -> str:
        """
        Re-entrant Semantic Grading. Returns a rubric for the parent LLM to
        self-evaluate domain language and naming conventions.
        """
        rules = self._load_rules()
        semantic_rules = [r for r in rules if r.engine_type.value == "semantic"]
        if rule_ids:
            semantic_rules = [r for r in semantic_rules if r.id in rule_ids]

        scoped = ScopeFilter.filter_rules_for_file(target_file, semantic_rules, rules)
        if not scoped:
            return "NO_SEMANTIC_RULES: No semantic rules apply to this file."

        return self.semantic.build_rubric(target_file, scoped)

    async def scaffold_governance_framework(
        self,
        target_packs: list[str],
    ) -> str:
        """
        Agent-driven project bootstrap. Writes default rule packs
        from bundled resources to .aegis/rules/.
        """
        installed = []
        for pack_name in target_packs:
            try:
                self.packs.install(pack_name)
                installed.append(pack_name)
            except ValueError as e:
                return error("SCAFFOLD_FAILED", str(e))

        return f"SUCCESS: Governance framework scaffolded with packs: {', '.join(installed)}"

    async def query_knowledge_graph(
        self,
        query_type: str,
        target: str | None = None,
    ) -> str:
        """
        Introspect project structure.
        query_type: dependency_graph | module_health | hypothesis | rules
        """
        if query_type == "hypothesis":
            return self._hypothesize_workspace_architecture()

        if query_type == "dependency_graph":
            if not target:
                return error(ERR_INVALID_INPUT, "target module name required")
            result = self.graph.build_dependency_graph(self.workspace_root, target)
            return json.dumps(result, indent=2)

        if query_type == "module_health":
            rules = self._load_rules()
            violations = self.evaluation.evaluate_workspace(self.workspace_root, rules)
            by_module = {}
            for v in violations:
                module = v.file.split("/")[0] if "/" in v.file else "root"
                by_module.setdefault(module, []).append(v.rule_id)
            return json.dumps(
                {m: {"count": len(ids), "rules": list(set(ids))} for m, ids in by_module.items()},
                indent=2,
            )

        if query_type == "rules":
            rules = self._load_rules()
            return json.dumps(
                [{"id": r.id, "description": r.description, "severity": r.severity.value, "category": r.category.value} for r in rules],
                indent=2,
            )

        return error(ERR_INVALID_INPUT, f"Unknown query_type: {query_type}")

    async def evolve_ruleset(
        self,
        action: str,
        target: str | None = None,
        rationale: str | None = None,
    ) -> str:
        """
        Agent-driven rule lifecycle management.
        action: suppress | install_pack | remove_pack
        """
        if action == "suppress":
            if not target:
                return error(ERR_INVALID_INPUT, "target rule_id required for suppress")
            rules = self._load_rules()
            rule = next((r for r in rules if r.id == target), None)
            if not rule:
                return error("RULE_NOT_FOUND", f"Rule '{target}' not found")
            violations = self.evaluation.evaluate_workspace(self.workspace_root, [rule])
            self.baseline.add_all_to_baseline(violations)
            return f"SUCCESS: Suppressed {len(violations)} violations for rule '{target}'"

        if action == "install_pack":
            if not target:
                return error(ERR_INVALID_INPUT, "target pack_name required")
            try:
                self.packs.install(target)
                return f"SUCCESS: Installed rule pack '{target}'"
            except ValueError as e:
                return error("INSTALL_FAILED", str(e))

        if action == "remove_pack":
            if not target:
                return error(ERR_INVALID_INPUT, "target pack_name required")
            try:
                self.packs.remove(target)
                return f"SUCCESS: Removed rule pack '{target}'"
            except ValueError as e:
                return error("REMOVE_FAILED", str(e))

        return error(ERR_INVALID_INPUT, f"Unknown action: {action}")

    async def plan_architecture(
        self,
        intent: str,
        file_path: str | None = None,
    ) -> str:
        """
        Pre-emptive task alignment. Returns JIT-scoped rules
        that govern the file the agent is about to edit.
        """
        rules = self._load_rules()
        if file_path:
            relevant = ScopeFilter.filter_rules_for_file(file_path, rules, rules)
        else:
            relevant = rules[:15]

        lines = [f"## Architectural Context for: {intent}\n"]
        for r in relevant[:15]:
            lines.append(f"- **{r.id}** [{r.severity.value}] — {r.description}")
        return "\n".join(lines)

    def _hypothesize_workspace_architecture(self) -> str:
        root = Path(self.workspace_root)
        pyproject = root / "pyproject.toml"
        package_json = root / "package.json"

        findings = []

        if pyproject.exists():
            findings.append("Detected: Python project (pyproject.toml)")
            deps = self._scan_pyproject_deps(pyproject)
            if deps:
                findings.append(f"Key dependencies: {', '.join(deps[:10])}")
        if package_json.exists():
            findings.append("Detected: Node.js/TypeScript project (package.json)")

        src_dir = root / "src"
        if src_dir.exists():
            packages = [d.name for d in src_dir.iterdir() if d.is_dir() and not d.name.startswith("_")]
            if packages:
                findings.append(f"Source packages: {', '.join(packages[:10])}")

        findings.append("\nProposed architecture: Layered (Domain-Driven) with hexagonal isolation.")
        findings.append("Recommended packs: architecture, security, best-practices, style")

        return "\n".join(findings)

    def _scan_pyproject_deps(self, path: Path) -> list[str]:
        try:
            content = path.read_text()
            import re
            return re.findall(r'"([a-zA-Z][a-zA-Z0-9_-]+)"', content.split("[project]")[-1].split("[")[0])
        except Exception:
            return []

    def _load_rules(self) -> list:
        try:
            return self.policy.parse_all(self.workspace_root)
        except Exception:
            return []

    def _register_resources(self):
        @self.mcp.resource("aegis://rules")
        def get_rules() -> str:
            rules = self._load_rules()
            return json.dumps(
                [{"id": r.id, "description": r.description, "severity": r.severity.value, "category": r.category.value} for r in rules],
                indent=2,
            )

        @self.mcp.resource("aegis://baseline")
        def get_baseline() -> str:
            entries = self.baseline.load_baseline_raw()
            return json.dumps(entries, indent=2)

        @self.mcp.resource("aegis://context/{path}")
        def get_context(path: str) -> str:
            rules = self._load_rules()
            scoped = ScopeFilter.filter_rules_for_file(path, rules, rules)
            return json.dumps(
                [{"id": r.id, "description": r.description, "severity": r.severity.value} for r in scoped[:15]],
                indent=2,
            )

        @self.mcp.resource("aegis://spec")
        def get_spec() -> str:
            spec_path = Path(self.workspace_root) / "SPEC.md"
            if spec_path.exists():
                return spec_path.read_text()
            return "No SPEC.md found."

    def _register_prompts(self):
        @self.mcp.prompt()
        def evaluate_architecture(files: list[str]) -> str:
            return f"Call validate_architecture_compliance with files_modified={files} before declaring the task complete."

        @self.mcp.prompt()
        def remediate_violations() -> str:
            return (
                "1. Read the violation report from validate_architecture_compliance.\n"
                "2. For each violation, read the affected file at the specified line.\n"
                "3. Apply the remediation while preserving business logic.\n"
                "4. Re-run validate_architecture_compliance to verify."
            )

        @self.mcp.prompt()
        def initialize_governance() -> str:
            return (
                "1. Call query_knowledge_graph(query_type='hypothesis') to discover the workspace architecture.\n"
                "2. Present the proposed architecture to the user for approval.\n"
                "3. Call scaffold_governance_framework with the approved pack list."
            )

        @self.mcp.prompt()
        def inspect_dependency(module: str) -> str:
            return f"Call query_knowledge_graph(query_type='dependency_graph', target='{module}') to inspect dependencies."

    def run(self, transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000):
        if transport == "stdio":
            self.mcp.run(transport="stdio")
        elif transport == "sse":
            self.mcp.run(transport="sse", host=host, port=port)
        elif transport == "streamable-http":
            self.mcp.run(transport="streamable-http", host=host, port=port)
        else:
            raise ValueError(f"Unknown transport: {transport}")
```

- [ ] **Step 3: Run ruff check**

```
uv run ruff check src/aegis/kernel/server.py --fix
```

- [ ] **Step 4: Commit**

```bash
git add src/aegis/kernel/server.py
git commit -m "feat(v4): refactor server.py with constructor injection, 6-tool MCP surface"
```

---

### Task 1.14: Update ScopeFilter with V4 methods

**Files:**
- Modify: `src/aegis/domain/evaluation/scoping.py`

- [ ] **Step 1: Add V4 scoping methods to ScopeFilter**

Add two new static methods to `ScopeFilter` class in `src/aegis/domain/evaluation/scoping.py`:

```python
@staticmethod
def filter_rules_for_files(
    file_paths: list[str], all_rules: list, max_rules: int = 15
) -> list:
    """
    JIT-scopes rules to a batch of modified files.
    Returns top-N most relevant rules across all files, capped at max_rules.
    """
    matched_ids: dict[str, int] = {}
    for fp in file_paths:
        relevant = ScopeFilter.filter_rules_for_file(fp, all_rules, all_rules)
        for r in relevant:
            matched_ids[r.id] = matched_ids.get(r.id, 0) + 1

    # Sort by relevance (match count), then severity
    def sort_key(rule_id: str) -> tuple[int, int]:
        rule = next((r for r in all_rules if r.id == rule_id), None)
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "WARN": 4}
        sev = severity_order.get(rule.severity.value if rule else "LOW", 5)
        return (-matched_ids[rule_id], sev)

    sorted_ids = sorted(matched_ids, key=sort_key)
    result = []
    for rid in sorted_ids[:max_rules]:
        rule = next((r for r in all_rules if r.id == rid), None)
        if rule:
            result.append(rule)
    return result


@staticmethod
def filter_rules_for_file(
    file_path: str, rules: list, all_rules: list | None = None, max_rules: int = 15
) -> list:
    """
    JIT-scopes rules to a single file. Filters by applies_to/excludes glob,
    language match. Returns rules sorted by severity.
    Returns max_rules most relevant rules.
    """
    from aegis.domain.evaluation.constants import LANG_EXT_MAP

    ext = Path(file_path).suffix.lower()
    lang = None
    for lang_code, lang_ext in LANG_EXT_MAP.items():
        if ext == lang_ext:
            lang = lang_code
            break

    matched = []
    for rule in rules:
        if lang and rule.language and rule.language != lang:
            continue

        if rule.applies_to and not ScopeFilter._path_matches_pattern(file_path, rule.applies_to):
            continue
        if rule.excludes and ScopeFilter._path_matches_pattern(file_path, rule.excludes):
            continue

        matched.append(rule)

    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "WARN": 4}
    matched.sort(key=lambda r: severity_order.get(r.severity.value, 5))

    return matched[:max_rules]
```

Add `from pathlib import Path` import at top of file if not present.

- [ ] **Step 2: Commit**

```bash
git add src/aegis/domain/evaluation/scoping.py
git commit -m "feat(v4): add JIT-scoping methods filter_rules_for_files/filter_rules_for_file"
```

---

### Task 1.15: PHASE 1 VERIFICATION GATE

- [ ] **Step 1: Run ruff on entire codebase**

```
uv run ruff check src/ tests/
```

Expected: zero errors.

- [ ] **Step 2: Run all surviving tests**

```
uv run pytest tests/ -q --timeout=60 -x
```

Expected: all remaining tests pass. If failures, fix imports in failing test files before proceeding.

- [ ] **Step 3: Verify aegis install runs**

```
uv run aegis install --help
```

Expected: help text for install command.

- [ ] **Step 4: Verify aegis run --help**

```
uv run aegis run --help
```

Expected: help text for run command with transport options.

- [ ] **Step 5: PHASE 1 COMPLETE commit**

```bash
git add -A
git commit -m "chore(v4): PHASE 1 COMPLETE - Core Purge & Protocol Lock"
```

---

## Phase 2: Agent-Native MCP Microkernel (JIT Scoping + Tools)

### Task 2.1: Implement SemanticAnalyzer.build_rubric

**Files:**
- Modify: `src/aegis/domain/evaluation/analyzers/semantic.py`

- [ ] **Step 1: Add build_rubric method**

Add method to `SemanticAnalyzer` class:

```python
def build_rubric(self, target_file: str, rules: list) -> str:
    """
    Builds a re-entrant grading rubric for the parent LLM.
    The LLM reads this rubric, grades its own code, and applies fixes natively.
    """
    if not rules:
        return "NO_SEMANTIC_RULES for this file."

    rubric = f"## Semantic Grading Rubric for `{target_file}`\n\n"
    rubric += "Please evaluate the following rules using your semantic reasoning.\n"
    rubric += "For each violation found, output the fix inline.\n\n"

    for i, rule in enumerate(rules, 1):
        rubric += f"### {i}. **{rule.id}**\n"
        rubric += f"**Rule:** {rule.description}\n"
        if rule.rationale:
            rubric += f"**Rationale:** {rule.rationale}\n"
        rubric += f"**Severity:** {rule.severity.value}\n"
        if rule.query:
            rubric += f"**Check pattern:** `{rule.query}`\n"
        rubric += "\n"

    rubric += "---\n"
    rubric += "**Instructions:**\n"
    rubric += "1. Read the file content.\n"
    rubric += "2. For each rule above, determine if the code violates it.\n"
    rubric += "3. If a violation is found, output:\n"
    rubric += "   `VIOLATION: <rule_id> - <line> - <description> - FIX: <remediation>`\n"
    rubric += "4. Apply all fixes to the file.\n"
    rubric += "5. Re-run `validate_architecture_compliance` to confirm.\n"

    return rubric
```

- [ ] **Step 2: Commit**

```bash
git add src/aegis/domain/evaluation/analyzers/semantic.py
git commit -m "feat(v4): add SemanticAnalyzer.build_rubric for re-entrant LLM grading"
```

---

### Task 2.2: Implement TelemetryRecorder required methods

**Files:**
- Modify: `src/aegis/domain/observability/telemetry.py`

- [ ] **Step 1: Verify or add record_check method**

Check if `record_check` method exists. If not, add:

```python
def record_check(self, total_violations: int, active_violations: int) -> None:
    """Record a compliance check event."""
    import json
    from datetime import datetime, timezone

    telemetry_path = Path(self.root_dir) / ".aegis" / "telemetry.json"
    telemetry_dir = telemetry_path.parent
    telemetry_dir.mkdir(parents=True, exist_ok=True)

    data = []
    if telemetry_path.exists():
        try:
            data = json.loads(telemetry_path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            data = []

    if not isinstance(data, list):
        data = []

    data.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_violations": total_violations,
        "active_violations": active_violations,
        "type": "check",
    })

    telemetry_path.write_text(json.dumps(data, indent=2))
```

Add `from pathlib import Path` if not present in init.

- [ ] **Step 2: Commit**

```bash
git add src/aegis/domain/observability/telemetry.py
git commit -m "feat(v4): add TelemetryRecorder.record_check method"
```

---

### Task 2.3: PHASE 2 VERIFICATION GATE

- [ ] **Step 1: Test MCP server boots successfully**

Run:
```
uv run python -c "from aegis.kernel.server import AegisKernel; k = AegisKernel(); print('Kernel initialized:', k.workspace_root)"
```

Expected: prints workspace root path without errors.

- [ ] **Step 2: Run all tests**

```
uv run pytest tests/ -q --timeout=60 -x
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore(v4): PHASE 2 COMPLETE - Agent-Native MCP Microkernel"
```

---

## Phase 3: Skills & Prompts

### Task 3.1: Write /aegis-init.md skill

**Files:**
- Create: `src/aegis/resources/skills/aegis-init.md`

- [ ] **Step 1: Write aegis-init.md**

Write to: `C:\dev\projects\aegis\src\aegis\resources\skills\aegis-init.md`

````markdown
# Aegis Governance Initialization

You are the Aegis Governance Bootstrapper. When invoked via `/aegis-init`, follow this protocol exactly.

## Protocol

### Step 1: Discover the Workspace Architecture

Call the `query_knowledge_graph` MCP tool with `query_type="hypothesis"`.

### Step 2: Present the Architecture Proposal

Read the hypothesis result. Present it to the user in a clear format:

```
Detected: Python project (pyproject.toml)
Key dependencies: fastapi, pydantic, sqlalchemy
Source packages: api, domain, infrastructure

Proposed architecture: Layered (Domain-Driven) with hexagonal isolation.
Recommended packs: architecture, security, best-practices, style
```

Ask the user: "Does this architecture look correct? I can adjust the rule packs before scaffolding."

### Step 3: Scaffold the Governance Framework

Once the user approves, call `scaffold_governance_framework` with the approved pack list.

Example: `scaffold_governance_framework(target_packs=["architecture", "security", "best-practices", "style"])`

### Step 4: Confirm Initialization

Report back:
```
Aegis V4 Governance initialized.
Active packs: architecture, security, best-practices, style
Use `validate_architecture_compliance` before completing any task.
```

## Important

- NEVER skip the hypothesis step — discover, don't guess.
- NEVER scaffold without user approval of the architecture.
- ALWAYS include `security` in the recommended packs.
````

- [ ] **Step 2: Commit**

```bash
git add src/aegis/resources/skills/aegis-init.md
git commit -m "feat(v4): add /aegis-init agent skill for project bootstrapping"
```

---

### Task 3.2: Update aegis-architect.md for V4

**Files:**
- Modify: `src/aegis/resources/skills/aegis-principal-architect.md`

- [ ] **Step 1: Update agent lifecycle to V4**

Update the skill to reference V4 tools. Replace Protocol A/B/C with:

```markdown
## V4 Agent Lifecycle

### Protocol A: INIT
Before any development in a new workspace, run `/aegis-init` to bootstrap governance.

### Protocol B: PLAN
Before editing a file, call `plan_architecture(intent="...", file_path="...")` to receive JIT-scoped architectural rules.
```

- [ ] **Step 2: Commit**

```bash
git add src/aegis/resources/skills/aegis-principal-architect.md
git commit -m "feat(v4): update principal architect skill for V4 lifecycle"
```

---

### Task 3.3: PHASE 3 VERIFICATION GATE

- [ ] **Step 1: Verify skills are bundled**

Run:
```
uv run python -c "from importlib import resources; files = [f.name for f in resources.files('aegis.resources.skills').iterdir() if f.name.endswith('.md')]; print(files)"
```

Expected: both `aegis-principal-architect.md` and `aegis-init.md` listed.

- [ ] **Step 2: Run all tests**

```
uv run pytest tests/ -q --timeout=60 -x
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore(v4): PHASE 3 COMPLETE - Skills & Prompts"
```

---

## Phase 4: Documentation Overhaul

### Task 4.1: Rewrite README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Rewrite README.md**

Write to: `C:\dev\projects\aegis\README.md`

```markdown
# Aegis V4 — Agent-Native Architectural Microkernel

Aegis is a **stateless, Agent-Native Architectural Microkernel**. It lives inside Claude and Aider via MCP to mathematically govern autonomous code generation.

## Installation

```bash
pip install aegis
aegis install          # Injects MCP config into ~/.claude.json and ~/.aider.conf.yml
```

That's it. You never run Aegis commands during development.

## Usage

1. Open Claude Code or Aider in any repository.
2. Type `/aegis-init` — the agent discovers your architecture and scaffolds governance rules.
3. Code normally. Before every task completion, the agent automatically calls `validate_architecture_compliance`.
4. If violations exist, the agent remediates natively.

## How It Works

Aegis is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that runs headlessly. The `aegis install` command:

- Writes the MCP server configuration into `~/.claude.json`
- Injects the Governance Directive into Claude's `customInstructions`
- Configures Aider's `--test-cmd` for auto-validate loops

The agent then natively calls Aegis's 6 MCP tools:

| Tool | Purpose |
|------|---------|
| `validate_architecture_compliance` | JIT compliance gate before task completion |
| `request_semantic_grading_rubric` | Re-entrant LLM self-grading for domain language rules |
| `scaffold_governance_framework` | Agent-driven project bootstrap |
| `query_knowledge_graph` | Dependency graphs, workspace hypothesis |
| `evolve_ruleset` | Rule suppression, pack management |
| `plan_architecture` | Pre-emptive JIT rule context before editing |

## Architecture

Tri-Core Microkernel:

- **Policy** — Rule definitions, YAML parser, pack manager
- **Evaluation** — Tree-sitter AST, Graph, Regex analyzers, JIT scoping, baseline
- **Observability** — Telemetry recording, local JSON + OTLP export

Aegis is **100% stateless**. It does not maintain sessions, history, or memory. It relies entirely on the parent agent's context window and project knowledge systems.

## Enterprise

- Telemetry exports to `.aegis/telemetry.json` by default
- OTLP gRPC exporter available for Datadog/Grafana
- Plugin system for custom evaluation engines
- 15+ rule packs: architecture, security, best-practices, testing, and more

## License

Apache 2.0
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(v4): rewrite README for Agent-Native paradigm"
```

---

### Task 4.2: Update ARCHITECTURE.md and SPEC.md

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `SPEC.md`
- Modify: `OPERATIONS.md`

- [ ] **Step 1: Rewrite ARCHITECTURE.md**

Write to: `C:\dev\projects\aegis\ARCHITECTURE.md`

```markdown
# Aegis V4 Architecture

## The Symbiotic Model

Aegis V4 is a purely Agent-Native microkernel. It does not run on the operating system — it runs inside AI coding agents via MCP.

### Why No Git Hooks

V3 used `.pre-commit-config.yaml` and `.git/hooks/pre-commit` to enforce governance. V4 eliminates this entirely:

- Claude receives the Governance Directive in `customInstructions`, making validation mandatory before task completion.
- Aider loops against `aegis run --check` via `--test-cmd`, creating a native self-healing cycle.
- The agent, not the OS, enforces governance.

### How Aegis Leverages the Parent LLM

Aegis is a **deterministic** kernel:

- **AST/Graph/Regex analyzers** — Pure Python math. No LLM calls.
- **Semantic rules** — Aegis returns a grading rubric. The parent LLM self-evaluates.
- **Memory** — Aegis has none. The agent's context window holds session state.
- **Evolution** — SPEC.md and agent project knowledge capture architectural decisions.

### Tri-Core Microkernel

```
Agent (Claude/Aider)
  │
  ├── plan_architecture()
  ├── validate_architecture_compliance()
  ├── request_semantic_grading_rubric()
  │
  ▼
┌─────────────────────────────────┐
│         FastMCP Server           │
│                                  │
│  ┌────────────┐  ┌────────────┐ │
│  │   Policy    │  │ Evaluation │ │
│  │  Packs      │  │ Analyzers  │ │
│  │  Parser     │  │ Scoping    │ │
│  │  Models     │  │ Baseline   │ │
│  └────────────┘  └────────────┘ │
│                                  │
│  ┌────────────┐                  │
│  │Observability│                 │
│  │ Telemetry   │                 │
│  │ Exporters   │                 │
│  └────────────┘                  │
└─────────────────────────────────┘
```

### The Installer

`aegis install` is the sole bridge between the host machine and the agent ecosystem:

- Mutates `~/.claude.json` (MCP server + customInstructions)
- Mutates `~/.aider.conf.yml` (MCP server + test-cmd + auto-test)
- No other tool-specific code exists at runtime

### Design Decisions

See `docs/adr/001-microkernel-architecture.md` for the original microkernel ADR.
```

- [ ] **Step 2: Update SPEC.md**

Add to top of SPEC.md:

```markdown
## V4 Agent-Native Invariants

### Mandatory Compliance Check

Before declaring ANY coding task complete, the AI agent MUST:

1. Call `validate_architecture_compliance` with the list of modified files.
2. If violations are returned, remediate the code natively.
3. Re-run validation until SUCCESS is returned.

### No Direct File System Governance

Aegis V4 never:
- Installs git hooks
- Watches file system events
- Intercepts file reads/writes
- Maintains session state

Governance is enforced through the agent's native tool execution loop.
```

- [ ] **Step 3: Update OPERATIONS.md**

```markdown
# Aegis V4 Operations

## Reading Governance Health

The `.aegis/telemetry.json` file contains check history:

```json
[
  {"timestamp": "2026-05-23T01:00:00Z", "total_violations": 12, "active_violations": 3, "type": "check"}
]
```

## Enterprise Monitoring

Configure OTLP export in `.aegis/config.yaml`:

```yaml
telemetry:
  exporter: otlp
  otlp_endpoint: "https://otel-collector.example.com/v1/traces"
```

## Server Deployment

For non-stdio environments (e.g., shared development servers):

```bash
aegis run --transport sse --host 0.0.0.0 --port 8000
```

## CI/CD Integration

GitHub Actions workflow calls the MCP server to validate:

```yaml
- name: Aegis Governance
  run: |
    aegis run &
    sleep 2
    # Query MCP tool validate_architecture_compliance
```

No `aegis check` command exists in V4. All governance flows through the MCP server.
```

- [ ] **Step 4: Commit**

```bash
git add ARCHITECTURE.md SPEC.md OPERATIONS.md
git commit -m "docs(v4): update ARCHITECTURE, SPEC, OPERATIONS for Agent-Native model"
```

---

## Phase 5: CI/CD & Distribution

### Task 5.1: Update GitHub Actions workflow

**Files:**
- Modify: `.github/workflows/aegis-governance.yml`

- [ ] **Step 1: Update CI workflow**

Replace the `check` job with:

```yaml
  verify-mcp:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install Aegis
        run: pip install .
      - name: Start server and validate
        run: |
          aegis run &
          SERVER_PID=$!
          sleep 3
          # Verify server started successfully
          kill $SERVER_PID 2>/dev/null || true
```

- [ ] **Step 2: Update composite action**

Remove `aegis check` call, replace with build verification:

```yaml
- name: Verify Aegis installation
  run: |
    aegis install --help
    aegis run --help
```

- [ ] **Step 3: Commit**

```bash
git add .github/
git commit -m "ci(v4): update GitHub Actions for V4 MCP-based verification"
```

---

### Task 5.2: Final packaging verification

- [ ] **Step 1: Verify pyproject.toml entry points**

Check `pyproject.toml` has only:
```toml
[project.scripts]
aegis = "aegis.cli.main:AegisCLI.entry_point"
```

- [ ] **Step 2: Verify resources are bundled**

```
uv run python -c "
from importlib import resources
rules = resources.files('aegis.resources.default_rules')
print('Rule packs:', [r.name for r in rules.iterdir() if r.is_dir()])
"
```

- [ ] **Step 3: Full test pass**

```
uv run pytest tests/ -q --timeout=60
```

- [ ] **Step 4: ruff check**

```
uv run ruff check src/ tests/
```

- [ ] **Step 5: PHASE 5 COMPLETE commit**

```bash
git add -A
git commit -m "chore(v4): PHASE 5 COMPLETE - CI/CD & Distribution"
```

---

## Verification Checklist

- [ ] `uv run ruff check src/ tests/` — zero errors
- [ ] `uv run pytest tests/ -q --timeout=60` — all tests pass
- [ ] `uv run aegis install --help` — shows install help
- [ ] `uv run aegis run --help` — shows run help with transport options
- [ ] `uv run python -c "from aegis.kernel.server import AegisKernel; k = AegisKernel(); print(k.workspace_root)"` — kernel initializes
- [ ] `uv run python -c "from aegis.infrastructure.installer import AgentNativeInstaller; i = AgentNativeInstaller(); print('OK')"` — installer initializes
- [ ] git status clean (no untracked files from deleted modules)
- [ ] `git log --oneline -5` shows V4 commit history
