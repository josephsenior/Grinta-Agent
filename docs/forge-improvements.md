# Forge Improvements

## Recent Changes

### 1. Prompt Optimization
- **Before:** 1,065 lines
- **After:** 166 lines (84% reduction)
- **Why:** Simpler prompts = better LLM performance (research-backed)
- **Result:** Clearer instructions, fewer conflicts, faster execution

### 2. Language Support Expansion
- **Before:** 26 languages
- **After:** 45+ languages
- **Added:** Lua, Dart, Haskell, Elixir, Zig, Nim, Vue, Svelte, F#, Perl, R, GraphQL, and more
- **File:** `openhands/agenthub/codeact_agent/tools/universal_editor.py`

### 3. Production Deployment Fixes
- **Tree-sitter:** Now required (was optional)
- **Health checks:** Startup validation for critical dependencies
- **Error messages:** Production-focused with clear fix instructions
- **Files:** `pyproject.toml`, `health_check.py`, `codeact_agent.py`

### 4. UI Improvements
- **Streaming:** Character-by-character (ChatGPT-style)
- **Message grouping:** Agent responses in one bubble
- **Empty bubbles:** Fixed null/empty message rendering
- **Files:** `frontend/src/components/features/chat/*.tsx`

### 5. Bug Fixes
- **File creation:** Agent now uses correct tool (`str_replace_editor` for new files)
- **Runtime crashes:** Fixed ProcessManager `pkill` bug
- **Error recovery:** Auto-recovery from ERROR state to READY
- **Streaming errors:** Null safety checks for failed LLM streams

## Files Modified

**Backend:**
- `pyproject.toml` - Dependencies
- `openhands/agenthub/codeact_agent/tools/universal_editor.py` - Language support
- `openhands/agenthub/codeact_agent/tools/health_check.py` - NEW startup validation
- `openhands/agenthub/codeact_agent/codeact_agent.py` - Health check integration
- `openhands/agenthub/codeact_agent/prompts/system_prompt_forge.j2` - Optimized prompt

**Frontend:**
- `frontend/src/utils/coalesce-messages.ts` - Disabled batching for real-time streaming
- `frontend/src/components/features/chat/chat-message.tsx` - Faster animation
- `frontend/src/components/features/chat/event-message.tsx` - Fixed empty bubbles, enabled streaming
- `frontend/src/components/features/chat/messages.tsx` - Message grouping
- `frontend/src/context/ws-client-provider.tsx` - Auto-recovery system
- `frontend/src/state/agent-slice.tsx` - State management

## Testing

Run health check:
```bash
python openhands/agenthub/codeact_agent/tools/health_check.py
```

Expected output:
```
✅ ultimate_editor [CRITICAL]: PASS
✅ atomic_refactor: PASS
🎯 OVERALL: HEALTHY
```

## Deployment

1. Rebuild dependencies: `poetry install`
2. Restart services: `docker-compose restart`
3. Verify logs show health check passing

## See Also

- [ultimate-editor.md](./ultimate-editor.md) - Editor guide
- [production-setup.md](./production-setup.md) - Deployment guide

