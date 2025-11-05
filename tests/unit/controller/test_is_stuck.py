import logging
from unittest.mock import Mock, patch
import pytest
from pytest import TempPathFactory
from openhands.controller.agent_controller import AgentController
from openhands.controller.state.state import State
from openhands.controller.stuck import StuckDetector
from openhands.events.action import CmdRunAction, FileReadAction, MessageAction
from openhands.events.action.commands import IPythonRunCellAction
from openhands.events.observation import CmdOutputObservation, FileReadObservation
from openhands.events.observation.agent import AgentCondensationObservation
from openhands.events.observation.commands import IPythonRunCellObservation
from openhands.events.observation.empty import NullObservation
from openhands.events.observation.error import ErrorObservation
from openhands.events.stream import EventSource, EventStream
from openhands.storage import get_file_store


def collect_events(stream):
    return list(stream.get_events())


logging.basicConfig(level=logging.DEBUG)
jupyter_line_1 = "\n[Jupyter current working directory:"
jupyter_line_2 = "\n[Jupyter Python interpreter:"
code_snippet = '\nedit_file_by_replace(\n    \'book_store.py\',\n    to_replace="""def total(basket):\n    if not basket:\n        return 0\n'


@pytest.fixture
def temp_dir(tmp_path_factory: TempPathFactory) -> str:
    return str(tmp_path_factory.mktemp("test_is_stuck"))


@pytest.fixture
def event_stream(temp_dir):
    file_store = get_file_store("local", temp_dir)
    event_stream = EventStream("asdf", file_store)
    yield event_stream
    event_stream.clear()


