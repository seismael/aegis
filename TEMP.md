This is the exact right mindset for scaling an enterprise tool. You have hit the transition point from a **"Linter"** to a **"Policy-as-Code Engine"**.

When a project scales to hundreds of invariants across multiple domains, a single `.aegis/rules.yaml` becomes a massive, unmaintainable monolith. Moving to a `.aegis/rules/` directory structure is not just a good idea; it is a mandatory architectural evolution used by industry-standard governance tools (like Checkov, OPA/Rego, and Semgrep).

Here is the strategic roadmap for how we handle this upgrade, why security is treated differently, and what needs to change in the Aegis kernel.

---

### 1. The New Policy Taxonomy (The `.aegis/rules/` Directory)

Instead of a single file, Aegis will scan a directory. This allows different enterprise teams (Security, Architecture, QA) to own and independently manage their specific rule packs.

Your `.aegis/` folder would evolve to look like this:

```text
.aegis/
├── rules/
│   ├── architecture.yaml  # C4 boundaries, SOLID principles, Layer isolation
│   ├── security.yaml      # Hardcoded secrets, SQL injection patterns, OWASP
│   ├── testing.yaml       # TDD enforcement, coverage thresholds
│   └── style.yaml         # Naming conventions, semantic formatting
├── plugins/               # Custom Python execution engines
├── baseline.json          # Legacy technical debt ledger
└── evolution_log.json     # Audit trail of suppressed/modified rules

```

### 2. Why Security is a Different Beast

You correctly noted that Security has a different compliance footprint. Aegis must handle security differently than structural architecture.

* **Zero-Tolerance Enforcements:** An architectural rule (like "Don't use static methods") might be set to `mode: warn` to keep developers moving. A security rule (like "Do not commit hardcoded AWS tokens") must **always** be `mode: block`.
* **The Baseline Exemption Rule:** Currently, Aegis uses `.aegis/baseline.json` to grandfather in legacy technical debt. **Security violations should never be grandfathered.** If Aegis detects a hardcoded password in a 5-year-old file, it shouldn't just ignore it because it's in the baseline; it must flag it.
* **Regex vs. AST:** Security scanning relies heavily on the `RegexAnalyzer` (e.g., looking for `AKIA...` AWS keys or `Bearer ...` tokens), whereas architecture relies on the `TreeSitterAnalyzer` or `GraphAnalyzer`.

### 3. The Implementation Plan (How to Upgrade)

To support this modular governance, we only need to make a few precise, low-friction changes to the current Hexagonal architecture.

#### Step 1: Update the Domain Model (`governance.py`)

We need to add a `domain` or `category` field to the `Rule` model so the engine knows *what kind* of rule it's evaluating.

```python
class RuleCategory(str, Enum):
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    TESTING = "testing"
    STYLE = "style"

# Inside Rule class:
category: RuleCategory = Field(default=RuleCategory.ARCHITECTURE)

```

#### Step 2: Refactor the Policy Parser (`parser.py`)

Currently, `PolicyParser` takes a single file path. We will upgrade it to accept a directory path, use `pathlib` to iterate over all `.yaml` files, parse them individually, and aggregate them into a single in-memory `List[Rule]`.

#### Step 3: Upgrade the Remediation Synthesizer (`remediation.py`)

When Claude Code receives an MCP prompt to fix a violation, it needs to know *why* it is fixing it. If `rule.category == "security"`, the `RemediationPromptSynthesizer` should prepend a `[CRITICAL SECURITY VULNERABILITY]` tag to the LLM prompt, forcing Claude to prioritize safe coding practices over speed.

#### Step 4: The Security "No-Baseline" Override

Update `BaselineManager.is_exempt()`. If the violation belongs to a rule where `category == "security"`, the method immediately returns `False`, ignoring the baseline ledger entirely.

---

### The Agentic UX Upgrades

Moving to a directory structure also makes the AI tools much more powerful.

