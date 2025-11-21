import ast
import re
from pathlib import Path

# Backend-focused refined orphan scan for Python.
# - Scans under forge/
# - Excludes tests, venvs, caches
# - Uses AST for robust import parsing (absolute and relative)
# - Whitelists common entrypoints and generated code

ROOT = Path("backend/forge")
EXCLUDE_DIRS = {
    "node_modules",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "tests",
    "dist",
    "build",
}

WHITELIST_PATTERNS = [
    r"^forge/server/routes/.*\.py$",  # FastAPI routes
    r"^forge/cli/.*\.py$",  # CLI entrypoints
    r"^forge/services/generated/.*\.py$",  # protobuf stubs
    r"^forge/server/(listen|app)\.py$",  # server runners
    r"^forge/core/(main|setup)\.py$",  # core entry files
    r"^forge/runtime/.*(orchestrator|watchdog|file_viewer_server)\.py$",
    r"^forge/integrations/vscode/(out|src)/.*\.(?:[jt]s|ts)$",  # VSCode extension
]


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)


def py_module_key(root: Path, p: Path) -> str:
    rel = p.relative_to(root)
    parts = list(rel.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].rsplit(".", 1)[0]
    return ".".join(parts)


def collect_py_files(root: Path):
    files = []
    for p in root.rglob("*.py"):
        if p.is_file() and not is_excluded(p):
            files.append(p)
    return files


def whitelist(path: Path) -> bool:
    s = path.as_posix()
    return any(re.match(pat, s) for pat in WHITELIST_PATTERNS)


def build_graph():
    files = collect_py_files(ROOT)
    key_to_path = {}
    inbound = {}

    # map modules
    for f in files:
        k = f"py:{py_module_key(ROOT, f)}"
        key_to_path[k] = f
        inbound.setdefault(k, set())

    # parse imports via AST (abs + relative)
    for k, f in key_to_path.items():
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text, filename=str(f))
        except Exception:
            continue

        pkg = k.split(":", 1)[1]
        pkg_base = pkg.rsplit(".", 1)[0] if "." in pkg else ""

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    mod = n.name
                    tk = f"py:{mod}"
                    if tk in key_to_path:
                        inbound[tk].add(k)
            elif isinstance(node, ast.ImportFrom):
                level = node.level or 0
                mod = node.module or ""
                if level == 0:
                    # absolute
                    target = mod
                else:
                    base_parts = pkg_base.split(".") if pkg_base else []
                    up = base_parts[:-level] if level <= len(base_parts) else []
                    target = ".".join([*up, mod] if mod else up)
                if target:
                    tk = f"py:{target}"
                    if tk in key_to_path:
                        inbound[tk].add(k)

    return inbound, key_to_path


def main():
    inbound, key_to_path = build_graph()

    candidates = []
    for k, p in key_to_path.items():
        bn = p.name
        if bn in {"__init__.py", "__main__.py"}:
            continue
        if whitelist(p):
            continue
        if not inbound.get(k):
            candidates.append(p.as_posix())

    print("Backend orphan/dead candidates (refined, tests excluded, whitelists applied):")
    for s in sorted(candidates):
        print("-", s)
    print(f"Total candidates: {len(candidates)}")


if __name__ == "__main__":
    main()


