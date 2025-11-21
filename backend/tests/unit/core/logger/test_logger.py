import io
import json
import logging
import logging.handlers
import sys

from forge.core import logger as forge_logger


def _make_record(level=logging.INFO, msg="message"):
    return logging.LogRecord("test", level, __file__, 1, msg, args=(), exc_info=None)


def test_stack_info_filter_adds_stack_info():
    filt = forge_logger.StackInfoFilter()
    try:
        raise ValueError("boom")
    except ValueError:
        record = _make_record(logging.ERROR)
        record.exc_info = sys.exc_info()
        assert filt.filter(record) is True
        assert hasattr(record, "stack_info")

    info_record = _make_record(logging.INFO)
    assert filt.filter(info_record) is True
    assert getattr(info_record, "stack_info", None) in (None, "")


def test_no_color_formatter_strips_codes():
    formatter = forge_logger.NoColorFormatter("%(message)s")
    record = _make_record(msg="\x1b[31mcolored\x1b[0m")
    formatted = formatter.format(record)
    assert formatted == "colored"


def test_enhanced_json_formatter_adds_fields():
    formatter = forge_logger.EnhancedJSONFormatter()
    record = _make_record()
    record.request_id = "req-1"
    record.conversation_id = "conv"
    record.agent_type = "agent"
    record.action_type = "action"
    record.model_used = "model"
    record.tokens_consumed = 5
    record.cost_usd = 1.23
    record.duration_ms = 42
    log_record = {}
    formatter.add_fields(log_record, record, {})
    assert log_record["request_id"] == "req-1"
    assert log_record["conversation_id"] == "conv"
    assert log_record["agent_type"] == "agent"
    assert log_record["model_used"] == "model"
    assert log_record["tokens_consumed"] == 5
    assert log_record["cost_usd"] == 1.23
    assert log_record["duration_ms"] == 42
    assert log_record["location"].endswith(":1")


def test_strip_ansi_removes_sequences():
    assert forge_logger.strip_ansi("\x1b[32mhello\x1b[0m") == "hello"


def test_colored_formatter_formats_message(monkeypatch):
    monkeypatch.setattr(forge_logger, "DISABLE_COLOR_PRINTING", False, raising=False)
    formatter = forge_logger.ColoredFormatter("%(message)s", datefmt="%H:%M:%S")
    record = _make_record()
    record.msg_type = "ERROR"
    colored_output = formatter.format(record)
    assert "ERROR" in forge_logger.strip_ansi(colored_output)

    record_step = _make_record(msg="Step message")
    record_step.msg_type = "STEP"
    formatted_step = formatter.format(record_step).strip()
    assert "Step message" in formatted_step

    record_plain = _make_record()
    record_plain.msg_type = "UNKNOWN"
    assert formatter.format(record_plain) == "message"


def test_colored_formatter_with_event_source(monkeypatch):
    monkeypatch.setattr(forge_logger, "DISABLE_COLOR_PRINTING", False, raising=False)
    formatter = forge_logger.ColoredFormatter("%(message)s")
    record = _make_record()
    record.msg_type = "ACTION"
    record.event_source = "user"
    output = formatter.format(record)
    assert "USER_ACTION" in forge_logger.strip_ansi(output)


class _TTY:
    def __init__(self):
        self.buffer = io.StringIO()

    def write(self, data):
        self.buffer.write(data)

    def flush(self):
        pass

    def isatty(self):
        return True


def test_rolling_logger_adds_lines(monkeypatch):
    tty = _TTY()
    monkeypatch.setattr(forge_logger.sys, "stdout", tty)
    monkeypatch.setattr(forge_logger, "DEBUG", True, raising=False)
    roll = forge_logger.RollingLogger(max_lines=2, char_limit=5)
    roll.start()
    roll.add_line("first-line")
    roll.add_line("second-line")
    output = forge_logger.strip_ansi(tty.buffer.getvalue())
    assert "secon" in output


