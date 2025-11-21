"""Additional tests for forge.controller.mode_detector."""

from __future__ import annotations

from forge.controller.mode_detector import ModeDetector


def test_detect_mode_simple_task():
    """Short, simple tasks should return simple mode."""
    assert ModeDetector.detect_mode("Fix a typo in README") == "simple"


def test_detect_mode_enterprise_task():
    """Complex feature requests should return enterprise mode."""
    request = (
        "Design a new microservice architecture integrating payments, inventory, and compliance checks "
        "for production deployment"
    )
    assert ModeDetector.detect_mode(request) == "enterprise"


def test_detect_mode_auto_detect_disabled():
    """When auto detection is disabled the detector should defer to the user."""
    assert ModeDetector.detect_mode("Any task", auto_detect=False) == "ask_user"


def test_get_mode_recommendation_contains_reasons():
    """Mode recommendation should include rationale for the decision."""
    request = "Implement enterprise security audit system with compliance checks"
    recommendation = ModeDetector.get_mode_recommendation(request)
    assert recommendation["mode"] in {"enterprise", "ask_user", "simple"}
    assert "complexity_score" in recommendation
    assert recommendation["reasons"]
