import pytest
from forge.runtime.utils.bash import escape_bash_special_chars, split_bash_commands


def test_split_commands_util():
    cmds = [
        "ls -l",
        'echo -e "hello\nworld"',
        '\necho -e "hello it\\\'s me"\n'.strip(),
        "\necho \\\n    -e 'hello' \\\n    -v\n".strip(),
        "\necho -e 'hello\\nworld\\nare\\nyou\\nthere?'\n".strip(),
        "\necho -e 'hello\nworld\nare\nyou\\n\nthere?'\n".strip(),
        "\necho -e 'hello\nworld \"\n'\n".strip(),
        '\nkubectl apply -f - <<EOF\napiVersion: v1\nkind: Pod\nmetadata:\n  name: busybox-sleep\nspec:\n  containers:\n  - name: busybox\n    image: busybox:1.28\n    args:\n    - sleep\n    - "1000000"\nEOF\n'.strip(),
        '\nmkdir -p _modules && for month in {01..04}; do\n    for day in {01..05}; do\n        touch "_modules/2024-${month}-${day}-sample.md"\n    done\ndone\n'.strip(),
    ]
    joined_cmds = "\n".join(cmds)
    split_cmds = split_bash_commands(joined_cmds)
    for s in split_cmds:
        print("\nCMD")
        print(s)
    for i in range(len(cmds)):
        assert split_cmds[i].strip() == cmds[i].strip(), f"At index {i}: {split_cmds[i]} != {cmds[i]}."


@pytest.mark.parametrize(
    "input_command, expected_output",
    [
        ("ls -l", ["ls -l"]),
        ("echo 'Hello, world!'", ["echo 'Hello, world!'"]),
        ("cd /tmp && touch test.txt", ["cd /tmp && touch test.txt"]),
        ("echo -e 'line1\\nline2\\nline3'", ["echo -e 'line1\\nline2\\nline3'"]),
        ("grep 'pattern' file.txt | sort | uniq", ["grep 'pattern' file.txt | sort | uniq"]),
        ("for i in {1..5}; do echo $i; done", ["for i in {1..5}; do echo $i; done"]),
        ("echo 'Single quotes don\\'t escape'", ["echo 'Single quotes don\\'t escape'"]),
        ('echo "Double quotes \\"do\\" escape"', ['echo "Double quotes \\"do\\" escape"']),
    ],
)
def test_single_commands(input_command, expected_output):
    assert split_bash_commands(input_command) == expected_output


def test_heredoc():
    input_commands = '\ncat <<EOF\nmultiline\ntext\nEOF\necho "Done"\n'
    expected_output = ["cat <<EOF\nmultiline\ntext\nEOF", 'echo "Done"']
    assert split_bash_commands(input_commands) == expected_output


def test_backslash_continuation():
    input_commands = '\necho "This is a long command that spans multiple lines"\necho "Next command"\n'
    expected_output = ['echo "This is a long command that spans multiple lines"', 'echo "Next command"']
    assert split_bash_commands(input_commands) == expected_output


def test_comments():
    input_commands = '\necho "Hello" # This is a comment\n# This is another comment\nls -l\n'
    expected_output = ['echo "Hello" # This is a comment\n# This is another comment', "ls -l"]
    assert split_bash_commands(input_commands) == expected_output


def test_complex_quoting():
    input_commands = "\necho \"This is a \\\"quoted\\\" string\"\necho 'This is a '''single-quoted''' string'\necho \"Mixed 'quotes' in \\\"double quotes\\\"\"\n"
    expected_output = [
        'echo "This is a \\"quoted\\" string"',
        "echo 'This is a '''single-quoted''' string'",
        'echo "Mixed \'quotes\' in \\"double quotes\\""',
    ]
    assert split_bash_commands(input_commands) == expected_output


def test_invalid_syntax():
    invalid_inputs = ['echo "Unclosed quote', "echo 'Unclosed quote", "cat <<EOF\nUnclosed heredoc"]
    for input_command in invalid_inputs:
        assert split_bash_commands(input_command) == [input_command]


def test_unclosed_backtick():
    command = "echo `unclosed backtick"
    try:
        result = split_bash_commands(command)
        assert result == [command]
    except TypeError as e:
        raise e
    curl_command = 'curl -X POST "https://api.github.com/repos/example-org/example-repo/pulls" \\ -H "Authorization: Bearer $GITHUB_TOKEN" \\ -H "Accept: application/vnd.github.v3+json" \\ -d \'{ "title": "XXX", "head": "XXX", "base": "main", "draft": false }\' `echo unclosed'
    try:
        result = split_bash_commands(curl_command)
        assert result == [curl_command]
    except TypeError as e:
        raise e


