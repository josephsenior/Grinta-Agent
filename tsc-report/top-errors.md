# Top TypeScript Errors — Prioritized Triage

Summary
- **Repo tsc run:** `npx tsc --noEmit` reported ~11,339 errors across ~734 files.
- **Purpose:** prioritized list of the top-200 files by error count and suggested first-fix actions to reduce noise quickly.

Key Observations
- **High-frequency causes:** missing JSX config for .tsx files, ESM import extension errors (TS2835), alias resolution/type export mismatches for `#/*` paths, and missing declaration files for local `.js`/`.mjs` plugins.
- **Quick wins:** adjust TypeScript config boundaries (exclude frontend from root or ensure frontend `tsconfig.json` is the authoritative one for frontend files), add a few local `.d.ts` shims for untyped local JS modules, and install a small set of missing `@types/*` / framework types (Playwright, Vitest) where appropriate.

Suggested Next Steps (short list)
- **1) Create the human-readable triage (this file):** identify top files — completed.
- **2) Apply config-level quick fixes:** exclude `frontend` from root `tsconfig.json` or ensure root config has `jsx` + `paths` consistent; add `skipLibCheck: true` during triage to reduce noise.
- **3) Add small declaration shims:** add `types/local-plugins.d.ts` for local untyped `.js` modules and include it in `include`.
- **4) Install missing types:** `npm i -D @playwright/test @types/react @types/react-dom` and any other missing package types.
- **5) Re-run `npx tsc --noEmit` and iterate on highest-impact files.

Top 20 Files — Suggested First Fix

- **1) `frontend/src/components/features/orchestration/clean-visualizations.tsx` — 374 errors:**
  - Suggestion: ensure this file is compiled under the frontend `tsconfig` (which has `jsx` configured). If full-repo `tsc` is needed, set `jsx` in root `tsconfig` or exclude frontend from root `tsc` and only run `tsc -p frontend` for frontend checks. Also check for imports of untyped JS plugins and add `.d.ts` shims or explicit types.

- **2) `frontend/src/routes/snippets-settings.tsx` — 170 errors:**
  - Suggestion: same as above — likely JSX/TSX flags or missing React types; add `@types/react` / ensure `jsx` is set.

- **3) `frontend/src/components/features/orchestration/modern-flow-diagram.tsx` — 143 errors:**
  - Suggestion: likely imports of diagram/mermaid modules requiring `.mjs` extension or missing types. Add `declare module` for those packages or install types and add extensions where necessary.

- **4) `frontend/src/routes/pricing.tsx` — 141 errors:**
  - Suggestion: JSX flag + React types; ensure file is included in frontend tsconfig only.

- **5) `frontend/src/components/landing/HeroSection.tsx` — 136 errors:**
  - Suggestion: JSX configuration and missing `@types/react` / `@types/react-dom`.

- **6) `frontend/src/components/shared/demo/loading-demo.tsx` — 117 errors:**
  - Suggestion: test-related typings or JSX; ensure tests are covered by frontend tsconfig and vitest types are installed.

- **7) `frontend/src/components/landing/MetaSOPShowcase.tsx` — 106 errors:**
  - Suggestion: JSX + missing types or import alias resolution — verify `paths` mapping and `baseUrl` in tsconfig.

- **8) `frontend/src/components/features/chat/chat-interface.tsx` — 105 errors:**
  - Suggestion: check `#/*` path alias resolution; ensure the `paths` in root tsconfig are visible to frontend tsc or consolidate aliases.

- **9) `frontend/src/routes/analytics-settings.tsx` — 100 errors:**
  - Suggestion: JSX + missing types; add React types and verify frontend `tsconfig`.

- **10) `frontend/src/components/features/orchestration/orchestration-diagram-panel.tsx` — 98 errors:**
  - Suggestion: diagram library types or import extension issues; add shims or explicit file extensions in ESM imports.

- **11) `frontend/src/routes/changes-tab.backup.tsx` — 95 errors:**
  - Suggestion: ensure backups are intended to be typechecked — if not, exclude `*.backup.tsx` patterns.

- **12) `frontend/src/components/landing/ValueProposition.tsx` — 94 errors:**
  - Suggestion: JSX / React types.

