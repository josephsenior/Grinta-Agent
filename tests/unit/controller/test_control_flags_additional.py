from __future__ import annotations

import pytest

from forge.controller.state.control_flags import BudgetControlFlag, IterationControlFlag


def test_iteration_control_flag_step_increments_until_limit():
    flag = IterationControlFlag(limit_increase_amount=5, current_value=0, max_value=2)
    flag.step()
    assert flag.current_value == 1
    flag.step()
    assert flag.current_value == 2
    with pytest.raises(RuntimeError):
        flag.step()


def test_iteration_control_flag_increase_limit_resets_hit_flag():
    flag = IterationControlFlag(limit_increase_amount=3, current_value=3, max_value=3)
    assert flag.reached_limit()
    flag.increase_limit(headless_mode=True)
    assert flag.max_value == 3  # no change in headless mode
    flag.increase_limit(headless_mode=False)
    assert flag.max_value == 6
    assert not flag._hit_limit


def test_budget_control_flag_step_and_increase():
    flag = BudgetControlFlag(
        limit_increase_amount=10.0, current_value=5.0, max_value=5.0
    )
    assert flag.reached_limit()
    with pytest.raises(RuntimeError):
        flag.step()
    flag.increase_limit(headless_mode=False)
    assert flag.max_value == 15.0
    assert not flag.reached_limit()
    flag.current_value = 16.0
    with pytest.raises(RuntimeError):
        flag.step()
