import os
import site
import sys
from typing import List

repo_root = os.getcwd()
filtered: List[str] = []
for p in sys.path:
    if not p:
        filtered.append("")
        continue
    np = os.path.normcase(os.path.abspath(p))
    try:
        mcp_path = os.path.join(np, "mcp")
        if os.path.isdir(mcp_path) and mcp_path.startswith(repo_root):
            continue
    except Exception:
        pass
    filtered.append(p)
try:
    site_dirs = list(site.getsitepackages())
except Exception:
    site_dirs = []
try:
    user = site.getusersitepackages()
    if user:
        site_dirs.append(user)
except Exception:
    pass
for d in reversed(site_dirs):
    if d and d not in filtered:
        filtered.insert(0, d)
print("sanitized path[:10]=", filtered[:10])
