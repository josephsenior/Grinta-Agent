"""Edit-related tests for the DockerRuntime."""

import os

import pytest

from conftest import TEST_IN_CI, _close_test_runtime, _load_runtime
from forge.runtime.utils.edit import get_diff
from forge.core.logger import forge_logger as logger
from forge.events.action import FileEditAction, FileReadAction
from forge.events.observation import FileEditObservation

ORGINAL = "from flask import Flask\napp = Flask(__name__)\n\n@app.route('/')\ndef index():\n    numbers = list(range(1, 11))\n    return str(numbers)\n\nif __name__ == '__main__':\n    app.run(port=5000)\n"


@pytest.mark.skipif(TEST_IN_CI != "True", reason="This test requires LLM to run.")
def test_edit_from_scratch(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        action = FileEditAction(content=ORGINAL, start=-1, path=os.path.join("/workspace", "app.py"))
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs, FileEditObservation), "The observation should be a FileEditObservation."
        action = FileReadAction(path=os.path.join("/workspace", "app.py"))
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert obs.content.strip() == ORGINAL.strip()
    finally:
        _close_test_runtime(runtime)


EDIT = "# above stays the same\n@app.route('/')\ndef index():\n    numbers = list(range(1, 11))\n    return '<table>' + ''.join([f'<tr><td>{i}</td></tr>' for i in numbers]) + '</table>'\n# below stays the same\n"


@pytest.mark.skipif(TEST_IN_CI != "True", reason="This test requires LLM to run.")
def test_edit(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        action = FileEditAction(content=ORGINAL, path=os.path.join("/workspace", "app.py"))
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs, FileEditObservation), "The observation should be a FileEditObservation."
        action = FileReadAction(path=os.path.join("/workspace", "app.py"))
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert obs.content.strip() == ORGINAL.strip()
        action = FileEditAction(content=EDIT, path=os.path.join("/workspace", "app.py"))
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert (
            obs.content.strip()
            == "--- /workspace/app.py\n+++ /workspace/app.py\n@@ -4,7 +4,7 @@\n @app.route('/')\n def index():\n     numbers = list(range(1, 11))\n-    return str(numbers)\n+    return '<table>' + ''.join([f'<tr><td>{i}</td></tr>' for i in numbers]) + '</table>'\n\n if __name__ == '__main__':\n     app.run(port=5000)\n".strip()
        )
    finally:
        _close_test_runtime(runtime)


ORIGINAL_LONG = "\n".join([f"This is line {i}" for i in range(1, 1000)])
EDIT_LONG = "\nThis is line 100 + 10\nThis is line 101 + 10\n"


@pytest.mark.skipif(TEST_IN_CI != "True", reason="This test requires LLM to run.")
def test_edit_long_file(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        action = FileEditAction(content=ORIGINAL_LONG, path=os.path.join("/workspace", "app.py"), start=-1)
        logger.info(action, extra={"msg_type": "ACTION"})
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs, FileEditObservation), "The observation should be a FileEditObservation."
        action = FileReadAction(path=os.path.join("/workspace", "app.py"))
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert obs.content.strip() == ORIGINAL_LONG.strip()
        action = FileEditAction(content=EDIT_LONG, path=os.path.join("/workspace", "app.py"), start=100, end=200)
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert (
            obs.content.strip()
            == "--- /workspace/app.py\n+++ /workspace/app.py\n@@ -97,8 +97,8 @@\n This is line 97\n This is line 98\n This is line 99\n-This is line 100\n-This is line 101\n+This is line 100 + 10\n+This is line 101 + 10\n This is line 102\n This is line 103\n This is line 104\n".strip()
        )
    finally:
        _close_test_runtime(runtime)


def test_edit_obs_insert_only():
    EDIT_LONG_INSERT_ONLY = (
        "\n".join([f"This is line {i}" for i in range(1, 100)])
        + EDIT_LONG
        + "\n".join([f"This is line {i}" for i in range(100, 1000)])
    )
    diff = get_diff(ORIGINAL_LONG, EDIT_LONG_INSERT_ONLY, "/workspace/app.py")
    obs = FileEditObservation(
        content=diff,
        path="/workspace/app.py",
        prev_exist=True,
        old_content=ORIGINAL_LONG,
        new_content=EDIT_LONG_INSERT_ONLY,
    )
    assert (
        str(obs).strip()
        == "\n[Existing file /workspace/app.py is edited with 1 changes.]\n[begin of edit 1 / 1]\n(content before edit)\n  98|This is line 98\n  99|This is line 99\n 100|This is line 100\n 101|This is line 101\n(content after edit)\n  98|This is line 98\n  99|This is line 99\n+100|This is line 100 + 10\n+101|This is line 101 + 10\n 102|This is line 100\n 103|This is line 101\n[end of edit 1 / 1]\n".strip()
    )


