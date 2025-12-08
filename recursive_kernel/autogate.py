from enum import Enum
from typing import Dict, List

class GateDecision(Enum):
    AUTO_MERGE = "AUTO_MERGE"
    HUMAN_REVIEW = "HUMAN_REVIEW"

class AutoGate:
    def __init__(self, config: Dict):
        self.config = config

    def evaluate(self, changed_files: List[str], diff_lines: int) -> GateDecision:
        max_lines = self.config.get('max_diff_lines_auto_merge', 0)
        risk_rules = self.config.get('risk_rules', {})
        low_risk_paths = risk_rules.get('low_risk_paths', [])

        if diff_lines > max_lines:
            return GateDecision.HUMAN_REVIEW

        # check paths
        all_safe = True
        for f in changed_files:
            # Normalize path separators
            normalized = f.replace('\\', '/')
            if not any(normalized.startswith(p) for p in low_risk_paths):
                all_safe = False
                break
        
        if all_safe:
            return GateDecision.AUTO_MERGE
        return GateDecision.HUMAN_REVIEW