def test_sensitive_data_filter(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")
    filt = forge_logger.SensitiveDataFilter()
    record = _make_record(msg="api_key='sk-secret-value' other")
    assert filt.filter(record) is True
    assert "******" in record.msg


def test_trace_context_filter_and_helpers():
    forge_logger.set_trace_context({"trace_id": "abc"})
    filt = forge_logger.TraceContextFilter()
    record = _make_record()
    filt.filter(record)
    assert record.trace_id == "abc"
    forge_logger.clear_trace_context()
    record2 = _make_record()
    filt.filter(record2)
    assert not hasattr(record2, "trace_id")


def test_get_console_handler_returns_stream_handler():
    handler = forge_logger.get_console_handler(logging.WARNING)
    assert isinstance(handler, logging.StreamHandler)
    assert handler.level == logging.WARNING
    handler.close()


def test_get_file_handler_json(monkeypatch, tmp_path):
    monkeypatch.setattr(forge_logger, "LOG_JSON", True, raising=False)
    handler = forge_logger.get_file_handler(
        str(tmp_path), log_level=logging.ERROR, when="s", backup_count=1, utc=True
    )
    assert isinstance(handler, logging.handlers.TimedRotatingFileHandler)
    assert handler.level == logging.ERROR
    handler.close()


def test_json_formatter_and_handler():
    stream = io.StringIO()
    handler = forge_logger.json_log_handler(level=logging.INFO, _out=stream)
    handler.handle(_make_record())
    stream.seek(0)
    data = json.loads(stream.readline())
    assert forge_logger.LOG_JSON_LEVEL_KEY in data
    handler.close()


def test_log_uncaught_exceptions(monkeypatch):
    outputs = []
    monkeypatch.setattr(logging, "error", lambda msg: outputs.append(msg))
    forge_logger.log_uncaught_exceptions(ValueError, ValueError("bad"), None)
    assert any("ValueError" in item for item in outputs)


def test_fix_record_resolves_exc_info():
    record = _make_record()
    record.exc_info = True
    fixed = forge_logger._fix_record(record)
    assert fixed.exc_info is not True


def test_bind_context_helpers():
    adapter = forge_logger.ForgeLoggerAdapter(logging.getLogger("x"))
    new_adapter = adapter.bind(request_id="req")
    assert new_adapter.extra["request_id"] == "req"

    adapter2 = forge_logger.bind_context(logging.getLogger("y"), goal_id="goal")
    assert isinstance(adapter2, forge_logger.ForgeLoggerAdapter)
    assert adapter2.extra["goal_id"] == "goal"


def test_llm_file_handler_creates_files(monkeypatch, tmp_path):
    monkeypatch.setattr(forge_logger, "LOG_DIR", str(tmp_path), raising=False)
    monkeypatch.setattr(forge_logger, "DEBUG", False, raising=False)
    monkeypatch.setattr(
        forge_logger.FORGE_logger, "debug", lambda *args, **kwargs: None
    )
    handler = forge_logger._get_llm_file_handler("prompt", logging.INFO)
    record = _make_record()
    handler.emit(record)
    try:
        handler.close()
    except ValueError:
        # Some rotation scenarios close the underlying stream earlier
        handler.acquire()
        handler.stream = None
        handler.release()
    files = list((tmp_path / "llm" / handler.session).glob("prompt_*.log"))
    assert len(files) == 1


def test_setup_llm_logger_with_file(monkeypatch, tmp_path):
    monkeypatch.setattr(forge_logger, "LOG_DIR", str(tmp_path), raising=False)
    monkeypatch.setattr(forge_logger, "LOG_TO_FILE", True, raising=False)
    monkeypatch.setattr(forge_logger, "DEBUG", False, raising=False)
    monkeypatch.setattr(
        forge_logger.FORGE_logger, "debug", lambda *args, **kwargs: None
    )
    logger_obj = forge_logger._setup_llm_logger("custom_llm", logging.WARNING)
    assert logger_obj.level == logging.WARNING
    for handler in list(logger_obj.handlers):
        handler.close()
        logger_obj.removeHandler(handler)


def test_json_formatter_renames_level_key():
    formatter = forge_logger.json_formatter()
    assert formatter.rename_fields["levelname"] == forge_logger.LOG_JSON_LEVEL_KEY


def test_json_log_handler_configures_stream():
    stream = io.StringIO()
    handler = forge_logger.json_log_handler(level=logging.DEBUG, _out=stream)
    assert handler.level == logging.DEBUG
    handler.close()
