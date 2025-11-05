// Minimal stub of @vitest/expect used only during Playwright runs
// to avoid loading the real vitest expect bundle which defines globals
module.exports = {
  expect: () => ({
    toBe: () => {},
    toEqual: () => {},
    not: { toBe: () => {} },
  }),
  default: {},
};
