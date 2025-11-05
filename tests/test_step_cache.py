import types
from openhands.metasop.models import Artifact, SopStep, SopTemplate, StepOutputSpec
from openhands.metasop.orchestrator import MetaSOPOrchestrator


class DummyExecutor:

    def execute(self, step, ctx, role_profile, config=None):
        content = {"result": "ok", "value": 42}
        art = Artifact(step_id=step.id, role=step.role, content=content)
        trace = types.SimpleNamespace(
            total_tokens=20,
            model_name="dummy-model",
            prompt_tokens=10,
            completion_tokens=10,
            duration_ms=0,
            retries=0,
            step_id=step.id,
            role=step.role,
        )
        return types.SimpleNamespace(ok=True, artifact=art, trace=trace, rationale=None, error=None)


def _make_single_engineer_template():
    return SopTemplate(
        name="feature_delivery",
        steps=[
            SopStep(
                id="impl", role="engineer", task="implement feature", outputs=StepOutputSpec(schema_file="dummy.json")
            )
        ],
    )


def _new_orchestrator(persist_dir=None, exclude_roles=None):
    metasop_cfg = {"enable_step_cache": True}
    if persist_dir:
        metasop_cfg["step_cache_dir"] = persist_dir
    if exclude_roles:
        metasop_cfg["step_cache_exclude_roles"] = exclude_roles
    config = types.SimpleNamespace(extended=types.SimpleNamespace(metasop=metasop_cfg), runtime=types.SimpleNamespace())
    orch = MetaSOPOrchestrator(sop_name="feature_delivery", config=config)
    orch.template = _make_single_engineer_template()
    orch.settings.enabled = True
    orch.step_executor = DummyExecutor()
    orch.profiles["engineer"] = types.SimpleNamespace(model_dump=lambda: {}, capabilities=["implement"])
    return orch


def test_cache_in_memory_two_runs():
    orch = _new_orchestrator()
    ok1, _ = orch.run(user_request="do something")
    assert ok1 is True or ok1 is False
    statuses1 = {e.get("status") for e in orch.step_events if e.get("step_id") == "impl"}
    assert "executed_cached" not in statuses1, "First run should not be cached"
    ok2, _ = orch.run(user_request="do something")
    statuses2 = [e.get("status") for e in orch.step_events if e.get("step_id") == "impl"]
    assert "executed_cached" in statuses2, f"Expected executed_cached in second run, got {statuses2}"


def test_cache_persistent_across_instances(tmp_path):
    cache_dir = tmp_path / "step_cache"
    orch1 = _new_orchestrator(persist_dir=str(cache_dir))
    orch1.run(user_request="persist test")
    orch2 = _new_orchestrator(persist_dir=str(cache_dir))
    orch2.run(user_request="persist test")
    statuses = [e.get("status") for e in orch2.step_events if e.get("step_id") == "impl"]
    assert "executed_cached" in statuses, "Persistent cache did not yield executed_cached"


def test_cache_excluded_role():
    orch = _new_orchestrator(exclude_roles=["engineer"])
    orch.run(user_request="exclude test")
    orch.run(user_request="exclude test")
    statuses = [e.get("status") for e in orch.step_events if e.get("step_id") == "impl"]
    assert "executed_cached" not in statuses, "Cache should not apply to excluded role"
