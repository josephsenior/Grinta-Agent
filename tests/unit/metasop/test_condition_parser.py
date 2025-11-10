from __future__ import annotations
import pytest
from forge.metasop.models import Artifact, SopStep, StepOutputSpec
from forge.metasop.orchestrator import MetaSOPOrchestrator


class DummyConfig:

    class extended:
        metasop = {"enabled": False}


@pytest.fixture
def orch():
    from forge.core.config import ForgeConfig

    cfg = ForgeConfig()
    setattr(cfg, "extended", type("E", (), {"metasop": {"enabled": True}})())
    return MetaSOPOrchestrator("feature_delivery", cfg)


def make_step(cond: str | None):
    return SopStep(id="s", role="Engineer", task="t", outputs=StepOutputSpec(schema="engineer.schema.json"), condition=cond)


def test_condition_true_simple(orch):
    done = {"a": Artifact(step_id="a", role="Engineer", content={"ok": True, "num": 5})}
    step = make_step("a.ok == true")
    decision, warn, parse_err = orch._evaluate_condition(done, step)
    assert decision is True and warn is None and (parse_err is False)


def test_condition_false_value_mismatch(orch):
    done = {"a": Artifact(step_id="a", role="Engineer", content={"ok": False})}
    step = make_step("a.ok == true")
    decision, warn, parse_err = orch._evaluate_condition(done, step)
    assert decision is False and parse_err is False


def test_condition_numeric_comparison(orch):
    done = {"a": Artifact(step_id="a", role="Engineer", content={"count": 10})}
    step = make_step("a.count > 5 and a.count < 20")
    decision, warn, parse_err = orch._evaluate_condition(done, step)
    assert decision is True


def test_condition_missing_artifact(orch):
    done = {}
    step = make_step("a.ok == true")
    decision, warn, parse_err = orch._evaluate_condition(done, step)
    assert decision is False and parse_err is False


def test_condition_parse_error(orch):
    done = {"a": Artifact(step_id="a", role="Engineer", content={"ok": True})}
    step = make_step("a.ok === true")
    decision, warn, parse_err = orch._evaluate_condition(done, step)
    assert decision is False and parse_err is True and (warn is not None)


def test_condition_mixed_clauses_one_fails(orch):
    done = {"a": Artifact(step_id="a", role="Engineer", content={"x": 1, "y": 2})}
    step = make_step("a.x == 1 and a.y == 99")
    decision, warn, parse_err = orch._evaluate_condition(done, step)
    assert decision is False and parse_err is False
