# Refactor baseline metrics

Generated from the current tree on **2026-08-11**. This is a navigation aid,
not an architectural contract; line counts change continuously.

## Largest production Python modules

Tests and generated files are excluded.

| Lines | Module |
| ---: | --- |
| 1,555 | `backend/cli/tui/widgets/scan_line/cards.py` |
| 1,393 | `backend/context/prompt/prompt_window.py` |
| 1,314 | `backend/execution/aes/helpers.py` |
| 1,270 | `backend/context/memory/conversation_memory.py` |
| 1,264 | `backend/execution/aes/file_operations.py` |
| 1,250 | `backend/context/compactor/pre_condensation_snapshot.py` |
| 1,177 | `backend/inference/catalog/catalog_loader.py` |
| 1,173 | `backend/utils/lsp/lsp_client.py` |
| 1,165 | `backend/integrations/mcp/mcp_utils.py` |
| 1,144 | `backend/engine/executor_mixins/_executor_streaming_mixin.py` |
| 1,132 | `backend/ledger/stream/event_stream.py` |
| 1,098 | `backend/execution/server/base.py` |
| 1,097 | `backend/engine/planner.py` |
| 1,039 | `backend/execution/io_mixins/_aes_io_terminal_mixin.py` |
| 1,028 | `backend/utils/runtime_detect.py` |

Large modules are review signals, not automatic split requirements. Check
public imports in `docs/internals/import-manifest.json` before moving symbols.

## Refresh command

```powershell
$rows = Get-ChildItem backend -Recurse -Filter *.py |
  Where-Object { $_.FullName -notmatch '[\\/]tests[\\/]' } |
  ForEach-Object {
    [pscustomobject]@{
      Lines = (Get-Content -LiteralPath $_.FullName).Count
      Path = (Resolve-Path -Relative $_.FullName) -replace '^.\\', ''
    }
  }
$rows | Sort-Object Lines -Descending | Select-Object -First 20
```

For current package boundaries, use [ARCHITECTURE.md](ARCHITECTURE.md) and
[CONTRIBUTOR_MAP.md](CONTRIBUTOR_MAP.md), not older refactor plans.
