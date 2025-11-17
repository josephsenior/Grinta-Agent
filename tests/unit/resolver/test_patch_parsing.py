"""Additional coverage for forge.resolver.patching.patch parsing helpers."""

from __future__ import annotations

from forge.resolver.patching import patch


def _first_diff(diff_text: str) -> patch.diffobj:
    """Utility to collect the first diffobj from parse_patch."""
    diffs = list(patch.parse_patch(diff_text))
    assert diffs, "Expected parse_patch to yield at least one diff"
    return diffs[0]


def test_parse_patch_git_header_normalizes_paths() -> None:
    diff_text = """\
diff --git a/src/foo.py b/src/foo.py
index 1234567..89abcde 100644
--- a/src/foo.py
+++ b/src/foo.py
@@ -1 +1 @@
-old
+new
"""
    diff = _first_diff(diff_text)

    assert diff.header.old_path == "src/foo.py"
    assert diff.header.new_path == "src/foo.py"
    assert diff.header.old_version == "1234567"
    assert diff.header.new_version == "89abcde"

    # Unified diff should record one deletion and one insertion.
    assert diff.changes is not None
    kinds = {(change.old is None, change.new is None) for change in diff.changes}
    assert (False, True) in kinds  # deletion
    assert (True, False) in kinds  # insertion


def test_parse_patch_git_rename_builds_paths_from_command_header() -> None:
    diff_text = """\
diff --git a/old_name.txt b/new_name.txt
similarity index 100%
rename from old_name.txt
rename to new_name.txt
index e69de29..b1946ac 100644
--- a/old_name.txt
+++ b/new_name.txt
"""
    diff = _first_diff(diff_text)

    assert diff.header.old_path == "old_name.txt"
    assert diff.header.new_path == "new_name.txt"
    assert diff.header.old_version == "e69de29"
    assert diff.header.new_version == "b1946ac"


def test_parse_patch_handles_new_file_from_dev_null() -> None:
    diff_text = """\
diff --git a/brand_new.txt b/brand_new.txt
new file mode 100644
index 0000000..3b18e51
--- /dev/null
+++ b/brand_new.txt
@@ -0,0 +1 @@
+hello world
"""
    diff = _first_diff(diff_text)

    assert diff.header.old_path == "/dev/null"
    assert diff.header.new_path == "brand_new.txt"
    assert diff.changes and diff.changes[0].line == "hello world"


def test_parse_patch_svn_header_converts_revision_numbers() -> None:
    diff_text = """\
Index: notes.txt
===================================================================
--- notes.txt\t(revision 123)
+++ notes.txt\t(working copy)
@@ -1 +1 @@
-todo
+done
"""
    diff = _first_diff(diff_text)

    # SVN parser should convert version strings to integers when possible.
    assert diff.header.old_path == "notes.txt"
    assert diff.header.new_path == "notes.txt"
    assert diff.header.old_version == 123
    assert diff.header.new_version is None


def test_parse_default_diff_edits() -> None:
    diff_lines = [
        "2,3c2,3",
        "< first old",
        "< second old",
        "---",
        "> first new",
        "> second new",
    ]
    changes = patch.parse_default_diff(diff_lines)

    assert changes is not None
    assert [(c.old, c.new, c.line) for c in changes] == [
        (2, None, "first old"),
        (3, None, "second old"),
        (None, 2, "first new"),
        (None, 3, "second new"),
    ]