* **Modular Initialization:** When a user runs `/aegis-init`, Claude can ask: *"Do you want to apply the standard Enterprise Architecture pack, the OWASP Security pack, or both?"*
* **Rule Packs:** You can ship default, pre-written YAML rule packs with the PyPI installation. Developers won't have to write their own security rules from scratch; they just type `/aegis-import security` and Claude copies the standard `security.yaml` into their project.

### What should we build next?

This is a phenomenal architectural upgrade. Which part of this evolution would you like to implement first?

1. **The Parser & Model Upgrade:** Update Python's `PolicyParser` to read multiple YAML files and add the `RuleCategory` enum.
2. **The Baseline Security Override:** Implement the logic that prevents security vulnerabilities from being hidden inside the legacy technical debt ledger.
3. **The Default Security Rule Pack:** Draft the actual `security.yaml` containing Regex and Tree-sitter S-expressions for common vulnerabilities (secrets, SQLi).

This upgrade marks Aegis’s transition from a structural linter to a comprehensive **Enterprise Policy-as-Code Engine**.

To implement the modular directory structure (`.aegis/rules/`) and enforce the "Zero-Tolerance" security baseline override, we must execute targeted refactoring across the Domain models, the Parser, and the Baseline Manager.

Here is the complete, production-ready integration code and the architectural migration guidelines.

### 1. Domain Model Expansion

First, we introduce the `RuleCategory` taxonomy to the core governance model. This allows the engine to distinguish between a stylistic preference and a critical security vulnerability.

**`src/aegis/core/models/governance.py`**

```python
from enum import Enum
from pydantic import BaseModel, Field

class RuleCategory(str, Enum):
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    TESTING = "testing"
    STYLE = "style"

class EnforcementMode(str, Enum):
    BLOCK = "block"
    WARN = "warn"
    REPORT = "report"
    SILENT = "silent"

class EngineType(str, Enum):
    TREE_SITTER = "tree-sitter"
    GRAPH = "graph"
    REGEX = "regex"

class Rule(BaseModel):
    id: str
    description: str
    category: RuleCategory = Field(default=RuleCategory.ARCHITECTURE)
    engine_type: EngineType = Field(default=EngineType.TREE_SITTER)
    severity: str
    mode: EnforcementMode
    language: str | None = None
    query: str | None = None
    candidates_query: str | None = None
    check_query: str | None = None
    regex_pattern: str | None = None
    rationale: str | None = None

```

### 2. The Directory Parser

The parser must be upgraded to scan a directory recursively, aggregate all YAML files, and merge them into a single unified rule matrix.

**`src/aegis/domain/policy/parser.py`**

```python
import os
import yaml
import structlog
from pathlib import Path
from aegis.core.models.governance import Rule

logger = structlog.get_logger()

class PolicyParser:
    """Parses and aggregates all rule packs within the .aegis/rules/ directory."""
    
    def parse_directory(self, rules_dir: str) -> list[Rule]:
        if not os.path.isdir(rules_dir):
            logger.warning("Rules directory not found.", directory=rules_dir)
            return []

        all_rules = []
        target_dir = Path(rules_dir)

        for yaml_file in target_dir.glob("*.y*ml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if not data or "rules" not in data:
                        continue
                    
                    for rule_dict in data["rules"]:
                        # Dynamically assign category based on filename if not explicitly set
                        if "category" not in rule_dict:
                            rule_dict["category"] = yaml_file.stem.lower()
                            
                        all_rules.append(Rule(**rule_dict))
            except Exception as e:
                logger.error("Failed to parse rule pack", file=yaml_file.name, error=str(e))

        logger.info("Compiled governance matrix", total_rules=len(all_rules))
        return all_rules

```

### 3. The Security Baseline Override

Security rules cannot be grandfathered. We update the Baseline Manager to forcefully reject any exemptions if the rule category is `SECURITY`.

