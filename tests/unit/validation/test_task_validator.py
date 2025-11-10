import json
from types import SimpleNamespace
from typing import List

import pytest

from forge.events.action.commands import CmdRunAction
from forge.events.observation.commands import CmdOutputObservation
from forge.validation import TaskValidator  # ensure __init__ coverage
from forge.validation.task_validator import (
    CompositeValidator,
    FileExistsValidator,
    GitDiffValidator,
    LLMTaskEvaluator,
    Task,
    TaskValidator as TaskValidatorAlias,
    TestPassingValidator,
    ValidationResult,
)


class DummyState:
    def __init__(self, history: List = None):
        self.history = history or []


@pytest.mark.asyncio
async def test_test_passing_validator_detects_absence_of_tests():
    validator = TestPassingValidator()
    task = Task(description="Ensure tests are run")
    state = DummyState([])

    result = await validator.validate_completion(task, state)

    assert not result.passed
    assert "test execution" in result.reason.lower()
    assert "Run test suite" in " ".join(result.missing_items)


@pytest.mark.asyncio
async def test_test_passing_validator_detects_failed_tests():
    validator = TestPassingValidator()
    task = Task(description="Run tests")
    history = [
        CmdRunAction(command="pytest --maxfail=1"),
        CmdOutputObservation(command="pytest --maxfail=1", content="failures", exit_code=1),
    ]
    state = DummyState(history)

    result = await validator.validate_completion(task, state)

    assert not result.passed
    assert "exit code" in result.reason.lower()
    assert "fix" in " ".join(result.suggestions).lower()


@pytest.mark.asyncio
async def test_test_passing_validator_passes_on_successful_tests():
    validator = TestPassingValidator()
    task = Task(description="Run tests successfully")
    history = [
        CmdRunAction(command="npm test -- --watch=false"),
        CmdOutputObservation(command="npm test -- --watch=false", content="all good", exit_code=0),
    ]
    state = DummyState(history)

    result = await validator.validate_completion(task, state)

    assert result.passed
    assert result.reason == "Tests are passing"


@pytest.mark.asyncio
async def test_git_diff_validator_requires_changes():
    validator = GitDiffValidator()
    task = Task(description="Make code changes")
    state = DummyState([])

    result = await validator.validate_completion(task, state)

    assert not result.passed
    assert "No git changes" in result.reason


@pytest.mark.asyncio
async def test_git_diff_validator_rejects_small_diff():
    validator = GitDiffValidator()
    task = Task(description="Implement feature")
    diff_content = """diff --git a/file.py b/file.py
+++ b/file.py
--- a/file.py
+pass
"""
    history = [
        CmdRunAction(command="git diff"),
        CmdOutputObservation(command="git diff", content=diff_content, exit_code=0),
    ]
    state = DummyState(history)

    result = await validator.validate_completion(task, state)

    assert not result.passed
    assert "meaningful changes detected" in result.reason.lower()


@pytest.mark.asyncio
async def test_git_diff_validator_passes_with_meaningful_changes():
    validator = GitDiffValidator()
    task = Task(description="Implement feature")
    diff_content = """diff --git a/app.py b/app.py
+++ b/app.py
--- a/app.py
+print("hello world")
+result = 1 + 2
-old_value = 0
+return result
+value = compute()
+print(value)
+# comment that should be ignored
"""
    history = [
        CmdRunAction(command="git diff"),
        CmdOutputObservation(command="git diff", content=diff_content, exit_code=0),
    ]
    state = DummyState(history)

    result = await validator.validate_completion(task, state)

    assert result.passed
    assert "Meaningful changes detected" in result.reason


@pytest.mark.asyncio
async def test_file_exists_validator_passes_when_no_expectations():
    validator = FileExistsValidator()
    task = Task(description="No files mentioned")
    state = DummyState([])

    result = await validator.validate_completion(task, state)

    assert result.passed
    assert result.reason == "No expected files specified"


@pytest.mark.asyncio
async def test_file_exists_validator_reports_missing_files():
    validator = FileExistsValidator(expected_files=["output.txt"])
    task = Task(description="Generate output file")
    state = DummyState([])

    result = await validator.validate_completion(task, state)

    assert not result.passed
    assert "output.txt" in "".join(result.missing_items)


@pytest.mark.asyncio
async def test_file_exists_validator_extracts_files_from_description():
    description = 'Please create file "result.txt" and save output to "result.txt".'
    validator = FileExistsValidator()
    task = Task(description=description)
    history = [
        CmdRunAction(command="cat result.txt"),
        CmdOutputObservation(command="cat result.txt", content="42", exit_code=0),
    ]
    state = DummyState(history)

    result = await validator.validate_completion(task, state)

    assert result.passed
    assert validator.expected_files == ["result.txt"]