- **13) `frontend/src/routes/slack-settings.tsx` — 93 errors:**
  - Suggestion: missing types for Slack SDK or alias resolution. Install Slack SDK types or add shims.

- **14) `frontend/src/routes/llm-settings.tsx` — 91 errors:**
  - Suggestion: React/JSX + missing types for any imported local modules.

- **15) `frontend/src/routes/root-layout.tsx` — 88 errors:**
  - Suggestion: JSX + route-level imports; ensure `@types/react-router` / router types installed if used.

- **16) `frontend/src/components/features/settings/mcp-settings/mcp-marketplace-details-modal.tsx` — 83 errors:**
  - Suggestion: the file may import remote modules or local JS helpers; add `.d.ts` shims and ensure JSX settings.

- **17) `frontend/src/components/features/conversation-panel/conversation-card.tsx` — 82 errors:**
  - Suggestion: React/JSX + path alias checks.

- **18) `frontend/src/components/features/chat/event-message.tsx` — 81 errors:**
  - Suggestion: JSX + missing types for event/message payload shapes — consider adding lightweight interfaces as a first step.

- **19) `frontend/__tests__/routes/llm-settings.test.tsx` — 81 errors:**
  - Suggestion: test runner types (Vitest/Playwright) are missing or misconfigured. Install `vitest` types and add `types` to the test tsconfig.

- **20) `frontend/src/routes/memory-settings.tsx` — 75 errors:**
  - Suggestion: JSX + type imports; confirm `paths` and `baseUrl` for alias resolution.

General remediation ideas for the rest of the top files
- Many of the remaining high-error files are frontend TSX components and tests. The most effective early actions are:
  - **A)** Ensure frontend files are typechecked only by the frontend `tsconfig.json` (either exclude `frontend` in root tsconfig or make frontend the only tsconfig that includes these files).
  - **B)** Add `jsx: "react-jsx"` and React types (`@types/react`, `@types/react-dom`) to the environment if missing.
  - **C)** Install test framework types: `vitest`, `@types/testing-library__react`, `@playwright/test` where used.
  - **D)** Add small declaration shims for local untyped JS modules: create `types/local-plugins.d.ts` with `declare module '*.js'; declare module '*.mjs';` and include it in tsconfig `include`.
  - **E)** Consider `skipLibCheck: true` during triage to reduce cascading third-party type issues.

