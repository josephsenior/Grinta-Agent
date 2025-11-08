import pytest
from forge.controller.state.control_flags import BudgetControlFlag, IterationControlFlag


def test_iteration_control_flag_reaches_limit_and_increases():
    flag = IterationControlFlag(limit_increase_amount=5, current_value=5, max_value=5)
    assert flag.reached_limit() is True
    assert flag._hit_limit is True
    flag.increase_limit(headless_mode=False)
    assert flag.max_value == 10
    flag._hit_limit = False
    assert flag.reached_limit() is False


def test_iteration_control_flag_does_not_increase_in_headless():
    flag = IterationControlFlag(limit_increase_amount=5, current_value=5, max_value=5)
    assert flag.reached_limit() is True
    assert flag._hit_limit is True
    flag.increase_limit(headless_mode=True)
    assert flag.max_value == 5


def test_iteration_control_flag_step_behavior():
    flag = IterationControlFlag(limit_increase_amount=2, current_value=0, max_value=2)
    flag.step()
    assert flag.current_value == 1
    assert not flag.reached_limit()
    flag.step()
    assert flag.current_value == 2
    assert flag.reached_limit()
    with pytest.raises(RuntimeError, match="Agent reached maximum iteration"):
        flag.step()


def test_budget_control_flag_reaches_limit_and_increases():
    flag = BudgetControlFlag(limit_increase_amount=10.0, current_value=50.0, max_value=50.0)
    assert flag.reached_limit() is True
    assert flag._hit_limit is True
    flag.increase_limit(headless_mode=False)
    assert flag.max_value == 60.0
    flag._hit_limit = False
    flag.current_value = 55.0
    assert flag.reached_limit() is False


def test_budget_control_flag_does_not_increase_if_not_hit_limit():
    flag = BudgetControlFlag(limit_increase_amount=10.0, current_value=40.0, max_value=50.0)
    assert flag.reached_limit() is False
    assert flag._hit_limit is False
    old_max_value = flag.max_value
    flag.increase_limit(headless_mode=False)
    assert flag.max_value == old_max_value


def test_budget_control_flag_does_not_increase_in_headless():
    flag = BudgetControlFlag(limit_increase_amount=10.0, current_value=50.0, max_value=50.0)
    assert flag.reached_limit() is True
    assert flag._hit_limit is True
    flag.increase_limit(headless_mode=True)
    assert flag.max_value == 60.0


def test_budget_control_flag_step_raises_on_limit():
    flag = BudgetControlFlag(limit_increase_amount=5.0, current_value=55.0, max_value=50.0)
    with pytest.raises(RuntimeError, match="Agent reached maximum budget"):
        flag.step()
    flag.max_value = 60.0
    flag._hit_limit = False
    flag.step()


def test_budget_control_flag_hit_limit_resets_after_increase():
    flag = BudgetControlFlag(limit_increase_amount=10.0, current_value=50.0, max_value=50.0)
    assert flag.reached_limit() is True
    assert flag._hit_limit is True
    flag.increase_limit(headless_mode=False)
    assert flag._hit_limit is False
    assert flag.reached_limit() is False
    flag.current_value = flag.max_value + 1.0
    assert flag.reached_limit() is True
