"""Structured return types for MCP kernel tools.

FastMCP serializes Pydantic models to JSON automatically.
Agents receive native structured data instead of parsing markdown strings.
"""

from pydantic import BaseModel


class RuleInfo(BaseModel):
    """Rule metadata for structured tool responses."""

    id: str
    description: str
    severity: str
    mode: str
    category: str
    engine_type: str
    language: str
    rationale: str | None = None
    active_violations: int = 0
    baseline_entries: int = 0


class ViolationInfo(BaseModel):
    """Single violation in structured tool responses."""

    file: str
    line: int
    rule_id: str
    severity: str
    description: str
    signature: str | None = None
    mode: str = "block"


class ComplianceResult(BaseModel):
    """Result of validate_architecture_compliance."""

    passed: bool
    message: str
    total_violations: int
    blocking_violations: int
    violations: list[ViolationInfo] = []


class RelevantRulesResult(BaseModel):
    """Result of get_relevant_rules / get_active_context."""

    file_path: str
    total_rules: int
    rules: list[RuleInfo]
    message: str | None = None


class CodeDeltaResult(BaseModel):
    """Result of evaluate_code_delta."""

    passed: bool
    total_violations: int
    violations: list[ViolationInfo] = []


class ServerStatusResult(BaseModel):
    """Result of server_status."""

    version: str
    status: str  # "ready" | "degraded"
    workspace: str
    rules_loaded: int
    tools_count: int
    resources_count: int
    prompts_count: int
    active_violations: int
    plugins_loaded: int


class DependencyGraphResult(BaseModel):
    """Result of get_dependency_graph."""

    node_name: str
    matched_modules: list[str]
    total_dependencies: int
    total_reverse_dependencies: int
    circular_dependency_count: int


class PackInfo(BaseModel):
    """Rule pack metadata for structured responses."""

    name: str
    description: str
    installed: bool = False
    version: str | None = None


class AgentHandoffContext(BaseModel):
    """Governance state summary for agent-to-agent handoff.

    An agent finishing a governance task can pass this context to
    the next agent so it understands the current compliance posture
    without re-scanning the workspace.
    """

    rules_loaded: int
    active_violations: int
    blocking_violations: int
    baselined_entries: int
    top_rules: list[RuleInfo]
    status: str  # "clean" | "violations" | "degraded"
    workspace: str