def test_edit_obs_replace():
    _new_content = (
        "\n".join([f"This is line {i}" for i in range(1, 100)])
        + EDIT_LONG
        + "\n".join([f"This is line {i}" for i in range(102, 1000)])
    )
    diff = get_diff(ORIGINAL_LONG, _new_content, "/workspace/app.py")
    obs = FileEditObservation(
        content=diff, path="/workspace/app.py", prev_exist=True, old_content=ORIGINAL_LONG, new_content=_new_content
    )
    print(obs)
    assert (
        str(obs).strip()
        == "\n[Existing file /workspace/app.py is edited with 1 changes.]\n[begin of edit 1 / 1]\n(content before edit)\n  98|This is line 98\n  99|This is line 99\n-100|This is line 100\n-101|This is line 101\n 102|This is line 102\n 103|This is line 103\n(content after edit)\n  98|This is line 98\n  99|This is line 99\n+100|This is line 100 + 10\n+101|This is line 101 + 10\n 102|This is line 102\n 103|This is line 103\n[end of edit 1 / 1]\n".strip()
    )


def test_edit_obs_replace_with_empty_line():
    _new_content = (
        "\n".join([f"This is line {i}" for i in range(1, 100)])
        + "\n"
        + EDIT_LONG
        + "\n".join([f"This is line {i}" for i in range(102, 1000)])
    )
    diff = get_diff(ORIGINAL_LONG, _new_content, "/workspace/app.py")
    obs = FileEditObservation(
        content=diff, path="/workspace/app.py", prev_exist=True, old_content=ORIGINAL_LONG, new_content=_new_content
    )
    print(obs)
    assert (
        str(obs).strip()
        == "\n[Existing file /workspace/app.py is edited with 1 changes.]\n[begin of edit 1 / 1]\n(content before edit)\n  98|This is line 98\n  99|This is line 99\n-100|This is line 100\n-101|This is line 101\n 102|This is line 102\n 103|This is line 103\n(content after edit)\n  98|This is line 98\n  99|This is line 99\n+100|\n+101|This is line 100 + 10\n+102|This is line 101 + 10\n 103|This is line 102\n 104|This is line 103\n[end of edit 1 / 1]\n".strip()
    )


def test_edit_obs_multiple_edits():
    _new_content = (
        "\n".join([f"This is line {i}" for i in range(1, 50)])
        + "\nbalabala\n"
        + "\n".join([f"This is line {i}" for i in range(50, 100)])
        + EDIT_LONG
        + "\n".join([f"This is line {i}" for i in range(102, 1000)])
    )
    diff = get_diff(ORIGINAL_LONG, _new_content, "/workspace/app.py")
    obs = FileEditObservation(
        content=diff, path="/workspace/app.py", prev_exist=True, old_content=ORIGINAL_LONG, new_content=_new_content
    )
    assert (
        str(obs).strip()
        == "\n[Existing file /workspace/app.py is edited with 2 changes.]\n[begin of edit 1 / 2]\n(content before edit)\n 48|This is line 48\n 49|This is line 49\n 50|This is line 50\n 51|This is line 51\n(content after edit)\n 48|This is line 48\n 49|This is line 49\n+50|balabala\n 51|This is line 50\n 52|This is line 51\n[end of edit 1 / 2]\n-------------------------\n[begin of edit 2 / 2]\n(content before edit)\n  98|This is line 98\n  99|This is line 99\n-100|This is line 100\n-101|This is line 101\n 102|This is line 102\n 103|This is line 103\n(content after edit)\n  99|This is line 98\n 100|This is line 99\n+101|This is line 100 + 10\n+102|This is line 101 + 10\n 103|This is line 102\n 104|This is line 103\n[end of edit 2 / 2]\n".strip()
    )


def test_edit_visualize_failed_edit():
    _new_content = (
        "\n".join([f"This is line {i}" for i in range(1, 50)])
        + "\nbalabala\n"
        + "\n".join([f"This is line {i}" for i in range(50, 100)])
        + EDIT_LONG
        + "\n".join([f"This is line {i}" for i in range(102, 1000)])
    )
    diff = get_diff(ORIGINAL_LONG, _new_content, "/workspace/app.py")
    obs = FileEditObservation(
        content=diff, path="/workspace/app.py", prev_exist=True, old_content=ORIGINAL_LONG, new_content=_new_content
    )
    assert (
        obs.visualize_diff(change_applied=False).strip()
        == "\n[Changes are NOT applied to /workspace/app.py - Here's how the file looks like if changes are applied.]\n[begin of ATTEMPTED edit 1 / 2]\n(content before ATTEMPTED edit)\n 48|This is line 48\n 49|This is line 49\n 50|This is line 50\n 51|This is line 51\n(content after ATTEMPTED edit)\n 48|This is line 48\n 49|This is line 49\n+50|balabala\n 51|This is line 50\n 52|This is line 51\n[end of ATTEMPTED edit 1 / 2]\n-------------------------\n[begin of ATTEMPTED edit 2 / 2]\n(content before ATTEMPTED edit)\n  98|This is line 98\n  99|This is line 99\n-100|This is line 100\n-101|This is line 101\n 102|This is line 102\n 103|This is line 103\n(content after ATTEMPTED edit)\n  99|This is line 98\n 100|This is line 99\n+101|This is line 100 + 10\n+102|This is line 101 + 10\n 103|This is line 102\n 104|This is line 103\n[end of ATTEMPTED edit 2 / 2]\n".strip()
    )
