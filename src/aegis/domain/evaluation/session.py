import os
from datetime import datetime

from pydantic import BaseModel


class SessionState(BaseModel):
    last_validation_time: datetime | None = None
    last_agent_id: str | None = None
    active_task: str | None = None
    handoff_notes: str | None = None


class SessionManager:
    def __init__(self, workspace_root: str):
        self.path = os.path.join(workspace_root, ".aegis", "session.json")

    def load(self) -> SessionState:
        if not os.path.exists(self.path):
            return SessionState()
        try:
            with open(self.path, encoding="utf-8") as f:
                return SessionState.model_validate_json(f.read())
        except Exception:
            # Fallback for any corruption, JSON errors, or validation errors
            return SessionState()

    def save(self, state: SessionState):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(state.model_dump_json(indent=2))
