Phase 2: Structural Intelligence & Autonomy - Overview

Goals

- Add semantic structural diff classification using Tree-sitter to better understand
  code edits (AST-level diffs), enabling test targeting and stagnation heuristics.
- Implement memory entry scoring with periodic compaction to keep memory relevant
  and small.
- Introduce reflection artifacts so the orchestrator can pivot strategies when
  repeated failure taxonomy labels appear.

Planned Workstreams

1. Third-party setup
   - Use `third_party/third_party_fetch.ps1` to fetch Tree-sitter, py-tree-sitter,
     language grammar(s), and an ANN library (Annoy) for memory compaction.
2. Tree-sitter integration
   - Add a small `Forge/structural` package that wraps py-tree-sitter and
     provides AST extraction, AST-diff, and small semantic classifiers.
   - Start with `tree-sitter-python` grammar for Python projects.
3. Memory improvements
   - Add scoring for MemoryIndex entries (freshness, relevance, patch-success signals).
   - Add periodic compaction: keep top-k by score, evict the rest; expose config.
4. Reflection & strategy pivot
   - Emit a `reflection` artifact when repeated failure types are detected (configurable threshold).
   - Reflection should contain: failure taxonomy summary, candidate fingerprints, suggested strategy (e.g., "switch to mutation QA slow mode", "increase candidates"), and a small plan.

Next actions (I can take them now)

- Run the fetch script to clone required OSS into `third_party/`.
- Create scaffolding `Forge/structural` with minimal Tree-sitter wrappers and unit tests.
- Implement a MemoryIndex scoring prototype and compaction API.

If you want me to proceed, I'll run the fetch script next (PowerShell). If you'd prefer I clone different tags or add other OSS, tell me which tags or repos to include.

Build notes:

- Building Tree-sitter language shared libraries requires a C compiler and
  the py-tree-sitter `Language.build_library` API or running a platform
  compiler. On Windows you should have Visual Studio Build Tools or MinGW
  installed; on macOS Xcode command line tools; on Linux, gcc/clang.

I attempted an automatic build in this environment but the installed
py-tree-sitter variant did not expose the `build_library` helper. If you
want me to attempt a local build, please confirm that a C build toolchain
is installed (and whether you prefer MSVC or MinGW on Windows). Alternatively
I can provide prebuilt binaries for common platforms or document the exact
steps to run locally.
