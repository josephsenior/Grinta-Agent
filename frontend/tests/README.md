# Playwright tests only

This directory contains Playwright end-to-end tests. Do not place Vitest unit tests
or files that import from `vitest` here — Playwright's loader executes test files
and importing `vitest` will pull Vitest internals into Playwright's runtime and
cause runtime conflicts. Keep unit tests under `__tests__` or another directory.
