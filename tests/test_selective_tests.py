from openhands.metasop.selective_tests import select_tests


def test_selective_empty_changes():
    out = select_tests([], repo_root=".")
    assert out == []


def test_selective_basic_imports(tmp_path):
    repo = tmp_path
    pkg = repo / "mypkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "core.py").write_text("def add(a,b):\n    return a+b\n", encoding="utf-8")
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_core.py").write_text(
        "import mypkg.core as core\n\ndef test_add():\n assert core.add(1,2)==3\n", encoding="utf-8"
    )
    out = select_tests(["mypkg/core.py"], repo_root=str(repo), mode="imports")
    assert "tests/test_core.py" in out


def test_selective_changed_mode(tmp_path):
    repo = tmp_path
    (repo / "module_a.py").write_text("x=1", encoding="utf-8")
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_module_a.py").write_text("import module_a\n", encoding="utf-8")
    out = select_tests(["module_a.py"], repo_root=str(repo), mode="changed")
    assert "tests/test_module_a.py" in out
