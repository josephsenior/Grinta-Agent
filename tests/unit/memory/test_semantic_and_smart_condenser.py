import json
from types import SimpleNamespace
from unittest.mock import MagicMock

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


def test_semantic_condenser_scores_action_keywords():
    from forge.events.action import Action

    condenser = ConcreteSemanticCondenser()

    class DummyAction(Action):
        def __init__(self):
            super().__init__()
            self.action = "Finish delegate file write"
            self.command = "install dependencies"

    event = make_event(DummyAction(), 99)
    score, reasons = condenser._score_action_event(event)
    assert score == pytest.approx(1.5)
    assert {"file_operation", "delegation", "completion", "setup_command"} <= set(reasons)


def test_semantic_condenser_scores_observation_details():
    from forge.events.observation.observation import Observation

    condenser = ConcreteSemanticCondenser()

    class DummyObservation(Observation):
        def __init__(self):
            super().__init__(content="X" * 1200)
            self.error = "failure"
            self.exit_code = 0

    event = make_event(DummyObservation(), 100)
    score, reasons = condenser._score_observation_event(event)
    assert score >= 0.8
    assert {"error", "success", "detailed_output"} <= set(reasons)


def test_semantic_condenser_scores_message_event():
    from forge.events.action.message import MessageAction

    condenser = ConcreteSemanticCondenser()

    class DummyMessage(MessageAction):
        @property
        def source(self):
            return "user"

    message = make_event(DummyMessage(content="Does this work?"), 101, source="user")
    score, reasons = condenser._score_message_event(message)
    assert score >= 0.7
    assert {"user_message", "question"} <= set(reasons)


def test_semantic_condenser_select_events_respects_max_size():
    from forge.events.event import Event
    from forge.memory.condenser.impl.semantic_condenser import EventImportance

    condenser = ConcreteSemanticCondenser(max_size=3, keep_first=1, importance_threshold=0.4)
    scored = []
    for idx in range(8):
        event = make_event(Event(), idx)
        scored.append(EventImportance(event=event, importance_score=1.0 - idx * 0.05, reasons=["importance"]))
    keep_ids = condenser._select_events_to_keep(scored)
    assert len(keep_ids) <= 3


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


def test_smart_condenser_returns_empty_when_below_keep_first():
    from forge.events.action import Action
    from forge.memory.condenser.impl.smart_condenser import SmartCondenser

    class TinyAction(Action):
        pass

    condenser = SmartCondenser(llm=None, keep_first=3, max_size=5)
    events = [make_event(TinyAction(), idx) for idx in range(2)]
    condensation = condenser.get_condensation(build_view(events))
    assert condensation.action.forgotten_event_ids == []


def test_smart_condenser_heuristic_scoring_covers_branches():
    from forge.events.action import Action
    from forge.events.action.message import MessageAction
    from forge.events.observation.error import ErrorObservation
    from forge.events.observation.observation import Observation
    from forge.memory.condenser.impl.smart_condenser import SmartCondenser

    class RunnableAction(Action):
        runnable = True

    class LongObservation(Observation):
        def __init__(self):
            super().__init__(content="X" * 600)

    class UserMessage(MessageAction):
        @property
        def source(self):
            return "user"

    user_message = make_event(UserMessage(content="user input"), 1, source="user")
    error_obs = make_event(ErrorObservation("fatal crash occurred"), 2)
    action = make_event(RunnableAction(), 3)
    observation = make_event(LongObservation(), 4)

    condenser = SmartCondenser(llm=None)
    scored = condenser._heuristic_scoring([user_message, error_obs, action, observation])
    assert scored[user_message.id] == 0.9
    assert scored[error_obs.id] == 0.8
    assert scored[action.id] == 0.7
    assert scored[observation.id] == 0.6


def test_smart_condenser_parse_llm_scores_handles_markdown():
    from forge.events.action.message import MessageAction
    from forge.memory.condenser.impl.smart_condenser import SmartCondenser

    condenser = SmartCondenser(llm=None)
    events = [make_event(MessageAction(content=f"Event {i}"), i) for i in range(2)]
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="```json\n[0.5, 0.2]\n```")
            )
        ]
    )
    scores = condenser._parse_llm_scores(response, events)
    assert scores[events[0].id] == 0.5
    assert scores[events[1].id] == 0.2


def test_smart_condenser_parse_llm_scores_fallback_on_error(monkeypatch):
    from forge.events.action.message import MessageAction
    from forge.memory.condenser.impl.smart_condenser import SmartCondenser

    condenser = SmartCondenser(llm=None)
    events = [make_event(MessageAction(content=f"Event {i}"), i) for i in range(2)]
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))])
    scores = condenser._parse_llm_scores(response, events)
    assert all(0.0 <= value <= 1.0 for value in scores.values())


def test_smart_condenser_preserves_action_observation_pairs():
    from forge.events.action import Action
    from forge.events.observation.observation import Observation
    from forge.memory.condenser.impl.smart_condenser import SmartCondenser

    class DummyAction(Action):
        pass

    class DummyObservation(Observation):
        def __init__(self, cause):
            super().__init__(content="obs")
            self._cause = cause

    action = make_event(DummyAction(), 10)
    observation = make_event(DummyObservation(cause=action.id), 11)
    events = [action, observation]
    condenser = SmartCondenser(llm=None, recency_bonus_window=1, importance_threshold=0.1, max_size=2, keep_first=0)
    keep = condenser._preserve_action_observation_pairs(events, {action.id})
    assert action.id in keep and observation.id in keep


def test_smart_condenser_from_config_uses_registry(monkeypatch):
    from forge.core.config.condenser_config import SmartCondenserConfig
    from forge.memory.condenser.impl.smart_condenser import SmartCondenser

    registry = MagicMock()
    stub_llm = DummyLLM()
    registry.get_llm_config.return_value = stub_llm

    config = SmartCondenserConfig(llm_config="llm-name", max_size=5, keep_first=1)
    condenser = SmartCondenser.from_config(config, registry)
    registry.get_llm_config.assert_called_once_with("llm-name")
    assert condenser.llm is stub_llm

