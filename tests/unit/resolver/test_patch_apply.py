from openhands.resolver.patching.apply import apply_diff
from openhands.resolver.patching.patch import diffobj, parse_diff


def test_patch_apply_with_empty_lines():
    original_content = "# PR Viewer\n\nThis React application allows you to view open pull requests from GitHub repositories in a GitHub organization. By default, it uses the All-Hands-AI organization.\n\n## Setup"
    patch = "diff --git a/README.md b/README.md\nindex b760a53..5071727 100644\n--- a/README.md\n+++ b/README.md\n@@ -1,3 +1,3 @@\n # PR Viewer\n\n-This React application allows you to view open pull requests from GitHub repositories in a GitHub organization. By default, it uses the All-Hands-AI organization.\n+This React application was created by Graham Neubig and OpenHands. It allows you to view open pull requests from GitHub repositories in a GitHub organization. By default, it uses the All-Hands-AI organization."
    print("Original content lines:")
    for i, line in enumerate(original_content.splitlines(), 1):
        print(f"{i}: {repr(line)}")
    print("\nPatch lines:")
    for i, line in enumerate(patch.splitlines(), 1):
        print(f"{i}: {repr(line)}")
    changes = parse_diff(patch)
    print("\nParsed changes:")
    for change in changes:
        print(f"Change(old={change.old}, new={change.new}, line={repr(change.line)}, hunk={change.hunk})")
    diff = diffobj(header=None, changes=changes, text=patch)
    result = apply_diff(diff, original_content)
    expected_result = [
        "# PR Viewer",
        "",
        "This React application was created by Graham Neubig and OpenHands. It allows you to view open pull requests from GitHub repositories in a GitHub organization. By default, it uses the All-Hands-AI organization.",
        "",
        "## Setup",
    ]
    assert result == expected_result
