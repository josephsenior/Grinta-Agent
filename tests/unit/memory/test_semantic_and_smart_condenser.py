import json
from types import SimpleNamespace

import pytest

from forge.memory.condenser.impl.semantic_condenser import SemanticCondenser

import forge.events.action.message as message_module
from forge.events.action.agent import CondensationAction as AgentCondensationAction

setattr(message_module, "CondensationAction", AgentCondensationAction)


def make_event(event, event_id, source="agent"):
    event._id = event_id
    event._source = source
    return event


def build_view(events):
    from forge.memory.view import View

    return View(events=events)


class ConcreteSemanticCondenser(SemanticCondenser):
    def should_condense(self, view):
        return True


def test_semantic_condenser_basic_flow():
    from forge.events.action.message import MessageAction
    from forge.events.observation.observation import Observation
    from forge.memory.condenser.impl.semantic_condenser import SemanticCondenser

    events = []
    for idx in range(8):
        if idx % 3 == 0:
            event = make_event(MessageAction(content=f"Question {idx}", wait_for_response=False), idx, source="user")
        else:
            event = make_event(Observation(content=f"Observation {idx}"), idx)
        events.append(event)

    condenser = ConcreteSemanticCondenser(keep_first=2, max_size=4, importance_threshold=0.2)
    condensation = condenser.get_condensation(build_view(events))
    assert condensation.action is not None


def test_semantic_condenser_importance_scoring():
    from forge.events.action.message import MessageAction
    from forge.events.observation.observation import Observation
    from forge.memory.condenser.impl.semantic_condenser import SemanticCondenser
    from forge.events.action import MessageAction as BaseMessageAction

    condenser = ConcreteSemanticCondenser()
    action = make_event(MessageAction(content="User question?"), 1, source="user")
    observation = make_event(Observation(content="Error output"), 2)
    observation.error = True
    score_action, reasons_action = condenser._calculate_importance(action)
    score_obs, reasons_obs = condenser._calculate_importance(observation)
    assert "normal_importance" in reasons_action
    assert score_obs > 0 and "error" in reasons_obs


def test_semantic_condenser_coherence():
    from forge.events.action.message import MessageAction
    from forge.events.observation.observation import Observation
    from forge.memory.condenser.impl.semantic_condenser import SemanticCondenser

    action = make_event(MessageAction(content="Run command"), 1)
    observation = make_event(Observation(content="Result"), 2)
    observation._cause = 1
    events = [action, observation]
    condenser = ConcreteSemanticCondenser()
    keep_ids = condenser._ensure_coherence(events, {1})
    assert keep_ids == {1, 2}


def test_semantic_condenser_under_limit_returns_empty():
    from forge.events.event import Event

    condenser = ConcreteSemanticCondenser(max_size=10)
    view = build_view([make_event(Event(), i) for i in range(3)])
    condensation = condenser.get_condensation(view)
    assert condensation.action.forgotten_event_ids == []


def test_semantic_condenser_select_top_importance():
    from forge.events.event import Event

    condenser = ConcreteSemanticCondenser(max_size=2, keep_first=0, importance_threshold=0.2)
    scored = [condenser._score_events([make_event(Event(), i)])[0] for i in range(4)]
    for idx, item in enumerate(scored):
        item.importance_score = 1.0 - idx * 0.2
    keep = condenser._select_events_to_keep(scored)
    assert len(keep) == 2


class DummyLLM:
    def __init__(self):
        self.calls = 0
        self.config = SimpleNamespace(model="stub")

    def completion(self, messages, temperature):
        self.calls += 1
        scores = json.dumps([0.9 for _ in messages[0]["content"].splitlines() if "[" in _])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=scores))])


def test_smart_condenser_recency_and_threshold():
    from forge.events.action import Action
    from forge.events.action.message import MessageAction
    from forge.events.observation.error import ErrorObservation
    from forge.memory.condenser.impl.smart_condenser import SmartCondenser

    class DummyAction(Action):
        pass

    events = []
    for idx in range(15):
        if idx == 2:
            event = make_event(ErrorObservation(content="Critical failure"), idx)
        elif idx % 4 == 0:
            event = make_event(MessageAction(content=f"Message {idx}"), idx, source="user")
        else:
            event = make_event(DummyAction(), idx)
        events.append(event)

    condenser = SmartCondenser(llm=None, max_size=5, keep_first=1, importance_threshold=0.7, recency_bonus_window=3)
    view = build_view(events)
    assert condenser.should_condense(view)
    condensation = condenser.get_condensation(view)
    assert condensation.action


def test_smart_condenser_llm_scoring(monkeypatch):
    from forge.events.action.message import MessageAction
    from forge.memory.condenser.impl.smart_condenser import SmartCondenser

    llm = DummyLLM()
    llm.config = SimpleNamespace(model="stub")
    events = [make_event(MessageAction(content=f"Event {i}"), i, source="user") for i in range(10)]
    condenser = SmartCondenser(llm=llm, max_size=3, keep_first=0, importance_threshold=0.8, recency_bonus_window=2)
    condensation = condenser.get_condensation(build_view(events))
    assert llm.calls > 0
    assert condensation.action is not None