class TestStuckDetector:

    @pytest.fixture
    def stuck_detector(self):
        state = State(inputs={})
        state.iteration_flag.max_value = 50
        state.history = []
        return StuckDetector(state)

    def _impl_syntax_error_events(self, state: State, error_message: str, random_line: bool, incidents: int = 4):
        for i in range(incidents):
            ipython_action = IPythonRunCellAction(code=code_snippet)
            state.history.append(ipython_action)
            extra_number = (i + 1) * 10 if random_line else "42"
            extra_line = "\n" * (i + 1) if random_line else ""
            ipython_observation = IPythonRunCellObservation(
                content=f'  Cell In[1], line {extra_number}\nto_replace="""def largest(min_factor, max_factor):\n            ^\n{error_message}{extra_line}'
                + jupyter_line_1
                + jupyter_line_2,
                code=code_snippet,
            )
            state.history.append(ipython_observation)

    def _impl_unterminated_string_error_events(self, state: State, random_line: bool, incidents: int = 4):
        for i in range(incidents):
            ipython_action = IPythonRunCellAction(code=code_snippet)
            state.history.append(ipython_action)
            line_number = (i + 1) * 10 if random_line else "1"
            ipython_observation = IPythonRunCellObservation(
                content=f'print("  Cell In[1], line {line_number}\nhello\n       ^\nSyntaxError: unterminated string literal (detected at line {line_number})'
                + jupyter_line_1
                + jupyter_line_2,
                code=code_snippet,
            )
            state.history.append(ipython_observation)

    def test_history_too_short(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        message_action = MessageAction(content="Hello", wait_for_response=False)
        message_action._source = EventSource.USER
        observation = NullObservation(content="")
        state.history.append(message_action)
        state.history.append(observation)
        cmd_action = CmdRunAction(command="ls")
        state.history.append(cmd_action)
        cmd_observation = CmdOutputObservation(command="ls", content="file1.txt\nfile2.txt")
        state.history.append(cmd_observation)
        assert stuck_detector.is_stuck(headless_mode=True) is False

    def test_interactive_mode_resets_after_user_message(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        for i in range(4):
            cmd_action = CmdRunAction(command="ls")
            cmd_action._id = i
            state.history.append(cmd_action)
            cmd_observation = CmdOutputObservation(content="", command="ls", command_id=i)
            cmd_observation._cause = cmd_action._id
            state.history.append(cmd_observation)
        assert stuck_detector.is_stuck(headless_mode=True) is True
        assert stuck_detector.is_stuck(headless_mode=False) is True
        message_action = MessageAction(content="Hello", wait_for_response=False)
        message_action._source = EventSource.USER
        state.history.append(message_action)
        assert stuck_detector.is_stuck(headless_mode=False) is False
        assert stuck_detector.is_stuck(headless_mode=True) is True
        for i in range(2):
            cmd_action = CmdRunAction(command="ls")
            cmd_action._id = i + 4
            state.history.append(cmd_action)
            cmd_observation = CmdOutputObservation(content="", command="ls", command_id=i + 4)
            cmd_observation._cause = cmd_action._id
            state.history.append(cmd_observation)
        assert stuck_detector.is_stuck(headless_mode=False) is False
        for i in range(2):
            cmd_action = CmdRunAction(command="ls")
            cmd_action._id = i + 6
            state.history.append(cmd_action)
            cmd_observation = CmdOutputObservation(content="", command="ls", command_id=i + 6)
            cmd_observation._cause = cmd_action._id
            state.history.append(cmd_observation)
        assert stuck_detector.is_stuck(headless_mode=False) is True

    def test_is_stuck_repeating_action_observation(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        message_action = MessageAction(content="Done", wait_for_response=False)
        message_action._source = EventSource.USER
        hello_action = MessageAction(content="Hello", wait_for_response=False)
        hello_observation = NullObservation("")
        state.history.append(hello_action)
        state.history.append(hello_observation)
        cmd_action_1 = CmdRunAction(command="ls")
        cmd_action_1._id = 1
        state.history.append(cmd_action_1)
        cmd_observation_1 = CmdOutputObservation(content="", command="ls")
        cmd_observation_1._cause = cmd_action_1._id
        state.history.append(cmd_observation_1)
        cmd_action_2 = CmdRunAction(command="ls")
        cmd_action_2._id = 2
        state.history.append(cmd_action_2)
        cmd_observation_2 = CmdOutputObservation(content="", command="ls")
        cmd_observation_2._cause = cmd_action_2._id
        state.history.append(cmd_observation_2)
        message_null_observation = NullObservation(content="")
        state.history.append(message_action)
        state.history.append(message_null_observation)
        assert stuck_detector.is_stuck(headless_mode=True) is False
        cmd_action_3 = CmdRunAction(command="ls")
        cmd_action_3._id = 3
        state.history.append(cmd_action_3)
        cmd_observation_3 = CmdOutputObservation(content="", command="ls")
        cmd_observation_3._cause = cmd_action_3._id
        state.history.append(cmd_observation_3)
        assert len(state.history) == 10
        assert stuck_detector.is_stuck(headless_mode=True) is False
        cmd_action_4 = CmdRunAction(command="ls")
        cmd_action_4._id = 4
        state.history.append(cmd_action_4)
        cmd_observation_4 = CmdOutputObservation(content="", command="ls")
        cmd_observation_4._cause = cmd_action_4._id
        state.history.append(cmd_observation_4)
        assert len(state.history) == 12
        with patch("logging.Logger.warning") as mock_warning:
            assert stuck_detector.is_stuck(headless_mode=True) is True
            mock_warning.assert_called_once_with("Action, Observation loop detected")

    def test_is_stuck_repeating_action_error(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        message_action = MessageAction(content="Done", wait_for_response=False)
        message_action._source = EventSource.USER
        hello_action = MessageAction(content="Hello", wait_for_response=False)
        hello_observation = NullObservation(content="")
        state.history.append(hello_action)
        state.history.append(hello_observation)
        cmd_action_1 = CmdRunAction(command="invalid_command")
        state.history.append(cmd_action_1)
        error_observation_1 = ErrorObservation(content="Command not found")
        state.history.append(error_observation_1)
        cmd_action_2 = CmdRunAction(command="invalid_command")
        state.history.append(cmd_action_2)
        error_observation_2 = ErrorObservation(content="Command still not found or another error")
        state.history.append(error_observation_2)
        message_null_observation = NullObservation(content="")
        state.history.append(message_action)
        state.history.append(message_null_observation)
        cmd_action_3 = CmdRunAction(command="invalid_command")
        state.history.append(cmd_action_3)
        error_observation_3 = ErrorObservation(content="Different error")
        state.history.append(error_observation_3)
        cmd_action_4 = CmdRunAction(command="invalid_command")
        state.history.append(cmd_action_4)
        error_observation_4 = ErrorObservation(content="Command not found")
        state.history.append(error_observation_4)
        with patch("logging.Logger.warning") as mock_warning:
            assert stuck_detector.is_stuck(headless_mode=True) is True
            mock_warning.assert_called_once_with("Action, ErrorObservation loop detected")

    def test_is_stuck_invalid_syntax_error(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        self._impl_syntax_error_events(
            state, error_message="SyntaxError: invalid syntax. Perhaps you forgot a comma?", random_line=False
        )
        with patch("logging.Logger.warning"):
            assert stuck_detector.is_stuck(headless_mode=True) is True

    def test_is_not_stuck_invalid_syntax_error_random_lines(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        self._impl_syntax_error_events(
            state, error_message="SyntaxError: invalid syntax. Perhaps you forgot a comma?", random_line=True
        )
        with patch("logging.Logger.warning"):
            assert stuck_detector.is_stuck(headless_mode=True) is False

    def test_is_not_stuck_invalid_syntax_error_only_three_incidents(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        self._impl_syntax_error_events(
            state,
            error_message="SyntaxError: invalid syntax. Perhaps you forgot a comma?",
            random_line=True,
            incidents=3,
        )
        with patch("logging.Logger.warning"):
            assert stuck_detector.is_stuck(headless_mode=True) is False

    def test_is_stuck_incomplete_input_error(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        self._impl_syntax_error_events(state, error_message="SyntaxError: incomplete input", random_line=False)
        with patch("logging.Logger.warning"):
            assert stuck_detector.is_stuck(headless_mode=True) is True

    def test_is_not_stuck_incomplete_input_error(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        self._impl_syntax_error_events(state, error_message="SyntaxError: incomplete input", random_line=True)
        with patch("logging.Logger.warning"):
            assert stuck_detector.is_stuck(headless_mode=True) is False

    def test_is_not_stuck_ipython_unterminated_string_error_random_lines(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        self._impl_unterminated_string_error_events(state, random_line=True)
        with patch("logging.Logger.warning"):
            assert stuck_detector.is_stuck(headless_mode=True) is False

    def test_is_not_stuck_ipython_unterminated_string_error_only_two_incidents(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        self._impl_unterminated_string_error_events(state, random_line=False, incidents=2)
        with patch("logging.Logger.warning"):
            assert stuck_detector.is_stuck(headless_mode=True) is False

    def test_is_stuck_ipython_unterminated_string_error(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        self._impl_unterminated_string_error_events(state, random_line=False)
        with patch("logging.Logger.warning"):
            assert stuck_detector.is_stuck(headless_mode=True) is True

    def test_is_not_stuck_ipython_syntax_error_not_at_end(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        ipython_action_1 = IPythonRunCellAction(code='print("hello')
        state.history.append(ipython_action_1)
        ipython_observation_1 = IPythonRunCellObservation(
            content='print("hello\n       ^\nSyntaxError: unterminated string literal (detected at line 1)\nThis is some additional output',
            code='print("hello',
        )
        state.history.append(ipython_observation_1)
        ipython_action_2 = IPythonRunCellAction(code='print("hello')
        state.history.append(ipython_action_2)
        ipython_observation_2 = IPythonRunCellObservation(
            content='print("hello\n       ^\nSyntaxError: unterminated string literal (detected at line 1)\nToo much output here on and on',
            code='print("hello',
        )
        state.history.append(ipython_observation_2)
        ipython_action_3 = IPythonRunCellAction(code='print("hello')
        state.history.append(ipython_action_3)
        ipython_observation_3 = IPythonRunCellObservation(
            content='print("hello\n       ^\nSyntaxError: unterminated string literal (detected at line 3)\nEnough',
            code='print("hello',
        )
        state.history.append(ipython_observation_3)
        ipython_action_4 = IPythonRunCellAction(code='print("hello')
        state.history.append(ipython_action_4)
        ipython_observation_4 = IPythonRunCellObservation(
            content='print("hello\n       ^\nSyntaxError: unterminated string literal (detected at line 2)\nLast line of output',
            code='print("hello',
        )
        state.history.append(ipython_observation_4)
        with patch("logging.Logger.warning") as mock_warning:
            assert stuck_detector.is_stuck(headless_mode=True) is False
            mock_warning.assert_not_called()

    def test_is_stuck_repeating_action_observation_pattern(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        message_action = MessageAction(content="Come on", wait_for_response=False)
        message_action._source = EventSource.USER
        state.history.append(message_action)
        message_observation = NullObservation(content="")
        state.history.append(message_observation)
        cmd_action_1 = CmdRunAction(command="ls")
        state.history.append(cmd_action_1)
        cmd_observation_1 = CmdOutputObservation(command="ls", content="file1.txt\nfile2.txt")
        state.history.append(cmd_observation_1)
        read_action_1 = FileReadAction(path="file1.txt")
        state.history.append(read_action_1)
        read_observation_1 = FileReadObservation(content="File content", path="file1.txt")
        state.history.append(read_observation_1)
        cmd_action_2 = CmdRunAction(command="ls")
        state.history.append(cmd_action_2)
        cmd_observation_2 = CmdOutputObservation(command="ls", content="file1.txt\nfile2.txt")
        state.history.append(cmd_observation_2)
        read_action_2 = FileReadAction(path="file1.txt")
        state.history.append(read_action_2)
        read_observation_2 = FileReadObservation(content="File content", path="file1.txt")
        state.history.append(read_observation_2)
        message_action = MessageAction(content="Come on", wait_for_response=False)
        message_action._source = EventSource.USER
        state.history.append(message_action)
        message_null_observation = NullObservation(content="")
        state.history.append(message_null_observation)
        cmd_action_3 = CmdRunAction(command="ls")
        state.history.append(cmd_action_3)
        cmd_observation_3 = CmdOutputObservation(command="ls", content="file1.txt\nfile2.txt")
        state.history.append(cmd_observation_3)
        read_action_3 = FileReadAction(path="file1.txt")
        state.history.append(read_action_3)
        read_observation_3 = FileReadObservation(content="File content", path="file1.txt")
        state.history.append(read_observation_3)
        with patch("logging.Logger.warning") as mock_warning:
            assert stuck_detector.is_stuck(headless_mode=True) is True
            mock_warning.assert_called_once_with("Action, Observation pattern detected")

    def test_is_stuck_not_stuck(self, stuck_detector: StuckDetector):
        state = stuck_detector.state
        message_action = MessageAction(content="Done", wait_for_response=False)
        message_action._source = EventSource.USER
        hello_action = MessageAction(content="Hello", wait_for_response=False)
        state.history.append(hello_action)
        hello_observation = NullObservation(content="")
        state.history.append(hello_observation)
        cmd_action_1 = CmdRunAction(command="ls")
        state.history.append(cmd_action_1)
        cmd_observation_1 = CmdOutputObservation(command="ls", content="file1.txt\nfile2.txt")
        state.history.append(cmd_observation_1)
        read_action_1 = FileReadAction(path="file1.txt")
        state.history.append(read_action_1)
        read_observation_1 = FileReadObservation(content="File content", path="file1.txt")
        state.history.append(read_observation_1)
        cmd_action_2 = CmdRunAction(command="pwd")
        state.history.append(cmd_action_2)
        cmd_observation_2 = CmdOutputObservation(command="pwd", content="/home/user")
        state.history.append(cmd_observation_2)
        read_action_2 = FileReadAction(path="file2.txt")
        state.history.append(read_action_2)
        read_observation_2 = FileReadObservation(content="Another file content", path="file2.txt")
        state.history.append(read_observation_2)
        message_null_observation = NullObservation(content="")
        state.history.append(message_action)
        state.history.append(message_null_observation)
        cmd_action_3 = CmdRunAction(command="pwd")
        state.history.append(cmd_action_3)
        cmd_observation_3 = CmdOutputObservation(command="pwd", content="/home/user")
        state.history.append(cmd_observation_3)
        read_action_3 = FileReadAction(path="file2.txt")
        state.history.append(read_action_3)
        read_observation_3 = FileReadObservation(content="Another file content", path="file2.txt")
        state.history.append(read_observation_3)
        assert stuck_detector.is_stuck(headless_mode=True) is False

    def test_is_stuck_monologue(self, stuck_detector):
        state = stuck_detector.state
        message_action_1 = MessageAction(content="Hi there!")
        message_action_1._source = EventSource.USER
        state.history.append(message_action_1)
        message_action_2 = MessageAction(content="Hi there!")
        message_action_2._source = EventSource.AGENT
        state.history.append(message_action_2)
        message_action_3 = MessageAction(content="How are you?")
        message_action_3._source = EventSource.USER
        state.history.append(message_action_3)
        cmd_kill_action = CmdRunAction(command="echo 42", thought="I'm not stuck, he's stuck")
        state.history.append(cmd_kill_action)
        message_action_4 = MessageAction(content="I'm doing well, thanks for asking.")
        message_action_4._source = EventSource.AGENT
        state.history.append(message_action_4)
        message_action_5 = MessageAction(content="I'm doing well, thanks for asking.")
        message_action_5._source = EventSource.AGENT
        state.history.append(message_action_5)
        message_action_6 = MessageAction(content="I'm doing well, thanks for asking.")
        message_action_6._source = EventSource.AGENT
        state.history.append(message_action_6)
        assert stuck_detector.is_stuck(headless_mode=True)
        cmd_output_observation = CmdOutputObservation(
            content="OK, I was stuck, but no more.", command="storybook", exit_code=0
        )
        state.history.append(cmd_output_observation)
        message_action_7 = MessageAction(content="I'm doing well, thanks for asking.")
        message_action_7._source = EventSource.AGENT
        state.history.append(message_action_7)
        message_action_8 = MessageAction(content="I'm doing well, thanks for asking.")
        message_action_8._source = EventSource.AGENT
        state.history.append(message_action_8)
        with patch("logging.Logger.warning"):
            assert not stuck_detector.is_stuck(headless_mode=True)

    def test_is_stuck_context_window_error_loop(self, stuck_detector):
        """Test that we detect when we're stuck in a loop of context window errors."""
        state = stuck_detector.state
        message_action = MessageAction(content="Hello", wait_for_response=False)
        message_action._source = EventSource.USER
        state.history.append(message_action)
        message_observation = NullObservation(content="")
        state.history.append(message_observation)
        for _ in range(10):
            condensation = AgentCondensationObservation(content="Trimming prompt to meet context window limitations")
            state.history.append(condensation)
        with patch("logging.Logger.warning") as mock_warning:
            assert stuck_detector.is_stuck(headless_mode=True) is True
            mock_warning.assert_called_once_with("Context window error loop detected - repeated condensation events")

    def test_is_not_stuck_context_window_error_with_other_events(self, stuck_detector):
        """Test that we don't detect a loop when there are other events between condensation events."""
        state = stuck_detector.state
        message_action = MessageAction(content="Hello", wait_for_response=False)
        message_action._source = EventSource.USER
        state.history.append(message_action)
        message_observation = NullObservation(content="")
        state.history.append(message_observation)
        for i in range(10):
            condensation = AgentCondensationObservation(content="Trimming prompt to meet context window limitations")
            state.history.append(condensation)
            if i < 9:
                cmd_action = CmdRunAction(command=f"ls {i}")
                state.history.append(cmd_action)
                cmd_observation = CmdOutputObservation(command=f"ls {i}", content="file1.txt\nfile2.txt")
                state.history.append(cmd_observation)
                if i % 2 == 0:
                    read_action = FileReadAction(path=f"file{i}.txt")
                    state.history.append(read_action)
                    read_observation = FileReadObservation(content=f"File content {i}", path=f"file{i}.txt")
                    state.history.append(read_observation)
        with patch("logging.Logger.warning") as mock_warning:
            assert stuck_detector.is_stuck(headless_mode=True) is False
            mock_warning.assert_not_called()

    def test_is_not_stuck_context_window_error_less_than_ten(self, stuck_detector):
        """Test that we don't detect a loop with less than ten condensation events."""
        state = stuck_detector.state
        message_action = MessageAction(content="Hello", wait_for_response=False)
        message_action._source = EventSource.USER
        state.history.append(message_action)
        message_observation = NullObservation(content="")
        state.history.append(message_observation)
        for _ in range(9):
            condensation = AgentCondensationObservation(content="Trimming prompt to meet context window limitations")
            state.history.append(condensation)
        with patch("logging.Logger.warning") as mock_warning:
            assert stuck_detector.is_stuck(headless_mode=True) is False
            mock_warning.assert_not_called()

    def test_is_stuck_context_window_error_with_user_messages(self, stuck_detector):
        """Test that we still detect a loop even with user messages between condensation events in headless mode.

        User messages are filtered out in the stuck detection logic, so they shouldn't
        prevent us from detecting a loop of condensation events.
        """
        state = stuck_detector.state
        message_action = MessageAction(content="Hello", wait_for_response=False)
        message_action._source = EventSource.USER
        state.history.append(message_action)
        message_observation = NullObservation(content="")
        state.history.append(message_observation)
        for i in range(10):
            condensation = AgentCondensationObservation(content="Trimming prompt to meet context window limitations")
            state.history.append(condensation)
            if i < 9:
                user_message = MessageAction(content=f"Please continue {i}", wait_for_response=False)
                user_message._source = EventSource.USER
                state.history.append(user_message)
                user_observation = NullObservation(content="")
                state.history.append(user_observation)
        with patch("logging.Logger.warning") as mock_warning:
            assert stuck_detector.is_stuck(headless_mode=True) is True
            mock_warning.assert_called_once_with("Context window error loop detected - repeated condensation events")

    def test_is_not_stuck_context_window_error_in_non_headless(self, stuck_detector):
        """Test that in non-headless mode, we don't detect a loop if the condensation events.

        are before the last user message.

        In non-headless mode, we only look at events after the last user message.
        """
        state = stuck_detector.state
        for _ in range(10):
            condensation = AgentCondensationObservation(content="Trimming prompt to meet context window limitations")
            state.history.append(condensation)
        user_message = MessageAction(content="Please continue", wait_for_response=False)
        user_message._source = EventSource.USER
        state.history.append(user_message)
        user_observation = NullObservation(content="")
        state.history.append(user_observation)
        with patch("logging.Logger.warning") as mock_warning:
            assert stuck_detector.is_stuck(headless_mode=True) is True
            mock_warning.assert_called_once_with("Context window error loop detected - repeated condensation events")
            mock_warning.reset_mock()
            assert stuck_detector.is_stuck(headless_mode=False) is False
            mock_warning.assert_not_called()


class TestAgentController:

    @pytest.fixture
    def controller(self):
        controller = Mock(spec=AgentController)
        controller._is_stuck = AgentController._is_stuck.__get__(controller, AgentController)
        controller.delegate = None
        controller.state = Mock()
        return controller

    def test_is_stuck_delegate_stuck(self, controller: AgentController):
        controller.delegate = Mock()
        controller.delegate._is_stuck.return_value = True
        assert controller._is_stuck() is True
