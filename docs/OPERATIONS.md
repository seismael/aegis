# Aegis V4 Operations & CLI Manual

> Operational guide for deploying, executing, and auditing Aegis Native Governance Engine.

---

## 1. CLI Commands (`aegis`)

### 1.1 Workspace Initializer (`aegis init`)

Scaffolds `.aegis/rules/`, `.aegis/mcp.json`, `pyproject.toml`, and harness instructions (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`).

```bash
aegis init --workspace .
```

### 1.2 Proactive Plan Verification CLI (`aegis agent`)

Executes proactive pre-flight plan verification directly from the command line:

```bash
aegis agent --workspace . --plan-import aegis.infrastructure --target-module aegis.domain.service
```

### 1.3 Microkernel MCP Server (`aegis run`)

Starts the FastMCP microkernel server:

```bash
# Stdio transport (default for AI harnesses)
aegis run

# HTTP SSE transport for remote server setups
aegis run --transport sse --host 0.0.0.0 --port 8000
```

---

## 2. Python SDK Operational Integration

```python
from aegis import create_aegis_agent, RegistryLoader

# Load rules from local .aegis/rules
rules = RegistryLoader.load(".")

# Instantiate AegisAgent
agent = create_aegis_agent(rules=rules, workspace_root=".")

# Execute pre-flight intent verification
res = agent.verify_plan(["infrastructure.db"], "domain.service")
if not res["plan_valid"]:
    print(res["feedback"])
```

---

## 3. Observability & Telemetry

- **Local Telemetry Ledger**: Audit history stored at `.aegis/telemetry.json`.
- **Scorecard Dashboard**: Living project scorecard at `.aegis/AEGIS.md`.
- **OTLP gRPC Export**: Enterprise trace streaming configurable via `aegis.yaml`.
