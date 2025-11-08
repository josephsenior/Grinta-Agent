# Permissive Declaration Shims Report

Scanned declaration files that look like permissive shims to tighten. These are prioritized to minimize breakage.

Found candidate files:

- `types/local-plugins.d.ts` — wildcard JS/MJS shims and a catch-all module pattern. (low-risk to tighten)
- `frontend/types/forge-types-shim.d.ts` — intentionally permissive shim for `#/api/forge.types` exported types as `any`. (high-impact; many imports)
- `frontend/src/types/aliases.d.ts` — defines `declare module "#/*" { const value: any }` wildcard used across repo. (very high-impact)
- `types/vitest-shims.d.ts` — permissive `any` exports for vitest runtime. (low-risk to improve)
- `frontend/src/types/ambient/testing.d.ts`, `frontend/src/types/react-query.d.ts`, `frontend/src/types/file-icons-js.d.ts`, etc. — smaller ambient shims to inspect.
- `frontend/global.d.ts` and `vite-env.d.ts` — already narrow and OK.

Recommended prioritized plan (incremental, low-risk first):

1. Scan and create this report (done).
2. Tighten low-risk shims:
   - Make `types/local-plugins.d.ts` explicit (export `unknown` instead of unnamed module, add `export default` shape) and add a short comment to require explicit casts when used.
   - Make `types/vitest-shims.d.ts` slightly more precise by using `unknown` or specific exported types where feasible.
   - Ensure asset module declarations (e.g. `*.png`) are present (they already are in `frontend/global.d.ts`).
3. Run `npx tsc --noEmit -p frontend` after each change.
4. Tackle `#/api/forge.types` (high-impact):
   - Identify top-used types (Conversation, GetConfigResponse, GitChange, Branch) via grep.
   - Add minimal, focused interfaces for those types (only include properties the code accesses) to replace `any` progressively.
   - Re-run tsc and fix consumer files with narrow, local casting or small type adapations if necessary.
5. Replace wildcard `declare module "#/*"` with narrower patterns where possible (e.g., `#/components/*`, `#/api/*`, `#/hooks/*`) and let TypeScript resolve explicitly typed modules.
6. Repeat and iterate until the wildcard/permissive shims are minimized.

Next low-risk step I can do now (automatic):
- Update `types/local-plugins.d.ts` to export modules with `export default unknown` + short JSDoc comment so consumers must cast to expected shape (this is a safe tightening that rarely creates new errors).
- Update `types/vitest-shims.d.ts` to replace broad `any` with `unknown` for `Mock` and keep runtime helpers typed as `any` only if needed.

If you want, I'll apply those low-risk changes now and run `npx tsc --noEmit -p frontend` after each edit. Otherwise I can start with a targeted tightening of `#/api/forge.types` instead.
