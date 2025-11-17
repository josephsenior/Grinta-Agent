"""Registry mapping security analyzer keys to their implementations."""

from forge.security.analyzer import SecurityAnalyzer
from forge.security.invariant.analyzer import InvariantAnalyzer
from forge.security.llm.analyzer import LLMRiskAnalyzer

SecurityAnalyzers: dict[str, type[SecurityAnalyzer]] = {
    "invariant": InvariantAnalyzer,
    "llm": LLMRiskAnalyzer,
}
