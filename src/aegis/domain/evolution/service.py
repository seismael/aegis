import json
import os
from typing import Optional
from aegis.core.models.evolution import EvolutionLog, EvolutionDecision

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
        log.decisions.append(decision)
        self.save_log(log)

    def load_log(self) -> EvolutionLog:
        if not os.path.exists(self.path):
            return EvolutionLog()
        with open(self.path, "r", encoding="utf-8") as f:
            return EvolutionLog.model_validate_json(f.read())

    def save_log(self, log: EvolutionLog) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(log.model_dump_json(indent=2))
