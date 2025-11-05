from openhands.resolver.patching.apply import apply_diff
from openhands.resolver.patching.patch import parse_patch


def test_patch_whitespace_mismatch():
    """Test that the patch application succeeds even when whitespace doesn't match."""
    original_content = "class Example:\n    def method(self):\n        pass\n\n    def another(self):\n        pass"
    patch_text = 'diff --git a/example.py b/example.py\nindex 1234567..89abcdef 100644\n--- a/example.py\n+++ b/example.py\n@@ -2,6 +2,10 @@ class Example:\n     def method(self):\n        pass\n\n+    new_field: str = "value"\n+\n     def another(self):\n        pass'
    patch = next(parse_patch(patch_text))
    new_content = apply_diff(patch, original_content)
    assert new_content == [
        "class Example:",
        "    def method(self):",
        "        pass",
        "",
        '    new_field: str = "value"',
        "",
        "    def another(self):",
        "        pass",
    ]


def test_patch_whitespace_match():
    """Test that the patch application succeeds when whitespace matches."""
    original_content = "class Example:\n    def method(self):\n        pass\n\n    def another(self):\n        pass"
    patch_text = 'diff --git a/example.py b/example.py\nindex 1234567..89abcdef 100644\n--- a/example.py\n+++ b/example.py\n@@ -2,6 +2,10 @@ class Example:\n     def method(self):\n        pass\n\n+    new_field: str = "value"\n+\n     def another(self):\n        pass'
    patch = next(parse_patch(patch_text))
    new_content = apply_diff(patch, original_content)
    assert new_content == [
        "class Example:",
        "    def method(self):",
        "        pass",
        "",
        '    new_field: str = "value"',
        "",
        "    def another(self):",
        "        pass",
    ]
