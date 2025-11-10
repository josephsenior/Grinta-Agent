import logging

import pytest

from forge.controller.mode_detector import ModeDetector


def test_detect_mode_simple(caplog):
    caplog.set_level(logging.DEBUG)
    request = "Fix a minor typo in README"
    assert ModeDetector.detect_mode(request) == "simple"
    rec = ModeDetector.get_mode_recommendation(request)
    assert rec["mode"] == "simple"
    assert rec["confidence"] == "high"
    assert any("Simple task indicator" in reason for reason in rec["reasons"])


def test_detect_mode_enterprise():
    request = (
        "Design a microservice architecture integrating payment system and compliance auditing "
        "with production release quality gates"
    )
    assert ModeDetector.detect_mode(request) == "enterprise"
    rec = ModeDetector.get_mode_recommendation(request)
    assert rec["mode"] == "enterprise"
    assert rec["complexity_score"] >= 7


def test_detect_mode_ask_user():
    request = "Write docs"
    result = ModeDetector.detect_mode(request)
    assert result == "ask_user"
    assert ModeDetector.detect_mode(request, auto_detect=False) == "ask_user"


