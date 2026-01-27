"""Tests for unified shell abstraction."""

import sys
import tempfile

import pytest

from forge.runtime.utils.tool_registry import ToolRegistry
from forge.runtime.utils.unified_shell import create_shell_session


def test_create_shell_session_windows():
    """Test shell session creation on Windows."""
    if sys.platform != "win32":
        pytest.skip("Windows-only test")
    
    tools = ToolRegistry()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_shell_session(
            work_dir=temp_dir,
            tools=tools,
            username=None,
        )
        
        # Should create WindowsPowershellSession
        from forge.runtime.utils.windows_bash import WindowsPowershellSession
        assert isinstance(session, WindowsPowershellSession)
        
        session.close()


def test_create_shell_session_unix_with_tmux():
    """Test shell session creation on Unix with tmux."""
    if sys.platform == "win32":
        pytest.skip("Unix-only test")
    
    tools = ToolRegistry()
    
    if not tools.has_tmux:
        pytest.skip("tmux not available")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_shell_session(
            work_dir=temp_dir,
            tools=tools,
            username=None,
        )
        
        # Should create BashSession (with tmux)
        from forge.runtime.utils.bash import BashSession
        assert isinstance(session, BashSession)
        
        session.close()


def test_create_shell_session_unix_without_tmux():
    """Test shell session creation on Unix without tmux."""
    if sys.platform == "win32":
        pytest.skip("Unix-only test")
    
    tools = ToolRegistry()
    
    if tools.has_tmux:
        pytest.skip("tmux is available, cannot test fallback")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_shell_session(
            work_dir=temp_dir,
            tools=tools,
            username=None,
        )
        
        # Should create SimpleBashSession (no tmux)
        from forge.runtime.utils.simple_bash import SimpleBashSession
        assert isinstance(session, SimpleBashSession)
        
        session.close()


def test_shell_session_cwd():
    """Test that shell session respects working directory."""
    tools = ToolRegistry()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        session = create_shell_session(
            work_dir=temp_dir,
            tools=tools,
            username=None,
        )
        
        # CWD should be the temp directory
        assert session.cwd == temp_dir
        
        session.close()
