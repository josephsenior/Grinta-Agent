import re
from evaluation.benchmarks.testgeneval.constants import Status as TestStatus


def parse_log_pytest(log: str) -> dict[str, str]:
    """Parser for test logs generated with PyTest framework.

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    for line in log.split("\n"):
        if any((line.startswith(x.value) for x in TestStatus)):
            if line.startswith(TestStatus.FAILED.value):
                line = line.replace(" - ", " ")
            test_case = line.split()
            if len(test_case) <= 1:
                continue
            test_status_map[test_case[1]] = test_case[0]
    return test_status_map


def parse_log_pytest_options(log: str) -> dict[str, str]:
    """Parser for test logs generated with PyTest framework with options.

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    option_pattern = re.compile("(.*?)\\[(.*)\\]")
    test_status_map = {}
    for line in log.split("\n"):
        if any((line.startswith(x.value) for x in TestStatus)):
            if line.startswith(TestStatus.FAILED.value):
                line = line.replace(" - ", " ")
            test_case = line.split()
            if len(test_case) <= 1:
                continue
            if has_option := option_pattern.search(test_case[1]):
                main, option = has_option.groups()
                if (
                    option.startswith("/")
                    and (not option.startswith("//"))
                    and ("*" not in option)
                ):
                    option = "/" + option.split("/")[-1]
                test_name = f"{main}[{option}]"
            else:
                test_name = test_case[1]
            test_status_map[test_name] = test_case[0]
    return test_status_map


def parse_log_django(log: str) -> dict[str, str]:
    """Parser for test logs generated with Django tester framework.

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    lines = log.split("\n")
    prev_test = None

    for line in lines:
        line = line.strip()
        prev_test = _process_line_for_django_log(line, test_status_map, prev_test)

    _process_regex_patterns(log, test_status_map)
    return test_status_map


def _process_line_for_django_log(
    line: str, test_status_map: dict, prev_test: str | None
) -> str | None:
    """Process a single line for Django log parsing."""
    # Handle special case for version test
    if "--version is equivalent to version" in line:
        test_status_map["--version is equivalent to version"] = TestStatus.PASSED.value

    # Track previous test if line contains test separator
    if " ... " in line:
        prev_test = line.split(" ... ")[0]

    # Process different test result patterns
    _process_passed_tests(line, test_status_map)
    _process_skipped_tests(line, test_status_map)
    _process_failed_tests(line, test_status_map)
    _process_error_tests(line, test_status_map)
    _process_ok_with_prev_test(line, test_status_map, prev_test)

    return prev_test


def _process_passed_tests(line: str, test_status_map: dict) -> None:
    """Process passed test patterns."""
    pass_suffixes = (" ... ok", " ... OK", " ...  OK")
    for suffix in pass_suffixes:
        if line.endswith(suffix):
            test = _extract_test_name_for_passed(line, suffix)
            test_status_map[test] = TestStatus.PASSED.value
            break


def _extract_test_name_for_passed(line: str, suffix: str) -> str:
    """Extract test name for passed test."""
    if line.strip().startswith(
        "Applying sites.0002_alter_domain_unique...test_no_migrations"
    ):
        line = line.split("...", 1)[-1].strip()
    return line.rsplit(suffix, 1)[0]


def _process_skipped_tests(line: str, test_status_map: dict) -> None:
    """Process skipped test patterns."""
    if " ... skipped" in line:
        test = line.split(" ... skipped")[0]
        test_status_map[test] = TestStatus.SKIPPED.value


def _process_failed_tests(line: str, test_status_map: dict) -> None:
    """Process failed test patterns."""
    if line.endswith(" ... FAIL"):
        test = line.split(" ... FAIL")[0]
        test_status_map[test] = TestStatus.FAILED.value
    elif line.startswith("FAIL:"):
        test = line.split()[1].strip()
        test_status_map[test] = TestStatus.FAILED.value


def _process_error_tests(line: str, test_status_map: dict) -> None:
    """Process error test patterns."""
    if line.endswith(" ... ERROR"):
        test = line.split(" ... ERROR")[0]
        test_status_map[test] = TestStatus.ERROR.value
    elif line.startswith("ERROR:"):
        test = line.split()[1].strip()
        test_status_map[test] = TestStatus.ERROR.value


def _process_ok_with_prev_test(
    line: str, test_status_map: dict, prev_test: str | None
) -> None:
    """Process 'ok' pattern with previous test."""
    if line.lstrip().startswith("ok") and prev_test is not None:
        test_status_map[prev_test] = TestStatus.PASSED.value


def _process_regex_patterns(log: str, test_status_map: dict) -> None:
    """Process regex patterns for additional test matches."""
    patterns = [
        r"^(.*?)\s\.\.\.\sTesting\sagainst\sDjango\sinstalled\sin\s((?s:.*?))\ssilenced\)\.\nok$",
        r"^(.*?)\s\.\.\.\sInternal\sServer\sError:\s\/(.*)\/\nok$",
        r"^(.*?)\s\.\.\.\sSystem\scheck\sidentified\sno\sissues\s\(0\ssilenced\)\nok$",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, log, re.MULTILINE):
            test_name = match.group(1)
            test_status_map[test_name] = TestStatus.PASSED.value


def parse_log_pytest_v2(log: str) -> dict[str, str]:
    """Parser for test logs generated with PyTest framework (Later Version).

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    escapes = "".join([chr(char) for char in range(1, 32)])
    for line in log.split("\n"):
        line = re.sub("\\[(\\d+)m", "", line)
        translator = str.maketrans("", "", escapes)
        line = line.translate(translator)
        if any((line.startswith(x.value) for x in TestStatus)):
            if line.startswith(TestStatus.FAILED.value):
                line = line.replace(" - ", " ")
            test_case = line.split()
            if len(test_case) >= 2:
                test_status_map[test_case[1]] = test_case[0]
        elif any((line.endswith(x.value) for x in TestStatus)):
            test_case = line.split()
            if len(test_case) >= 2:
                test_status_map[test_case[0]] = test_case[1]
    return test_status_map


