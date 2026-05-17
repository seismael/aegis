import os
from typing import List, Dict, Any
import structlog
from aegis.domain.evaluation.ports import ASTAnalyzerInterface, ASTViolation, DiffProviderInterface
from aegis.core.models.governance import Rule

logger = structlog.get_logger()

class EvaluationService:
    """
    Coordinates architectural analysis across the workspace.
    Supports both full sweeps and token-efficient diff-based analysis.
    """

    def __init__(
        self, 
        analyzer: ASTAnalyzerInterface,
        diff_provider: DiffProviderInterface
    ):
        self.analyzer = analyzer
        self.diff_provider = diff_provider

    def evaluate_workspace(self, root_dir: str, rules: List[Rule]) -> List[ASTViolation]:
        """
        Performs a full architectural sweep of the workspace.
        """
        all_violations = []
        
        for root, _, files in os.walk(root_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Skip known noise directories
                if any(x in file_path for x in [".venv", "node_modules", ".git", ".aegis"]):
                    continue
                    
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    violations = self.analyzer.analyze_file(file_path, content, rules)
                    all_violations.extend(violations)
                except (UnicodeDecodeError, PermissionError):
                    continue
                    
        return all_violations

    def evaluate_changes(self, rules: List[Rule]) -> List[ASTViolation]:
        """
        Performs a token-efficient analysis of only the changed lines in changed files.
        """
        diff = self.diff_provider.get_staged_changes()
        all_violations = []
        
        for file_path in diff.changed_files:
            try:
                full_path = os.path.join(self.diff_provider.repo.working_dir, file_path) if hasattr(self.diff_provider, 'repo') and self.diff_provider.repo else file_path
                
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                violations = self.analyzer.analyze_file(file_path, content, rules)
                
                # Filter violations to only those affecting modified lines
                modified_lines = diff.get_modified_lines(file_path)
                if modified_lines:
                    violations = [v for v in violations if v.line in modified_lines]
                    
                all_violations.extend(violations)
            except Exception as e:
                logger.error("Failed to analyze changed file", file=file_path, error=str(e))
                
        return all_violations
