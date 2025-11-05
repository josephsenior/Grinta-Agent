// This file used to be a Vitest unit test. Unit tests were moved to
// `__tests__` to avoid accidental imports of Vitest into Playwright's
// test loader runtime (which causes Vitest internals to be executed and
// crash Playwright). If you need to run unit tests, run them with
// `vitest` from the project's root. Do not put Vitest tests in this
// Playwright `tests/` folder.

import { test } from "@playwright/test";

// Stub test so Playwright doesn't error on an empty directory.
test("repo-selection-form (moved to __tests__)", async ({ page }) => {
  test.skip();
});
