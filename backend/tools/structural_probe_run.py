import logging
from forge.structural import available, semantic_diff_counts

logger = logging.getLogger(__name__)
logger.info("available() %s", available())
A = "\ndef add(a, b):\n    return a + b\n\nclass C:\n    def m(self, x):\n        return x * 2\n"
B = "\ndef add(a, b):\n    # now with validation\n    assert isinstance(a, int) and isinstance(b, int)\n    return a + b\n\nclass C:\n    def m(self, x):\n        return x * 2\n\nclass D:\n    pass\n"
logger.info("semantic diff counts: %s", semantic_diff_counts(A, B))
