"""Small probe to exercise the structural wrapper."""

import logging
from forge.structural import available, semantic_diff_counts

logger = logging.getLogger(__name__)
A = "\ndef add(a, b):\n    return a + b\n\nclass C:\n    def m(self, x):\n        return x * 2\n"
B = "\ndef add(a, b):\n    # now with validation\n    assert isinstance(a, int) and isinstance(b, int)\n    return a + b\n\nclass C:\n    def m(self, x):\n        return x * 2\n\nclass D:\n    pass\n"
if __name__ == "__main__":
    if not available():
        logger.error("tree-sitter bindings not available; structural probe cannot run")
    else:
        d = semantic_diff_counts(A, B)
        logger.info("semantic diff counts: %s", d)
