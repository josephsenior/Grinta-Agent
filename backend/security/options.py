"""Security analyzer options and registry."""

from backend.security.analyzer import SecurityAnalyzer

# Registry of available security analyzers
# Maps analyzer name to analyzer class
SecurityAnalyzers: dict[str, type[SecurityAnalyzer]] = {
    "default": SecurityAnalyzer,
}