def parse_log_seaborn(log: str) -> dict[str, str]:
    """Parser for test logs generated with seaborn testing framework.

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    for line in log.split("\n"):
        if line.startswith(TestStatus.FAILED.value):
            test_case = line.split()[1]
            test_status_map[test_case] = TestStatus.FAILED.value
        elif f" {TestStatus.PASSED.value} " in line:
            parts = line.split()
            if parts[1] == TestStatus.PASSED.value:
                test_case = parts[0]
                test_status_map[test_case] = TestStatus.PASSED.value
        elif line.startswith(TestStatus.PASSED.value):
            parts = line.split()
            test_case = parts[1]
            test_status_map[test_case] = TestStatus.PASSED.value
    return test_status_map


def parse_log_sympy(log: str) -> dict[str, str]:
    """Parser for test logs generated with Sympy framework.

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    pattern = "(_*) (.*)\\.py:(.*) (_*)"
    matches = re.findall(pattern, log)
    for match in matches:
        test_case = f"{match[1]}.py:{match[2]}"
        test_status_map[test_case] = TestStatus.FAILED.value
    for line in log.split("\n"):
        line = line.strip()
        if line.startswith("test_"):
            if line.endswith("[FAIL]") or line.endswith("[OK]"):
                line = line[: line.rfind("[")]
                line = line.strip()
            if line.endswith(" E"):
                test = line.split()[0]
                test_status_map[test] = TestStatus.ERROR.value
            if line.endswith(" F"):
                test = line.split()[0]
                test_status_map[test] = TestStatus.FAILED.value
            if line.endswith(" ok"):
                test = line.split()[0]
                test_status_map[test] = TestStatus.PASSED.value
    return test_status_map


def parse_log_matplotlib(log: str) -> dict[str, str]:
    """Parser for test logs generated with PyTest framework.

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    for line in log.split("\n"):
        line = line.replace("MouseButton.LEFT", "1")
        line = line.replace("MouseButton.RIGHT", "3")
        if any((line.startswith(x.value) for x in TestStatus)):
            if line.startswith(TestStatus.FAILED.value):
                line = line.replace(" - ", " ")
            test_case = line.split()
            if len(test_case) <= 1:
                continue
            test_status_map[test_case[1]] = test_case[0]
    return test_status_map


parse_log_astroid = parse_log_pytest
parse_log_flask = parse_log_pytest
parse_log_marshmallow = parse_log_pytest
parse_log_pvlib = parse_log_pytest
parse_log_pyvista = parse_log_pytest
parse_log_sqlfluff = parse_log_pytest
parse_log_xarray = parse_log_pytest
parse_log_pydicom = parse_log_pytest_options
parse_log_requests = parse_log_pytest_options
parse_log_pylint = parse_log_pytest_options
parse_log_astropy = parse_log_pytest_v2
parse_log_scikit = parse_log_pytest_v2
parse_log_sphinx = parse_log_pytest_v2
MAP_REPO_TO_PARSER = {
    "astropy/astropy": parse_log_astropy,
    "django/django": parse_log_django,
    "marshmallow-code/marshmallow": parse_log_marshmallow,
    "matplotlib/matplotlib": parse_log_matplotlib,
    "mwaskom/seaborn": parse_log_seaborn,
    "pallets/flask": parse_log_flask,
    "psf/requests": parse_log_requests,
    "pvlib/pvlib-python": parse_log_pvlib,
    "pydata/xarray": parse_log_xarray,
    "pydicom/pydicom": parse_log_pydicom,
    "pylint-dev/astroid": parse_log_astroid,
    "pylint-dev/pylint": parse_log_pylint,
    "pytest-dev/pytest": parse_log_pytest,
    "pyvista/pyvista": parse_log_pyvista,
    "scikit-learn/scikit-learn": parse_log_scikit,
    "sqlfluff/sqlfluff": parse_log_sqlfluff,
    "sphinx-doc/sphinx": parse_log_sphinx,
    "sympy/sympy": parse_log_sympy,
}
