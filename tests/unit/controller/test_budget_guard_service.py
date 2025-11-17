from __future__ import annotations

from unittest.mock import MagicMock

from forge.controller.services.controller_context import ControllerContext
from forge.controller.services.budget_guard_service import BudgetGuardService


def test_budget_guard_syncs_with_metrics():
    controller = MagicMock()
    controller.state_tracker.sync_budget_flag_with_metrics = MagicMock()
    context = ControllerContext(controller)
    service = BudgetGuardService(context)

    service.sync_with_metrics()

    controller.state_tracker.sync_budget_flag_with_metrics.assert_called_once()


def test_budget_guard_handles_missing_tracker():
    controller = MagicMock()
    controller.state_tracker = None
    context = ControllerContext(controller)
    service = BudgetGuardService(context)

    service.sync_with_metrics()  # should not raise
    # No calls expected
    assert True

