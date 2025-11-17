import re
from pathlib import Path

text = Path(r"$env:TEMP\radon_cc_full.txt").read_text(encoding="utf8")
current = None
for line in text.splitlines():
    line = line.rstrip()
    if not line:
        continue
    if line.endswith(".py"):
        current = line.strip()
        continue
    if current is None:
        continue
    lowered = current.lower()
    if "evaluation\\benchmarks" in lowered or "evaluation/benchmarks" in lowered:
        continue
    if "\\tests\\" in lowered or "/tests/" in lowered or lowered.endswith("\\tests.py") or lowered.endswith("/tests.py"):
        continue
    if re.match(r"\s+[A-Z] \d+:\d+", line):
        print(f"{current} :: {line.strip()}")
        break
