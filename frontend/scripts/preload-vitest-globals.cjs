// Preload to define Vitest expect-related global symbols to avoid
// redefinition errors when @vitest/expect is loaded in mixed runtimes.
try {
  const MATCHERS = Symbol.for('matchers-object');
  const JEST = Symbol.for('$$jest-matchers-object');
  const ASY = Symbol.for('asymmetric-matchers-object');

  if (!Object.prototype.hasOwnProperty.call(globalThis, MATCHERS)) {
    Object.defineProperty(globalThis, MATCHERS, {
      configurable: true,
      enumerable: false,
      writable: true,
      value: new WeakMap(),
    });
  }

  // Provide a concrete object with the fields @vitest/expect expects.
  if (!Object.prototype.hasOwnProperty.call(globalThis, JEST)) {
    Object.defineProperty(globalThis, JEST, {
      configurable: true,
      enumerable: false,
      writable: true,
      value: {
        // initial state shape used by vitest/playwright expect bundles
        state: {
          assertionCalls: 0,
          expectedAssertionsNumber: null,
          isExpectingAssertions: false,
          numPassingAsserts: 0,
          suppressedErrors: [],
        },
        matchers: Object.create(null),
        customEqualityTesters: [],
      },
    });
  }

  if (!Object.prototype.hasOwnProperty.call(globalThis, ASY)) {
    Object.defineProperty(globalThis, ASY, {
      configurable: true,
      enumerable: false,
      writable: true,
      value: Object.create(null),
    });
  }
} catch (e) {
  // best-effort; if this fails, let the normal loader handle it
  try { console.error('preload-vitest-globals error', e && e.stack ? e.stack : e); } catch (_) {}
}

console.error('preload-vitest-globals loaded');
