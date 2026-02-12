from enum import Enum
from typing import Any

class RiskCategory(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class CommandAnalyzer:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def analyze(self, command: str) -> tuple[RiskCategory, str, list[str]]:
        return RiskCategory.LOW, "safe", []
