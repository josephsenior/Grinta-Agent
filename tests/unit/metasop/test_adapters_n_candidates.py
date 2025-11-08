from forge.metasop.adapters.engineer_codeact import run_engineer_with_codeact
from forge.metasop.adapters.Forge import run_step_with_Forge
from forge.metasop.models import OrchestrationContext, SopStep


def _dummy_role_profile():
    return {"name": "Engineer", "goal": "Make change", "constraints": []}


class _DummyLLM:

    class Choice:

        def __init__(self, content):

            class Msg:

                def __init__(self, content):
                    self.content = content

            self.message = Msg(content)

    class Response:

        def __init__(self, content, model="dummy-model"):
            self.choices = [_DummyLLM.Choice(content)]
            self.usage = type("U", (), {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2})
            self.model = model

    def __init__(self, responses=None):
        self._responses = responses or ["first", "second", "third"]
        self._idx = 0

    def completion(self, messages=None):
        c = self._responses[self._idx % len(self._responses)]
        self._idx += 1
        return _DummyLLM.Response(c)


class _DummyLLMRegistry:

    def __init__(self, llm):
        self._llm = llm

    def get_active_llm(self):
        return self._llm


def test_FORGE_adapter_honors_n_candidates(monkeypatch, tmp_path):
    step = SopStep(id="s1", role="Engineer", task="do", outputs={"schema": ""})
    ctx = OrchestrationContext(run_id="r1", user_request="u", repo_root=str(tmp_path))
    ctx.extra[f"n_candidates::{step.id}"] = 3
    dummy_llm = _DummyLLM(responses=["a", "b", "c"])

    def dummy_registry_factory(config=None):
        return _DummyLLMRegistry(dummy_llm)

    monkeypatch.setattr("forge.metasop.adapters.forge.LLMRegistry", dummy_registry_factory)
    try:
        monkeypatch.setattr("forge.llm.llm_registry.LLMRegistry", dummy_registry_factory)
    except Exception:
        pass
    monkeypatch.setattr("forge.metasop.adapters.forge.load_schema", lambda s: {})
    res = run_step_with_Forge(
        step, ctx, _dummy_role_profile(), config=None, llm_registry=_DummyLLMRegistry(dummy_llm)
    )
    assert res.ok
    art = res.artifact
    assert isinstance(art.content, dict)
    assert "candidates" in art.content
    assert isinstance(art.content["candidates"], list)
    assert len(art.content["candidates"]) >= 3
    for c in art.content["candidates"]:
        assert isinstance(c, dict)
        meta = c.get("meta", {})
        assert meta.get("source") == "agent"


def test_engineer_codeact_adaptor_respects_candidates(monkeypatch, tmp_path):
    step = SopStep(id="s2", role="Engineer", task="do", outputs={"schema": ""})
    ctx = OrchestrationContext(run_id="r2", user_request="u", repo_root=str(tmp_path))
    ctx.extra[f"n_candidates::{step.id}"] = 2
    summary_path = tmp_path / ".metasop" / "engineer_step.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    parsed = {
        "artifact_path": ".metasop/engineer_step.json",
        "candidates": [{"content": "one", "meta": {}}, {"content": "two", "meta": {}}],
    }
    summary_path.write_text(__import__("json").dumps(parsed), encoding="utf-8")
    monkeypatch.setattr(
        "forge.metasop.adapters.engineer_codeact.call_async_from_sync", lambda func, **kwargs: {"fake": "state"}
    )
    try:
        monkeypatch.setattr(
            "forge.metasop.adapters.engineer_codeact.run_controller", lambda *a, **k: {"fake": "state"}
        )
    except Exception:
        pass
    res = run_engineer_with_codeact(step, ctx, _dummy_role_profile(), config=None)
    assert res.ok
    art = res.artifact
    assert isinstance(art.content, dict)
    assert "candidates" in art.content or "summary" in art.content
    if "candidates" in art.content:
        for c in art.content["candidates"]:
            assert c.get("meta", {}).get("source") == "agent"
