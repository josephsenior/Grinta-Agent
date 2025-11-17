import pytest

from forge.core import exceptions as exc


def test_agent_no_instruction_error_default_message():
    err = exc.AgentNoInstructionError()
    assert str(err) == "Instruction must be provided"


def test_agent_event_type_error_custom_message():
    err = exc.AgentEventTypeError("Must be dict")
    assert str(err) == "Must be dict"


def test_agent_already_registered_error_messages():
    assert str(exc.AgentAlreadyRegisteredError()) == "Agent class already registered"
    assert (
        str(exc.AgentAlreadyRegisteredError("demo"))
        == "Agent class already registered under 'demo'"
    )


def test_agent_not_registered_error_messages():
    assert str(exc.AgentNotRegisteredError()) == "No agent class registered"
    assert (
        str(exc.AgentNotRegisteredError("demo"))
        == "No agent class registered under 'demo'"
    )


def test_agent_stuck_in_loop_error():
    assert str(exc.AgentStuckInLoopError()) == "Agent got stuck in a loop"


def test_task_invalid_state_error_variants():
    assert str(exc.TaskInvalidStateError()) == "Invalid state"
    assert str(exc.TaskInvalidStateError("RUNNING")) == "Invalid state RUNNING"


def test_llm_malformed_action_error_str():
    err = exc.LLMMalformedActionError("bad response")
    assert str(err) == "bad response"


def test_other_llm_errors_default_messages():
    assert str(exc.LLMNoActionError()) == "Agent must return an action"
    assert str(exc.LLMResponseError()) == "Failed to retrieve action from LLM response"
    assert str(exc.LLMNoResponseError()).startswith("LLM did not return a response")


def test_user_cancelled_and_operation_cancelled_errors():
    assert str(exc.UserCancelledError("Stop")) == "Stop"
    assert str(exc.OperationCancelled()) == "Operation was cancelled"


def test_llm_context_window_exceed_error():
    message = "Conversation history longer than LLM context window limit. Consider turning on enable_history_truncation config to avoid this error"
    assert str(exc.LLMContextWindowExceedError()) == message


def test_function_call_errors():
    assert str(exc.FunctionCallConversionError("convert")) == "convert"
    assert str(exc.FunctionCallValidationError("validate")) == "validate"
    assert str(exc.FunctionCallNotExistsError("missing")) == "missing"


def test_agent_runtime_exceptions_inheritance():
    assert isinstance(exc.AgentRuntimeBuildError(), exc.AgentRuntimeError)
    assert isinstance(exc.AgentRuntimeTimeoutError(), exc.AgentRuntimeError)
    assert isinstance(exc.AgentRuntimeNotReadyError(), exc.AgentRuntimeUnavailableError)
    assert isinstance(
        exc.AgentRuntimeDisconnectedError(), exc.AgentRuntimeUnavailableError
    )
    assert isinstance(exc.AgentRuntimeNotFoundError(), exc.AgentRuntimeUnavailableError)


def test_browser_exceptions_messages():
    assert str(exc.BrowserInitException()) == "Failed to initialize browser environment"
    assert str(exc.BrowserUnavailableException()) == (
        "Browser environment is not available, please check if has been initialized"
    )


def test_microagent_validation_error():
    assert str(exc.MicroagentValidationError()) == "Microagent validation failed"
