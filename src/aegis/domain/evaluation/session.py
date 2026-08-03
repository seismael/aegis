"""
Persistent Multi-Agent Handover Store.
Manages disk metadata (.aegis/session.json) for cross-agent coordination (e.g. Aider -> Gemini).
"""

import os
from datetime import datetime

from pydantic import BaseModel


class AgentHandoverState(BaseModel):
    last_validation_time: datetime | None = None
    last_agent_id: str | None = None
    active_task: str | None = None
    handoff_notes: str | None = None


class AgentHandoverStore:
    """Manages persistent multi-agent handover metadata stored in .aegis/session.json."""

    def __init__(self, workspace_root: str):
        self.path = os.path.join(workspace_root, ".aegis", "session.json")

    def load(self) -> AgentHandoverState:
        if not os.path.exists(self.path):
            return AgentHandoverState()
        try:
            with open(self.path, encoding="utf-8") as f:
                return AgentHandoverState.model_validate_json(f.read())
        except Exception:
            return AgentHandoverState()

    def save(self, state: AgentHandoverState):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(state.model_dump_json(indent=2))


# Backward compatibility aliases
SessionState = AgentHandoverState
SessionManager = AgentHandoverStore

__all__ = [
    "AgentHandoverState",
    "AgentHandoverStore",
    "SessionState",
    "SessionManager",
]