def test_over_escaped_command():
    over_escaped_command = "# 0. Setup directory\\\\nrm -rf /workspace/repro_sphinx_bug && mkdir -p /workspace/repro_sphinx_bug && cd /workspace/repro_sphinx_bug\\\\n\\\\n# 1. Run sphinx-quickstart\\\\nsphinx-quickstart --no-sep --project myproject --author me -v 0.1.0 --release 0.1.0 --language en . -q\\\\n\\\\n# 2. Create index.rst\\\\necho -e \\'Welcome\\\\\\\\\\\\\\\\n=======\\\\\\\\\\\\\\\\n\\\\\\\\\\\\\\\\n.. toctree::\\\\\\\\n   :maxdepth: 2\\\\\\\\\\\\\\\\n\\\\\\\\\\\\\\\\n   mypackage_file\\\\\\\\\\\\\\\\n\\' > index.rst"
    try:
        result = split_bash_commands(over_escaped_command)
        assert result == [over_escaped_command]
    except Exception as e:
        pytest.fail(f"split_bash_commands raised {type(e).__name__} unexpectedly: {e}")


@pytest.fixture
def sample_commands():
    return [
        "ls -l",
        'echo "Hello, world!"',
        "cd /tmp && touch test.txt",
        'echo -e "line1\\nline2\\nline3"',
        'grep "pattern" file.txt | sort | uniq',
        "for i in {1..5}; do echo $i; done",
        "cat <<EOF\nmultiline\ntext\nEOF",
        'echo "Escaped \\"quotes\\""',
        "echo 'Single quotes don\\'t escape'",
        'echo "Command with a trailing backslash \\\n  and continuation"',
    ]


def test_split_single_commands(sample_commands):
    for cmd in sample_commands:
        result = split_bash_commands(cmd)
        assert len(result) == 1, f"Expected single command, got: {result}"


def test_split_commands_with_heredoc():
    input_commands = '\ncat <<EOF\nmultiline\ntext\nEOF\necho "Done"\n'
    expected_output = ["cat <<EOF\nmultiline\ntext\nEOF", 'echo "Done"']
    result = split_bash_commands(input_commands)
    assert result == expected_output, f"Expected {expected_output}, got {result}"


def test_split_commands_with_backslash_continuation():
    input_commands = '\necho "This is a long command that spans multiple lines"\necho "Next command"\n'
    expected_output = ['echo "This is a long command that spans multiple lines"', 'echo "Next command"']
    result = split_bash_commands(input_commands)
    assert result == expected_output, f"Expected {expected_output}, got {result}"


def test_split_commands_with_empty_lines():
    input_commands = '\nls -l\n\necho "Hello"\n\ncd /tmp\n'
    expected_output = ["ls -l", 'echo "Hello"', "cd /tmp"]
    result = split_bash_commands(input_commands)
    assert result == expected_output, f"Expected {expected_output}, got {result}"


def test_split_commands_with_comments():
    input_commands = '\necho "Hello" # This is a comment\n# This is another comment\nls -l\n'
    expected_output = ['echo "Hello" # This is a comment\n# This is another comment', "ls -l"]
    result = split_bash_commands(input_commands)
    assert result == expected_output, f"Expected {expected_output}, got {result}"


def test_split_commands_with_complex_quoting():
    input_commands = '\necho "This is a \\"quoted\\" string"\necho "Mixed \'quotes\' in \\"double quotes\\""\n'
    expected_output = ['echo "This is a \\"quoted\\" string"', 'echo "Mixed \'quotes\' in \\"double quotes\\""']
    result = split_bash_commands(input_commands)
    assert result == expected_output, f"Expected {expected_output}, got {result}"


def test_split_commands_with_invalid_input():
    invalid_inputs = ['echo "Unclosed quote', "echo 'Unclosed quote", "cat <<EOF\nUnclosed heredoc"]
    for input_command in invalid_inputs:
        assert split_bash_commands(input_command) == [input_command]


def test_escape_bash_special_chars():
    test_cases = [
        ("echo test \\; ls", "echo test \\\\; ls"),
        ("grep pattern \\| sort", "grep pattern \\\\| sort"),
        ("cmd1 \\&\\& cmd2", "cmd1 \\\\&\\\\& cmd2"),
        ("cat file \\> output.txt", "cat file \\\\> output.txt"),
        ("cat \\< input.txt", "cat \\\\< input.txt"),
        ('echo "test \\; unchanged"', 'echo "test \\; unchanged"'),
        ("echo 'test \\| unchanged'", "echo 'test \\| unchanged'"),
        ('echo "quoted \\;" \\; "more" \\| grep', 'echo "quoted \\;" \\\\; "more" \\\\| grep'),
        ("cmd1 \\;\\|\\& cmd2", "cmd1 \\\\;\\\\|\\\\& cmd2"),
        ("echo test\\ntest", "echo test\\ntest"),
        ('echo "test\\ntest"', 'echo "test\\ntest"'),
        ("", ""),
        ("\\\\", "\\\\"),
        ('\\"', '\\"'),
    ]
    for input_cmd, expected in test_cases:
        result = escape_bash_special_chars(input_cmd)
        assert result == expected, f'Failed on input "{input_cmd}"\nExpected: "{expected}"\nGot: "{result}"'


