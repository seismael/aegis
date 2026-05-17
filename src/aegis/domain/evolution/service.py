import json
import os

from aegis.core.models.evolution import EvolutionDecision, EvolutionLog


class EvolutionService:
    """
    Manages the architectural consensus and evolution lifecycle.
    Records decisions and updates the governance state.
    """

    def __init__(self, directory: str = ".aegis"):
        self.path = os.path.join(directory, "evolution_log.json")
        os.makedirs(directory, exist_ok=True)

    def log_decision(self, decision: EvolutionDecision) -> None:
        log = self.load_log()
        # Skip duplicates: same rule_id, action, and rationale
        for existing in log.decisions:
            if (
                existing.rule_id == decision.rule_id
                and existing.action == decision.action
                and existing.rationale == decision.rationale
            ):
                return
        log.decisions.append(decision)
        self.save_log(log)

    def load_log(self) -> EvolutionLog:
        if not os.path.exists(self.path):
            return EvolutionLog()
        try:
            with open(self.path, encoding="utf-8") as f:
                return EvolutionLog.model_validate_json(f.read())
        except (json.JSONDecodeError, ValueError):
            return EvolutionLog()

    def save_log(self, log: EvolutionLog) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(log.model_dump_json(indent=2))