Top-200 files (raw counts)
```
374 frontend/src/components/features/orchestration/clean-visualizations.tsx
170 frontend/src/routes/snippets-settings.tsx
143 frontend/src/components/features/orchestration/modern-flow-diagram.tsx
141 frontend/src/routes/pricing.tsx
136 frontend/src/components/landing/HeroSection.tsx
117 frontend/src/components/shared/demo/loading-demo.tsx
106 frontend/src/components/landing/MetaSOPShowcase.tsx
105 frontend/src/components/features/chat/chat-interface.tsx
100 frontend/src/routes/analytics-settings.tsx
98 frontend/src/components/features/orchestration/orchestration-diagram-panel.tsx
95 frontend/src/routes/changes-tab.backup.tsx
94 frontend/src/components/landing/ValueProposition.tsx
93 frontend/src/routes/slack-settings.tsx
91 frontend/src/routes/llm-settings.tsx
88 frontend/src/routes/root-layout.tsx
83 frontend/src/components/features/settings/mcp-settings/mcp-marketplace-details-modal.tsx
82 frontend/src/components/features/conversation-panel/conversation-card.tsx
81 frontend/src/components/features/chat/event-message.tsx
81 frontend/__tests__/routes/llm-settings.test.tsx
75 frontend/src/routes/memory-settings.tsx
73 frontend/__tests__/components/features/microagent-management/microagent-management.test.tsx
70 frontend/src/components/features/chat/chat-interface-refactored.tsx
69 frontend/src/routes/prompts-settings.tsx
67 frontend/src/routes/workspace-tab.tsx
66 frontend/src/components/features/orchestration/mermaid-diagram-viewer.tsx
65 frontend/src/components/features/settings/api-keys-manager.tsx
65 frontend/__tests__/routes/secrets-settings.test.tsx
63 frontend/src/components/features/chat/chat-interface-demo.tsx
63 frontend/src/components/features/prompts/prompt-form-modal.tsx
62 frontend/src/entry.client.tsx
62 frontend/src/components/features/chat/streaming-controls.tsx
62 frontend/src/components/features/chat/interactive-chat-box.tsx
62 frontend/src/components/features/file-explorer/file-explorer.tsx
61 frontend/src/components/features/settings/database-connections/database-connection-form.tsx
60 frontend/src/routes/backup-settings.tsx
59 frontend/src/components/features/knowledge-base/knowledge-base-manager.tsx
58 frontend/src/components/features/chat/streaming-demo.tsx
58 frontend/src/components/landing/InteractiveDemoSection.tsx
57 frontend/src/components/features/chat/messages.tsx
57 frontend/src/components/features/chat/conversation-search.tsx
56 frontend/src/components/features/monitoring/autonomous-monitor.tsx
56 frontend/src/components/features/settings/mcp-settings/mcp-marketplace.tsx
54 frontend/src/components/shared/modals/security/invariant/invariant.tsx
52 frontend/src/components/features/settings/advanced-llm-config.tsx
51 frontend/src/components/layout/Footer.tsx
50 frontend/src/components/features/file-explorer/file-viewer.tsx
50 frontend/src/components/features/chat/empty-state.tsx
49 frontend/src/components/layout/Header.tsx
49 frontend/src/components/features/file-explorer/file-management-panel.tsx
49 frontend/src/components/shared/error/user-friendly-error.tsx
49 frontend/src/components/features/chat/modern-chat-message.tsx
48 frontend/src/components/landing/Header.tsx
48 frontend/src/components/landing/Footer.tsx
47 frontend/src/routes/git-settings.tsx
47 frontend/src/components/features/memory/memory-form-modal.tsx
47 frontend/src/routes/app-settings.tsx
46 frontend/src/components/features/files/file-preview-modal.tsx
46 frontend/src/components/features/chat/conversation-bookmarks.tsx
46 frontend/src/components/features/chat/keyboard-shortcuts-panel.tsx
45 frontend/src/routes/conversation.tsx
45 frontend/src/components/features/chat/modern-chat-interface.tsx
45 frontend/src/components/features/settings/project-management/configure-modal.tsx
45 frontend/src/components/features/settings/mcp-settings/mcp-marketplace-card.tsx
45 frontend/src/components/features/conversation-panel/conversation-panel.tsx
44 frontend/src/components/landing/FeaturesGrid.tsx
43 frontend/src/components/features/conversation-panel/microagents-modal.tsx
43 frontend/src/components/features/database-browser/query-results.tsx
42 frontend/src/components/features/chat/smart-suggestions.tsx
42 frontend/src/components/features/microagent-management/microagent-management-content.tsx
41 frontend/src/components/features/settings/autonomy-settings.tsx
41 frontend/src/routes/database-settings.tsx
41 frontend/src/components/features/conversation-panel/system-message-modal.tsx
41 frontend/src/components/features/chat/streaming-code-artifact.tsx
40 frontend/src/components/features/analytics/model-usage-table.tsx
40 frontend/src/components/shared/SkeletonCard.tsx
39 frontend/src/components/features/settings/mcp-settings/mcp-config-viewer.tsx
39 frontend/src/components/features/database-browser/schema-browser.tsx
39 frontend/src/components/features/prompts/prompt-card.tsx
38 frontend/src/routes/home.tsx
38 frontend/src/components/features/progress/progress-indicator.tsx
38 frontend/__tests__/components/features/conversation-panel/conversation-card.test.tsx
37 frontend/src/routes/mcp-settings.tsx
37 frontend/src/components/shared/loading/skeleton-loader.tsx
36 frontend/src/routes/database-browser.tsx
36 frontend/src/components/shared/loading/enhanced-skeleton-loader.tsx
36 frontend/src/context/ws-client-provider.tsx
35 frontend/src/components/features/monitoring/enhanced-audit-trail.tsx
35 frontend/src/components/features/chat/microagent/launch-microagent-modal.tsx
35 frontend/src/components/features/chat/code-artifact.tsx
35 frontend/src/components/features/beta/inline-llm-setup.tsx
35 frontend/src/components/features/chat/modern-chat-input.tsx
34 frontend/src/components/features/chat/streaming-chat-message.tsx
34 frontend/src/components/landing/TestimonialsSection.tsx
34 frontend/src/components/features/microagent-management/microagent-management-upsert-microagent-modal.tsx
33 frontend/__tests__/components/features/home/repo-connector.test.tsx
33 frontend/src/routes/secrets-settings.tsx
33 frontend/src/components/landing/FinalCTA.tsx
33 frontend/src/components/features/prompts/__tests__/prompt-card.test.tsx
33 frontend/src/components/features/browser/interactive-browser.tsx
33 frontend/src/components/features/microagent-management/microagent-management-sidebar.tsx
33 frontend/src/components/features/chat/streaming-typing-indicator.tsx
32 frontend/src/components/features/chat/microagent/microagent-status-toast.tsx
31 frontend/src/components/features/settings/database-connections/database-connections-list.tsx
31 frontend/src/components/shared/inputs/custom-dropdown.tsx
31 frontend/src/components/features/task-panel/task-panel.tsx
31 frontend/__tests__/routes/app-settings.test.tsx
30 frontend/__tests__/components/landing-translations.test.tsx
30 frontend/src/components/features/settings/mcp-settings/mcp-server-form.tsx
30 frontend/src/components/features/chat/expandable-message.tsx
30 frontend/__tests__/components/chat/chat-input.test.tsx
30 frontend/__tests__/routes/git-settings.test.tsx
30 frontend/src/routes/contact.tsx
29 frontend/src/context/__tests__/theme-context.test.tsx
29 frontend/src/routes/__tests__/slack-settings.test.tsx
28 frontend/src/components/features/settings/mcp-settings/__tests__/mcp-marketplace-card.test.tsx
28 frontend/src/components/features/memory/memory-card.tsx
28 frontend/src/components/features/prompts/__tests__/prompt-form-modal.test.tsx
28 frontend/src/components/features/knowledge-base/kb-collection-card.tsx
28 frontend/__tests__/components/features/conversation-panel/conversation-panel.test.tsx
28 frontend/src/components/features/markdown/enhanced-code.tsx
27 frontend/src/components/features/settings/secrets-settings/secret-form.tsx
27 frontend/src/components/features/markdown/streaming-code.tsx
27 frontend/src/components/features/knowledge-base/kb-document-upload.tsx
27 frontend/src/routes/conversations-list.tsx
26 frontend/src/components/features/conversation-panel/conversation-card-context-menu.tsx
26 frontend/src/routes/user-settings.tsx
26 frontend/src/components/features/microagent-management/microagent-management-repo-microagents.tsx
26 frontend/src/routes/about.tsx
26 frontend/src/components/features/chat/chat-message.tsx
26 frontend/src/components/features/diff-viewer/file-diff-viewer.tsx
26 frontend/__tests__/routes/home-screen.test.tsx
26 frontend/src/components/features/terminal/streaming-terminal.tsx
26 frontend/src/components/features/chat/message-skeleton.tsx
26 frontend/src/components/features/terminal/streaming-terminal-clean.tsx
25 frontend/src/components/features/chat/streaming-thought.tsx
25 frontend/src/components/shared/command-console/command-console.tsx
25 frontend/__tests__/components/chat/chat-interface.test.tsx
25 frontend/src/components/features/microagent-management/microagent-management-learn-this-repo-modal.tsx
25 frontend/src/components/features/monitoring/command-blocking-card.tsx
25 frontend/src/components/features/waitlist/auth-modal.tsx
25 frontend/src/components/ui/theme-toggle.tsx
24 frontend/src/components/shared/modals/settings/settings-form.tsx
24 frontend/src/components/shared/card-skeleton.tsx
23 frontend/src/components/features/feedback/feedback-form.tsx
23 frontend/src/components/shared/modals/settings/settings-modal.tsx
23 frontend/src/components/features/knowledge-base/kb-create-collection-modal.tsx
23 frontend/src/components/shared/error-boundaries/GlobalErrorBoundary.tsx
22 frontend/src/components/SkeletonLoader.tsx
22 frontend/src/context/conversation-subscriptions-provider.tsx
22 frontend/src/components/features/chat/error-message-banner.tsx
22 frontend/src/components/features/controls/autonomy-mode-selector.tsx
22 frontend/src/routes/terms.tsx
22 frontend/src/components/features/analytics/cost-chart.tsx
22 frontend/src/components/features/beta/runtime-loading-screen.tsx
22 frontend/src/components/shared/error/error-boundary.tsx
22 frontend/src/routes/privacy.tsx
22 frontend/src/components/features/payment/payment-form.tsx
22 frontend/src/components/features/diff-viewer/streaming-file-viewer.tsx
21 frontend/src/components/features/conversation-panel/confirm-delete-modal.tsx
21 frontend/src/components/shared/notifications/toast.tsx
21 frontend/src/components/landing/SimpleHowItWorks.tsx
21 frontend/src/components/features/home/git-repo-dropdown/git-repo-dropdown.tsx
21 frontend/src/components/shared/modals/settings/model-selector.tsx
21 frontend/src/main.tsx
21 frontend/src/api/open-hands.ts
20 frontend/src/components/features/home/git-branch-dropdown/git-branch-dropdown.tsx
20 frontend/src/components/features/settings/settings-error-boundary.tsx
20 frontend/src/components/features/settings/mcp-settings/mcp-marketplace-stats.tsx
20 frontend/src/routes/settings.tsx
20 frontend/src/components/features/memory/__tests__/memory-card.test.tsx
20 frontend/src/hooks/query/use-prompts.ts
19 frontend/src/components/shared/buttons/confirmation-buttons.tsx
19 frontend/src/components/features/home/git-provider-dropdown/git-provider-dropdown.tsx
19 frontend/src/components/features/controls/autonomy-mode-demo.tsx
19 frontend/src/components/features/home/tasks/task-suggestions.tsx
19 frontend/src/components/landing/AnimatedBackground.tsx
19 frontend/src/components/features/chat/mcp-observation-content.tsx
19 frontend/src/components/features/chat/__tests__/streaming-thought.test.tsx
19 frontend/src/components/shared/terminal-snippet/terminal-snippet.tsx
18 frontend/src/components/features/settings/create-api-key-modal.tsx
18 frontend/src/components/features/microagent-management/microagent-management-repositories.tsx
18 frontend/src/components/shared/loading/loading-state.tsx
18 frontend/src/components/ui/dropdown-menu.tsx
18 frontend/src/components/features/feedback/likert-scale.tsx
18 frontend/@/components/ui/dropdown-menu.tsx
18 frontend/src/hooks/query/use-snippets.ts
18 frontend/__tests__/routes/_oh.test.tsx
17 frontend/src/components/shared/error-boundaries/ChatErrorBoundary.tsx
17 frontend/src/components/features/settings/mcp-settings/mcp-stdio-servers.tsx
17 frontend/src/components/layout/tab-content.tsx
17 frontend/__tests__/components/interactive-chat-box.test.tsx
17 frontend/__tests__/hooks/use-terminal.test.tsx
17 frontend/src/components/landing/BetaFAQ.tsx
16 frontend/src/routes/vscode-tab.tsx
16 frontend/src/components/features/chat/action-suggestions.tsx
16 frontend/src/components/features/chat/typing-indicator.tsx
16 frontend/src/components/features/chat/__tests__/ChatInterface.test.tsx
16 frontend/src/components/features/analytics/analytics-consent-form-modal.tsx
16 frontend/tests/conversation-panel.test.ts
16 frontend/__tests__/components/user-actions.test.tsx
```

If you'd like, I can now:
- **A)** Commit this report and open a PR with a small set of config changes (exclude frontend from root tsc, add a local `types/local-plugins.d.ts`) to immediately reduce noise.
- **B)** Start implementing the first-fix for the top 10 files (apply the JSX/type fixes and add shims where necessary).
- **C)** Produce a narrower follow-up report with the top 20 files and the most frequent TS error codes per-file.

Choose A, B, or C (or give different next steps) and I will proceed.