def test_escape_bash_special_chars_with_invalid_syntax():
    invalid_inputs = ['echo "unclosed quote', "echo 'unclosed quote", "cat <<EOF\nunclosed heredoc"]
    for input_cmd in invalid_inputs:
        result = escape_bash_special_chars(input_cmd)
        assert result == input_cmd, f"Failed to handle invalid input: {input_cmd}"


def test_escape_bash_special_chars_with_heredoc():
    input_cmd = "cat <<EOF\nline1 \\; not escaped\nline2 \\| not escaped\nEOF"
    expected = input_cmd
    result = escape_bash_special_chars(input_cmd)
    assert result == expected, f"Failed to handle heredoc correctly\nExpected: {expected}\nGot: {result}"


def test_escape_bash_special_chars_with_parameter_expansion():
    test_cases = [
        ("echo $HOME", "echo $HOME"),
        ("echo ${HOME}", "echo ${HOME}"),
        ("echo ${HOME:-default}", "echo ${HOME:-default}"),
        ("echo $HOME \\; ls", "echo $HOME \\\\; ls"),
        ("echo ${PATH} \\| grep bin", "echo ${PATH} \\\\| grep bin"),
        ('echo "$HOME"', 'echo "$HOME"'),
        ('echo "${HOME}"', 'echo "${HOME}"'),
        ("echo ${var:=default} \\; ls", "echo ${var:=default} \\\\; ls"),
        ("echo ${!prefix*} \\| sort", "echo ${!prefix*} \\\\| sort"),
    ]
    for input_cmd, expected in test_cases:
        result = escape_bash_special_chars(input_cmd)
        assert result == expected, f'Failed on input "{input_cmd}"\nExpected: "{expected}"\nGot: "{result}"'


def test_escape_bash_special_chars_with_command_substitution():
    test_cases = [
        ("echo $(pwd)", "echo $(pwd)"),
        ("echo `pwd`", "echo `pwd`"),
        ("echo $(pwd) \\; ls", "echo $(pwd) \\\\; ls"),
        ("echo `pwd` \\| grep home", "echo `pwd` \\\\| grep home"),
        ("echo $(echo `pwd`)", "echo $(echo `pwd`)"),
        ('echo $(find . -name "*.txt" \\; ls)', 'echo $(find . -name "*.txt" \\; ls)'),
        ('echo "$(pwd)"', 'echo "$(pwd)"'),
        ('echo "`pwd`"', 'echo "`pwd`"'),
    ]
    for input_cmd, expected in test_cases:
        result = escape_bash_special_chars(input_cmd)
        assert result == expected, f'Failed on input "{input_cmd}"\nExpected: "{expected}"\nGot: "{result}"'


def test_escape_bash_special_chars_mixed_nodes():
    test_cases = [
        ("echo $HOME/$(pwd)", "echo $HOME/$(pwd)"),
        ("echo $HOME/$(pwd) \\; ls", "echo $HOME/$(pwd) \\\\; ls"),
        ('echo "${HOME}/$(basename `pwd`) \\; next"', 'echo "${HOME}/$(basename `pwd`) \\; next"'),
        ("VAR=${HOME} \\; echo $(pwd)", "VAR=${HOME} \\\\; echo $(pwd)"),
        (
            'find . -name "*.txt" -exec grep "${PATTERN:-default}" {} \\;',
            'find . -name "*.txt" -exec grep "${PATTERN:-default}" {} \\\\;',
        ),
        (
            'echo "Current path: ${PWD}/$(basename `pwd`)" \\| grep home',
            'echo "Current path: ${PWD}/$(basename `pwd`)" \\\\| grep home',
        ),
    ]
    for input_cmd, expected in test_cases:
        result = escape_bash_special_chars(input_cmd)
        assert result == expected, f'Failed on input "{input_cmd}"\nExpected: "{expected}"\nGot: "{result}"'


def test_escape_bash_special_chars_with_chained_commands():
    test_cases = [
        ("ls && pwd", "ls && pwd"),
        ('echo "hello" && ls', 'echo "hello" && ls'),
        ("ls \\; pwd && echo test", "ls \\\\; pwd && echo test"),
        ("echo test && grep pattern \\| sort", "echo test && grep pattern \\\\| sort"),
        ("echo ${HOME} && ls \\; pwd", "echo ${HOME} && ls \\\\; pwd"),
        ('echo "$(pwd)" && cat file \\> out.txt', 'echo "$(pwd)" && cat file \\\\> out.txt'),
        ("cmd1 && cmd2 && cmd3", "cmd1 && cmd2 && cmd3"),
        ("cmd1 \\; ls && cmd2 \\| grep && cmd3", "cmd1 \\\\; ls && cmd2 \\\\| grep && cmd3"),
    ]
    for input_cmd, expected in test_cases:
        result = escape_bash_special_chars(input_cmd)
        assert result == expected, f'Failed on input "{input_cmd}"\nExpected: "{expected}"\nGot: "{result}"'
