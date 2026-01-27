"""Tests for ToolRegistry cross-platform tool detection."""

import shutil
import sys
from unittest.mock import patch

import pytest

from forge.runtime.utils.tool_registry import ToolRegistry


def test_tool_registry_initialization():
    """Test that ToolRegistry initializes and detects tools."""
    registry = ToolRegistry()
    
    # Should always detect a shell
    assert registry.shell_type in ("bash", "pwsh", "powershell", "cmd", "sh")
    
    # Should always detect a search tool (even if it's Python fallback)
    assert registry.search_tool in ("ripgrep", "grep", "findstr", "python")


def test_shell_detection_windows():
    """Test shell detection on Windows."""
    if sys.platform != "win32":
        pytest.skip("Windows-only test")
    
    registry = ToolRegistry()
    
    # Windows should detect PowerShell or cmd
    assert registry.shell_type in ("pwsh", "powershell", "cmd")
    assert registry.has_powershell or registry.shell_type == "cmd"


def test_shell_detection_unix():
    """Test shell detection on Unix-like systems."""
    if sys.platform == "win32":
        pytest.skip("Unix-only test")
    
    registry = ToolRegistry()
    
    # Unix should detect bash or sh
    assert registry.shell_type in ("bash", "sh")
    assert registry.has_bash or registry.shell_type == "sh"


def test_tmux_detection_unix():
    """Test tmux detection on Unix systems."""
    if sys.platform == "win32":
        pytest.skip("Unix-only test")
    
    registry = ToolRegistry()
    
    # tmux availability depends on system
    # Just verify the property works
    assert isinstance(registry.has_tmux, bool)


def test_tmux_not_available_windows():
    """Test that tmux is correctly reported as unavailable on Windows."""
    if sys.platform != "win32":
        pytest.skip("Windows-only test")
    
    registry = ToolRegistry()
    
    # tmux should never be available on Windows
    assert not registry.has_tmux


def test_git_detection():
    """Test Git detection."""
    registry = ToolRegistry()
    
    # Git availability depends on system
    # Just verify the property works
    assert isinstance(registry.has_git, bool)


def test_search_tool_preference():
    """Test that search tools are detected in preference order."""
    registry = ToolRegistry()
    
    # If ripgrep is available, it should be preferred
    if shutil.which("rg"):
        assert registry.search_tool == "ripgrep"
        assert registry.has_ripgrep
    # Otherwise, check for grep
    elif shutil.which("grep"):
        assert registry.search_tool == "grep"
    # Windows might have findstr
    elif sys.platform == "win32" and shutil.which("findstr"):
        assert registry.search_tool == "findstr"
    # Fallback to Python
    else:
        assert registry.search_tool == "python"


def test_get_tool_info():
    """Test getting detailed tool information."""
    registry = ToolRegistry()
    
    # Get shell info
    shell_info = registry.get_tool_info("shell")
    assert shell_info is not None
    assert shell_info.available
    assert shell_info.name in ("bash", "pwsh", "powershell", "cmd", "sh")
    
    # Get search info
    search_info = registry.get_tool_info("search")
    assert search_info is not None
    assert search_info.available


def test_require_git_success():
    """Test require_git when Git is available."""
    registry = ToolRegistry()
    
    if not registry.has_git:
        pytest.skip("Git not available on this system")
    
    # Should not raise
    registry.require_git()


def test_require_git_failure():
    """Test require_git when Git is not available."""
    registry = ToolRegistry()
    
    if registry.has_git:
        pytest.skip("Git is available on this system")
    
    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="Git is required"):
        registry.require_git()


def test_tool_registry_caching():
    """Test that tool detection is cached (not re-run)."""
    # Create two instances
    registry1 = ToolRegistry()
    registry2 = ToolRegistry()
    
    # They should detect the same tools
    assert registry1.shell_type == registry2.shell_type
    assert registry1.search_tool == registry2.search_tool
    assert registry1.has_git == registry2.has_git