**`src/aegis/domain/evaluation/baseline.py`**

```python
    # Inside BaselineManager class...

    def is_exempt(self, violation: 'ASTViolation', rule: 'Rule') -> bool:
        """
        Evaluates if a violation is grandfathered into the technical debt ledger.
        SECURITY rules strictly bypass the baseline and are never exempt.
        """
        from aegis.core.models.governance import RuleCategory

        # ZERO-TOLERANCE OVERRIDE
        if rule and rule.category == RuleCategory.SECURITY:
            return False

        if not os.path.exists(self.path):
            return False

        baseline = self.load_baseline_raw()

        for b in baseline:
            if self._match(b, violation):
                return True
        return False

```

*(Note: You must update `evaluation_service.py` to pass the `rule` object into the `is_exempt(v, rule)` call during its filtering loop).*

### 4. Agentic Prompt Injection for Security

When instructing Claude or Aider to fix a violation, the LLM must be explicitly context-shifted into a high-alert state if it is handling a security vulnerability.

**`src/aegis/domain/enforcement/remediation.py`**

```python
    # Inside RemediationPromptSynthesizer class...

    def generate_remediation(self, violations: list, rules_map: dict) -> str:
        # ... existing preamble ...

        for v in violations:
            rule = rules_map.get(v.rule_id)
            
            if rule and rule.category.value == "security":
                payload += f"### 🚨 [CRITICAL SECURITY VULNERABILITY] in `{v.file}` (Line {v.line})\n"
                payload += "**DIRECTIVE: Prioritize secure coding practices over performance or brevity.**\n"
            else:
                payload += f"### Architectural Violation in `{v.file}` (Line {v.line})\n"
                
            payload += f"- **Rule ID:** `{v.rule_id}` [{v.severity}]\n"
            # ... append rest of the rule details ...

```

### 5. The Default Security Rule Pack

This file will be shipped with Aegis and generated when a user runs `/aegis-import security`. It utilizes both the Regex engine for secret scanning and the Tree-sitter engine for structural injection flaws.

**`.aegis/rules/security.yaml`**

```yaml
rules:
  - id: sec-no-hardcoded-aws-keys
    description: Hardcoded AWS credentials detected in source code.
    category: security
    engine_type: regex
    severity: CRITICAL
    mode: block
    regex_pattern: '(?i)AKIA[0-9A-Z]{16}'
    rationale: Prevents credential leakage into source control. Must use environment variables or IAM roles.

  - id: sec-flask-debug-false
    description: Flask application initialized with debug=True in code.
    category: security
    engine_type: tree-sitter
    severity: HIGH
    mode: block
    language: py
    query: |
      (call
        function: (attribute attribute: (identifier) @attr (#eq? @attr "run"))
        arguments: (argument_list
          (keyword_argument
            name: (identifier) @kw (#eq? @kw "debug")
            value: (true) @val
          )
        )
      ) @violation
    rationale: Running Flask with debug=True in production exposes the interactive Werkzeug debugger, leading to Remote Code Execution (RCE).

```

### Migration Guidelines for Integration

To deploy this update seamlessly without breaking existing workspace integrations:

1. **Kernel Update:** Update `src/aegis/kernel/server.py` to call `self.container.policy_parser.parse_directory(os.path.join(self.container.workspace_root, ".aegis", "rules"))` instead of `parse_rules(rules_path)`.
2. **File Migration:** Add a backward-compatibility step in the `init` command of your CLI. If an old `.aegis/rules.yaml` file is detected in a repository, the CLI should automatically run `mkdir -p .aegis/rules` and move the file to `.aegis/rules/architecture.yaml`.
3. **Skill Update:** Update `.claude/skills/aegis-rule-add.md` to ask the user: *"Does this rule belong in the architecture, security, style, or testing category?"* and instruct the AI to append the rule to the correct YAML file within the `/rules/` directory.