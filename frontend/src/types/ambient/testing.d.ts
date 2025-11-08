// Ambient types for test and Playwright E2E globals used in the frontend tests
export {};

declare global {
  interface Window {
    __Forge_PLAYWRIGHT?: boolean;
    __Forge_E2E_TIMINGS?: Array<Record<string, unknown>>;
    __Forge_E2E_LOG?: (name: string, meta?: unknown) => void;
    __Forge_E2E_GET?: () => Array<Record<string, unknown>>;
    __Forge_E2E_MARK?: (name: string, meta?: unknown) => void;
    __Forge_E2E_APPLIED_RUNTIME_READY?: boolean;
  }

  // Allow tests to set flags on globalThis without casting
  var __Forge_PLAYWRIGHT: boolean | undefined;
  var __TEST_APP_MODE: string | undefined;
  var __TEST_SETTINGS_ERROR_STATUS: number | undefined;
  // Vitest global (mocking API) used by unit tests. Declared here so test
  // helpers can access it without importing 'vitest' at module init time.
  var vi: any;
  // E2E in-page helpers used by Playwright tests. Declaring them as globals
  // avoids ad-hoc casts in test files where page.evaluate/addInitScript is used.
  var __Forge_E2E_GET: (() => Array<Record<string, unknown>>) | undefined;
  var __Forge_E2E_LOG: ((name: string, meta?: unknown) => void) | undefined;
  var __Forge_E2E_MARK: ((name: string, meta?: unknown) => void) | undefined;
  var __Forge_E2E_TIMINGS: Array<Record<string, unknown>> | undefined;
}