class FakeLLM:
    def __init__(self, response=None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.calls = []

    async def completion(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._response


@pytest.mark.asyncio
async def test_llm_task_evaluator_skips_without_llm():
    evaluator = LLMTaskEvaluator()
    task = Task(description="Evaluate task")
    state = DummyState([])

    result = await evaluator.validate_completion(task, state)

    assert result.passed
    assert result.reason == "LLM evaluation not configured"


@pytest.mark.asyncio
async def test_llm_task_evaluator_parses_response():
    response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(
                        {
                            "completed": True,
                            "reason": "All requirements satisfied",
                            "confidence": 0.95,
                            "missing_items": [],
                        },
                    ),
                ),
            ),
        ],
    )
    llm = FakeLLM(response=response)
    evaluator = LLMTaskEvaluator(llm=llm)
    task = Task(description="Summary", requirements=["Req1"])
    history = [
        CmdRunAction(command="pytest"),
        CmdRunAction(command="git status"),
    ]
    state = DummyState(history)

    result = await evaluator.validate_completion(task, state)

    assert result.passed
    assert result.reason == "All requirements satisfied"
    assert llm.calls
    prompt = llm.calls[0]["messages"][0]["content"]
    assert "TASK: Summary" in prompt
    assert "- Req1" in prompt


@pytest.mark.asyncio
async def test_llm_task_evaluator_handles_parse_failure():
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))],
    )
    llm = FakeLLM(response=response)
    evaluator = LLMTaskEvaluator(llm=llm)
    task = Task(description="Task with failure")
    state = DummyState([])

    result = await evaluator.validate_completion(task, state)

    assert result.passed
    assert result.reason == "Could not parse LLM response"


@pytest.mark.asyncio
async def test_llm_task_evaluator_handles_llm_exception():
    llm = FakeLLM(error=RuntimeError("boom"))
    evaluator = LLMTaskEvaluator(llm=llm)
    task = Task(description="Task causing exception")
    state = DummyState([])

    result = await evaluator.validate_completion(task, state)

    assert result.passed
    assert result.reason == "LLM evaluation failed"


class StubValidator(TaskValidatorAlias):
    def __init__(self, result: ValidationResult | None = None, should_raise: bool = False):
        self._result = result
        self._should_raise = should_raise

    async def validate_completion(self, task: Task, state: DummyState) -> ValidationResult:
        if self._should_raise:
            raise RuntimeError("validator failure")
        return self._result


def test_validation_module_exports_task_validator():
    assert TaskValidator is TaskValidatorAlias


@pytest.mark.asyncio
async def test_composite_validator_all_must_pass_failure():
    validators = [
        StubValidator(ValidationResult(passed=True, reason="ok", confidence=0.9)),
        StubValidator(
            ValidationResult(
                passed=False,
                reason="fail",
                confidence=0.6,
                missing_items=["fix tests"],
                suggestions=["run pytest"],
            ),
        ),
    ]
    composite = CompositeValidator(validators, require_all_pass=True)
    result = await composite.validate_completion(Task(description=""), DummyState([]))

    assert not result.passed
    assert "1 validator(s) failed" in result.reason
    assert "fix tests" in result.missing_items


@pytest.mark.asyncio
async def test_composite_validator_all_must_pass_success():
    validators = [
        StubValidator(ValidationResult(passed=True, reason="first", confidence=0.8)),
        StubValidator(ValidationResult(passed=True, reason="second", confidence=0.85)),
    ]
    composite = CompositeValidator(validators, require_all_pass=True)
    result = await composite.validate_completion(Task(description=""), DummyState([]))

    assert result.passed
    assert "All validators passed" in result.reason
    assert result.confidence == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_composite_validator_weighted_vote_success():
    validators = [
        StubValidator(ValidationResult(passed=True, reason="v1", confidence=0.9)),
        StubValidator(ValidationResult(passed=True, reason="v2", confidence=0.8)),
    ]
    composite = CompositeValidator(validators, min_confidence=0.7)
    result = await composite.validate_completion(Task(description=""), DummyState([]))

    assert result.passed
    assert result.confidence == pytest.approx(0.85)


@pytest.mark.asyncio
async def test_composite_validator_weighted_vote_failure():
    validators = [
        StubValidator(ValidationResult(passed=True, reason="v1", confidence=0.6)),
        StubValidator(
            ValidationResult(
                passed=False,
                reason="v2",
                confidence=0.4,
                missing_items=["update docs"],
                suggestions=["add docs"],
            ),
        ),
    ]
    composite = CompositeValidator(validators, min_confidence=0.7)
    result = await composite.validate_completion(Task(description=""), DummyState([]))

    assert not result.passed
    assert "Task validation insufficient" in result.reason
    assert "update docs" in result.missing_items


@pytest.mark.asyncio
async def test_composite_validator_handles_validator_exceptions():
    validators = [StubValidator(should_raise=True)]
    composite = CompositeValidator(validators)
    result = await composite.validate_completion(Task(description=""), DummyState([]))

    assert result.passed
    assert result.reason == "No validators ran successfully"
    assert result.confidence == 0.0


