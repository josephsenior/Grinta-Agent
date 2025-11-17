from __future__ import annotations

import types
from unittest.mock import AsyncMock, MagicMock

import pytest

from forge.controller.services.confirmation_service import ConfirmationService
from forge.controller.services.controller_context import ControllerContext
from forge.events import EventSource
from forge.events.action import MessageAction, ActionConfirmationStatus
from forge.core.schemas import AgentState


def make_controller():
    controller = types.SimpleNamespace()
    controller.state = types.SimpleNamespace(confirmation_mode=True)
    controller.agent = MagicMock()
    controller.event_stream = MagicMock()
    controller._replay_manager = MagicMock()
    controller._replay_manager.should_replay.return_value = False
    controller._replay_manager.step = MagicMock()
    controller._replay_manager.replay_mode = False
    controller._replay_manager.replay_index = 0
    controller._replay_manager.replay_events = None
    controller.set_agent_state_to = AsyncMock()
    controller.log = MagicMock()
    return controller


@pytest.mark.asyncio
async def test_get_next_action_uses_replay_when_available():
    controller = make_controller()
    controller._replay_manager.should_replay.return_value = True
    replay_action = MessageAction(content="replayed")
    controller._replay_manager.step.return_value = replay_action
    context = ControllerContext(controller)
    service = ConfirmationService(context, MagicMock())

    action = service.get_next_action()

    assert action is replay_action
    controller.agent.step.assert_not_called()


@pytest.mark.asyncio
async def test_get_next_action_falls_back_to_agent():
    controller = make_controller()
    controller._replay_manager.should_replay.return_value = False
    live_action = MessageAction(content="live")
    controller.agent.step.return_value = live_action
    context = ControllerContext(controller)
    service = ConfirmationService(context, MagicMock())

    action = service.get_next_action()

    assert action is live_action
    assert action.source == EventSource.AGENT


@pytest.mark.asyncio
async def test_evaluate_action_runs_safety_pipeline():
    controller = make_controller()
    action = MessageAction(content="check")
    safety_service = types.SimpleNamespace(
        action_requires_confirmation=MagicMock(return_value=True),
        analyze_security=AsyncMock(),
        evaluate_security_risk=MagicMock(return_value=(True, False)),
        apply_confirmation_state=MagicMock(),
    )
    context = ControllerContext(controller)
    service = ConfirmationService(context, safety_service)

    await service.evaluate_action(action)

    safety_service.analyze_security.assert_awaited_with(action)
    safety_service.apply_confirmation_state.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_action_skips_when_disabled():
    controller = make_controller()
    controller.state.confirmation_mode = False
    action = MessageAction(content="skip")
    safety_service = types.SimpleNamespace(
        action_requires_confirmation=MagicMock(),
        analyze_security=AsyncMock(),
        evaluate_security_risk=MagicMock(),
        apply_confirmation_state=MagicMock(),
    )
    context = ControllerContext(controller)
    service = ConfirmationService(context, safety_service)

    await service.evaluate_action(action)

    safety_service.action_requires_confirmation.assert_not_called()


@pytest.mark.asyncio
async def test_handle_pending_confirmation_sets_state():
    controller = make_controller()
    context = ControllerContext(controller)
    service = ConfirmationService(context, MagicMock())
    action = MessageAction(content="pending")
    action.confirmation_state = ActionConfirmationStatus.AWAITING_CONFIRMATION

    transitioned = await service.handle_pending_confirmation(action)

    assert transitioned is True
    controller.set_agent_state_to.assert_awaited_with(
        AgentState.AWAITING_USER_CONFIRMATION
    )


@pytest.mark.asyncio
async def test_handle_pending_confirmation_noop():
    controller = make_controller()
    context = ControllerContext(controller)
    service = ConfirmationService(context, MagicMock())
    action = MessageAction(content="clear")
    action.confirmation_state = ActionConfirmationStatus.CONFIRMED

    transitioned = await service.handle_pending_confirmation(action)

    assert transitioned is False
    controller.set_agent_state_to.assert_not_awaited()


def test_replay_mode_property():
    controller = make_controller()
    controller._replay_manager.replay_mode = True
    context = ControllerContext(controller)
    service = ConfirmationService(context, MagicMock())

    assert service.is_replay_mode is True

    controller._replay_manager.replay_mode = False
    assert service.is_replay_mode is False


def test_replay_progress():
    controller = make_controller()
    controller._replay_manager.replay_mode = True
    controller._replay_manager.replay_events = [MagicMock(), MagicMock(), MagicMock()]
    controller._replay_manager.replay_index = 1
    context = ControllerContext(controller)
    service = ConfirmationService(context, MagicMock())

    progress = service.replay_progress
    assert progress == (1, 3)

    controller._replay_manager.replay_mode = False
    assert service.replay_progress is None


def test_action_counts_tracking():
    controller = make_controller()
    controller.log = MagicMock()
    context = ControllerContext(controller)
    service = ConfirmationService(context, MagicMock())

    # Replay actions
    controller._replay_manager.should_replay.return_value = True
    replay_action = MessageAction(content="replay1")
    replay_action.id = 1
    controller._replay_manager.step.return_value = replay_action
    controller._replay_manager.replay_index = 0

    action1 = service.get_next_action()
    assert action1 is replay_action
    assert service.action_counts["replay_actions"] == 1
    assert service.action_counts["live_actions"] == 0

    # Live actions
    controller._replay_manager.should_replay.return_value = False
    live_action = MessageAction(content="live1")
    controller.agent.step.return_value = live_action

    action2 = service.get_next_action()
    assert action2 is live_action
    assert service.action_counts["replay_actions"] == 1
    assert service.action_counts["live_actions"] == 1

    # More replay
    controller._replay_manager.should_replay.return_value = True
    replay_action2 = MessageAction(content="replay2")
    replay_action2.id = 2
    controller._replay_manager.step.return_value = replay_action2
    controller._replay_manager.replay_index = 1

    action3 = service.get_next_action()
    assert action3 is replay_action2
    assert service.action_counts["replay_actions"] == 2
    assert service.action_counts["live_actions"] == 1

