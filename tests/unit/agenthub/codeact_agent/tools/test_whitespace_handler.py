from __future__ import annotations

from forge.agenthub.codeact_agent.tools.whitespace_handler import (
    IndentConfig,
    IndentStyle,
    WhitespaceHandler,
)


def test_detect_line_ending_windows():
    assert WhitespaceHandler._detect_line_ending("line\r\n") == "\r\n"
    assert WhitespaceHandler._detect_line_ending("line\n") == "\n"


def test_count_indent_styles_and_determine():
    lines = ["\tfoo", "    bar", "    baz", "plain"]
    tab_count, space_count, sizes = WhitespaceHandler._count_indent_styles(lines)
    assert tab_count == 1
    assert space_count == 2
    assert sizes == [4, 4]

    style, size = WhitespaceHandler._determine_indent_style(
        tab_count, space_count, sizes, "python"
    )
    assert style == IndentStyle.SPACES and size == 4

    style_tabs, size_tabs = WhitespaceHandler._determine_indent_style(
        3, 1, [], None
    )
    assert style_tabs == IndentStyle.TABS and size_tabs == 1


def test_detect_indent_and_find_indent_size():
    code = "def foo():\n  return 1\n    \n"
    config = WhitespaceHandler.detect_indent(code, language="python")
    assert config.style == IndentStyle.SPACES
    assert config.size == 2

    go_config = WhitespaceHandler.detect_indent("print('x')", language="go")
    assert go_config.style == IndentStyle.TABS
    assert go_config.size == 1

    assert WhitespaceHandler._find_indent_size([2, 4, 6]) == 2
    assert WhitespaceHandler._find_indent_size([1, 2, 3]) == 4  # result == 1 path
    assert WhitespaceHandler._find_indent_size([1, 10, 19]) == 4  # result > 8
    assert WhitespaceHandler._find_indent_size([]) == 4


def test_styles_match_and_calculations():
    config_spaces = IndentConfig(IndentStyle.SPACES, 4, "\n")
    config_tabs = IndentConfig(IndentStyle.TABS, 1, "\n")
    assert WhitespaceHandler._styles_match(config_spaces, config_spaces)
    assert not WhitespaceHandler._styles_match(config_spaces, config_tabs)

    assert (
        WhitespaceHandler._calculate_indent_level(8, config_spaces) == 2
    )
    assert (
        WhitespaceHandler._calculate_indent_level(3, config_tabs) == 3
    )

    assert (
        WhitespaceHandler._apply_target_indent(2, config_spaces) == " " * 8
    )


def test_normalize_line_indent_and_normalize_indent():
    current = IndentConfig(IndentStyle.SPACES, 2, "\n")
    target = IndentConfig(IndentStyle.TABS, 1, "\n")
    line = "    code"
    normalized_line = WhitespaceHandler._normalize_line_indent(
        line, current, target
    )
    assert normalized_line.startswith("\t\t")

    code = "line1\nline2"
    target_config = IndentConfig(IndentStyle.SPACES, 2, "\r\n")
    normalized = WhitespaceHandler.normalize_indent(code, target_config=target_config)
    assert "\r\n" in normalized


def test_auto_indent_block_and_get_line_indent():
    config = IndentConfig(IndentStyle.SPACES, 2, "\n")
    block = "line1\n\nline2"
    auto = WhitespaceHandler.auto_indent_block(block, 2, config)
    assert auto.splitlines()[0].startswith(" " * 4)
    go_auto = WhitespaceHandler.auto_indent_block("line", 1, language="go")
    assert go_auto.startswith("\t")

    assert WhitespaceHandler.get_line_indent("    x", config) == 2
    assert WhitespaceHandler.get_line_indent("\t\tfoo", IndentConfig(IndentStyle.TABS, 1, "\n")) == 2
    assert WhitespaceHandler.get_line_indent("code", config) == 0


def test_preserve_relative_indent_helpers():
    config = IndentConfig(IndentStyle.SPACES, 2, "\n")
    lines = ["    x", "      y", ""]
    assert WhitespaceHandler._get_min_indent(lines, config) == 2

    reindented = WhitespaceHandler._reindent_line(
        "    x", min_indent=1, new_base_indent=2, config=config
    )
    assert reindented.startswith(" " * 4)
    assert (
        WhitespaceHandler._reindent_line("", min_indent=0, new_base_indent=0, config=config)
        == ""
    )

    block = "    a\n      b"
    preserved = WhitespaceHandler.preserve_relative_indent(
        block, new_base_indent=1, config=config
    )
    assert preserved.splitlines()[0].startswith(" " * 2)
    assert preserved.splitlines()[1].startswith(" " * 4)

    go_preserved = WhitespaceHandler.preserve_relative_indent("a\n\tb", new_base_indent=1, language="go")
    assert go_preserved.splitlines()[0].startswith("\t")


def test_strip_and_clean_helpers():
    code = "a  \n\n\n\nb"
    stripped = WhitespaceHandler.strip_trailing_whitespace(code)
    assert stripped.endswith("\n\n\nb")

    ensured = WhitespaceHandler.ensure_final_newline("content")
    assert ensured.endswith("\n") and ensured.count("\n") == 1

    messy = "def foo():\n    pass  \n\n\n\n"
    cleaned = WhitespaceHandler.clean_whitespace(messy)
    assert cleaned.endswith("\n")
    assert "\n\n\n\n" not in cleaned

