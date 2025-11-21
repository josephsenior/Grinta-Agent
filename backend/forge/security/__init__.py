"""Security and safety modules for Forge autonomous agents."""


# Use lazy imports to avoid circular dependencies
def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "SecurityAnalyzer":
        from forge.security.analyzer import SecurityAnalyzer

        return SecurityAnalyzer
    if name == "options":
        # Return the options module directly
        import importlib

        return importlib.import_module(".options", package="forge.security")
    if name == "CommandAnalyzer":
        from forge.security.command_analyzer import CommandAnalyzer

        return CommandAnalyzer
    if name == "CommandRiskAssessment":
        from forge.security.command_analyzer import CommandRiskAssessment

        return CommandRiskAssessment
    if name == "RiskCategory":
        from forge.security.command_analyzer import RiskCategory

        return RiskCategory
    if name == "SafetyConfig":
        from forge.security.safety_config import SafetyConfig

        return SafetyConfig
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = [
    "CommandAnalyzer",
    "CommandRiskAssessment",
    "RiskCategory",
    "SafetyConfig",
    "SecurityAnalyzer",
    "options",
]
