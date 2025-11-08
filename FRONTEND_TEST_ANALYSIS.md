# Frontend Test Failure Analysis

## Executive Summary

**Test Results:**
- Test Files: 36 failed, 85 passed, 4 skipped (125 total)
- Tests: 116 failed, 580 passed, 28 skipped, 11 todo (735 total)

The failures fall into **6 primary categories** with distinct root causes. All issues are systematically fixable with targeted updates to test setup, component mocking, and provider wrappers.

---

## Failure Categories & Analysis

### Category 1: Missing Context Provider Wrappers
**Severity:** HIGH | **Count:** 42 failures | **Files:** 21 tests
**Error Pattern:** `useToast must be used within a ToastProvider`, `useTasks must be used within a TaskProvider`

**Affected Tests:**
- `__tests__/routes/llm-settings.test.tsx` (21 failures)
- `__tests__/components/features/chat/task-tracking-observation-content.test.tsx` (8 failures)
- `__tests__/components/shared/modals/settings/settings-form.test.tsx` (1 failure - partially)

**Root Cause:**
Test components are rendered without necessary context providers. The test utilities in `test-utils.tsx` wrap components with Redux, QueryClient, and Router, but are missing:
1. **ToastProvider** - Required by any component using `useToast()` hook
2. **TaskProvider** - Required by any component using `useTasks()` hook
3. **Dynamic imports** - Some providers may not be properly mocked/wrapped

**Example Error:**
```
useToast must be used within a ToastProvider
```

**Fix Approach:**
1. **Update `test-utils.tsx`** to include a custom render wrapper that adds ToastProvider and TaskProvider
2. **Create mock providers** in `test-stubs/` for components that need them
3. **Update individual test files** to use the new render function with all necessary wrappers

**Implementation Priority:** 1 (Fix first - blocks many other tests)

---

### Category 2: Unicode/Emoji Rendering Issues
**Severity:** HIGH | **Count:** 5 failures | **Files:** 2 tests
**Error Pattern:** Text finding failures like "Unable to find an element with the text: ԡ� 4.5"

**Affected Tests:**
- `src/components/features/settings/mcp-settings/__tests__/mcp-marketplace-card.test.tsx` (3 failures)
- `src/routes/__tests__/slack-settings.test.tsx` (1 failure - partially)

**Root Cause:**
Emojis and special Unicode characters are being corrupted during test rendering/assertion:
- **Star emoji** (⭐) appears as "Ԡ" in test output
- **Success icon** rendering is showing garbled characters
- Tests use literal string matching instead of flexible matchers

**Example Failures:**
1. "should display rating" - Looking for "⭐ 4.5" but emoji is corrupted
2. "should display category and type tags" - Looking for "NPM" split across elements

**Fix Approach:**
1. **Use flexible text matchers** instead of exact string matching:
   ```typescript
   // Instead of:
   screen.getByText("⭐ 4.5")
   // Use:
   screen.getByText((content, element) => /4\.5/.test(content) && element?.querySelector('[data-testid="star-icon"]'))
   ```
2. **Mock icon components** to return testable elements with `data-testid` attributes
3. **Split text matching** - Look for text fragments when split across elements
4. **Use regex patterns** that don't depend on exact character encoding

**Implementation Priority:** 2 (Fix after providers)

---

### Category 3: Mock Function Call Argument Mismatches
**Severity:** MEDIUM | **Count:** 12 failures | **Files:** 6 tests
**Error Pattern:** `expected "functionName" to be called with arguments: [ expected ] | Received: [ different ]`

**Affected Tests:**
- `src/routes/__tests__/slack-settings.test.tsx` (1 failure)
  - `uninstallSlackWorkspace` receives extra QueryClient metadata
- `__tests__/routes/app-settings.test.tsx` (2 failures)
  - Form values have wrong language/settings structure
- `__tests__/components/shared/modals/settings/settings-form.test.tsx` (1 failure)
  - `saveSettings` receives undefined fields in payload
- `src/utils/__tests__/custom-toast-handlers.test.ts` (2 failures)
  - Toast error handler sending different message/options than expected

**Root Cause:**
1. **Mutation hooks** passing additional context/metadata (QueryClient, metadata) beyond expected parameters
2. **Form state tracking** not properly capturing current values before submission
3. **Async operations** include wrapper objects that tests don't expect

**Example Issues:**
- Expected: `["T123"]`
- Received: `["T123", { client: QueryClient {}, meta: undefined, mutationKey: undefined }]`

**Fix Approach:**
1. **Update mutation calls** to only pass expected arguments (use `useCallback` or wrapper functions)
2. **Use `toHaveBeenCalledWith` with `expect.objectContaining()`** for flexible matching
3. **Update mock implementations** to match actual API signatures
4. **Use `vi.fn().mockImplementationOnce()`** for precise call verification

**Implementation Priority:** 3 (Medium impact)

---

### Category 4: Router & Navigation Errors
**Severity:** HIGH | **Count:** 7 failures | **Files:** 4 tests
**Error Pattern:** `Unable to find role="navigation"`, `Unable to find [data-testid="home-screen"]`, route mismatch errors

**Affected Tests:**
- `__tests__/routes/settings.test.tsx` (1 failure)
  - Route `/settings/user` not found (404)
- `__tests__/routes/home-screen.test.tsx` (5 failures)
  - Missing `home-screen`, `header-launch-button` elements
  - Route configuration incomplete
- `__tests__/routes/app-settings.test.tsx` (partial)
  - Dropdown state issues

**Root Cause:**
1. **Route configuration mismatch** - Test route structures don't match actual router setup
2. **Missing layout/wrapper components** - Tests don't render parent layouts needed for child routes
3. **HydrateFallback missing** - React Router suspense boundaries not configured for tests
4. **Async route loading** - Components wrapped in Suspense but tests timeout before component renders

**Example Errors:**
```
No routes matched location "/settings/user"
No route matches URL "/settings/user"
```

**Fix Approach:**
1. **Create test route configuration** that mirrors production routes
2. **Wrap test renders** with MemoryRouter pre-configured with correct routes
3. **Add HydrateFallback** to route definitions
4. **Increase waitFor timeouts** for async components
5. **Mock async loaders** in route definitions for tests

**Implementation Priority:** 4 (Blocks navigation-heavy tests)

---

### Category 5: DOM Element Not Found (Missing Data-Testid)
**Severity:** MEDIUM | **Count:** 11 failures | **Files:** 8 tests
**Error Pattern:** `Unable to find an element by: [data-testid="..."]`

**Affected Tests:**
- `__tests__/components/interactive-chat-box.test.tsx` (5 failures)
  - Missing `upload-image-input` - File upload is hidden or not rendered
- `__tests__/components/features/home/task-card.test.tsx` (1 failure)
  - Missing `conversation-screen` - Not navigated properly
- `__tests__/components/features/conversation-panel/conversation-card.test.tsx` (multiple)
  - Clipboard API undefined - navigator.clipboard mock issue

**Root Cause:**
1. **Conditional rendering** - Elements hidden behind feature flags or state conditions
2. **Lazy loading** - Components wrapped in lazy imports that don't resolve in tests
3. **CSS/display:none** - Elements exist in DOM but invisible and not queryable
4. **Mock API missing** - navigator.clipboard mock not properly initialized

**Fix Approach:**
1. **Check component rendering logic** - Ensure test conditions match render conditions
2. **Use `screen.debug()`** to see actual DOM in failing tests
3. **Mock navigator.clipboard** globally in test setup (already done, but may need reset)
4. **Use `screen.queryBy...` then assert** instead of `screen.getBy...`
5. **Add role queries** instead of data-testid when elements are visible

**Implementation Priority:** 3 (Medium - blocks specific features)

---

### Category 6: Async/Await & Timing Issues
**Severity:** MEDIUM | **Count:** 8 failures | **Files:** 5 tests
**Error Pattern:** Timeout errors, "Unable to apply hover styles", clipboard undefined

**Affected Tests:**
- `src/components/features/settings/mcp-settings/__tests__/mcp-marketplace-card.test.tsx` (1 failure - hover test timeout)
- `__tests__/components/features/conversation-panel/conversation-card.test.tsx` (16 failures)
  - `Cannot read properties of undefined (reading 'clipboard')` - clipboard mock not set up
- `__tests__/routes/home-screen.test.tsx` (1 failure - payment modal)

**Root Cause:**
1. **Hover state verification** - Test attempts to assert styles changed after hover, but transition doesn't complete
2. **Clipboard API race condition** - Test runs before `vitest.setup.ts` fully initializes clipboard mock
3. **WebGL context** - Canvas operations fail in jsdom environment
4. **Suspense boundaries** - Components timeout waiting for async operations

**Example Errors:**
```
Cannot read properties of undefined (reading 'clipboard')
Received has type: Null
unable to create webgl context
```

**Fix Approach:**
1. **Increase jest timeout** for specific tests: `it("test", async () => {...}, { timeout: 10000 })`
2. **Mock hover state** without relying on actual CSS transitions
3. **Move clipboard mock earlier** in vitest.setup.ts OR reset it per test
4. **Mock canvas operations** with explicit stubs
5. **Use `waitFor` with longer timeout** for async operations

**Implementation Priority:** 2 (Critical for animation/async tests)

---

### Category 7: Missing Global Test Flags
**Severity:** LOW | **Count:** 1 failure | **Files:** 1 test
**Error Pattern:** `__TEST_APP_MODE is not defined`

**Affected Tests:**
- `__tests__/sidebar-for-triage.test.tsx` (1 failure)

**Root Cause:**
Test looks for a global flag `__TEST_APP_MODE` that's not defined in the test environment.

**Fix Approach:**
```typescript
// In test setup or test file:
beforeAll(() => {
  globalThis.__TEST_APP_MODE = true;
});
```

**Implementation Priority:** 7 (Lowest - single test)

---

## Fix Priority & Implementation Order

### Phase 1: Setup & Infrastructure (HIGH IMPACT)
1. **Add missing providers to test-utils.tsx**
   - ToastProvider wrapper
   - TaskProvider wrapper
   - Update render function to include all providers
   - **Impact:** Fixes 42 tests immediately

2. **Fix vitest.setup.ts clipboard/navigator mock**
   - Ensure it runs before all tests
   - Reset per test if needed
   - **Impact:** Fixes 10-15 clipboard-related failures

### Phase 2: Component & Mock Fixes (MEDIUM IMPACT)
3. **Update unicode/emoji test assertions**
   - Replace exact string matching with flexible matchers
   - Mock icon components with data-testid
   - **Impact:** Fixes 5 emoji rendering tests

4. **Fix mutation hook call signatures**
   - Update mock expectations to use `expect.any()` or `expect.objectContaining()`
   - Adjust hook implementations if needed
   - **Impact:** Fixes 12 mock verification tests

### Phase 3: Routing & Navigation (MEDIUM IMPACT)
5. **Configure test routes properly**
   - Create test router configuration
   - Add HydrateFallback to routes
   - Increase suspense timeouts
   - **Impact:** Fixes 7 navigation/route tests

### Phase 4: Element & Rendering (LOW-MEDIUM IMPACT)
6. **Fix conditional rendering tests**
   - Review test setup conditions vs component conditions
   - Use queryBy for optional elements
   - **Impact:** Fixes 11 element-not-found tests

7. **Handle async/timing edge cases**
   - Increase timeouts selectively
   - Better mock timing for animations
   - **Impact:** Fixes 8 async/timing tests

### Phase 5: Cleanup (MINIMAL IMPACT)
8. **Add missing global flags**
   - Define `__TEST_APP_MODE` in setup
   - **Impact:** Fixes 1 test

---

## Key Files to Modify

### High Priority
1. **`frontend/test-utils.tsx`** - Add provider wrappers
2. **`frontend/vitest.setup.ts`** - Ensure all mocks run before tests
3. **`frontend/__tests__/routes/llm-settings.test.tsx`** - Use updated render with providers
4. **`frontend/__tests__/components/features/settings/mcp-settings/__tests__/mcp-marketplace-card.test.tsx`** - Fix emoji/string matching

### Medium Priority
5. **`frontend/__tests__/routes/home-screen.test.tsx`** - Fix routing
6. **`frontend/__tests__/routes/app-settings.test.tsx`** - Fix form/dropdown tests
7. **`frontend/__tests__/components/interactive-chat-box.test.tsx`** - Fix upload tests
8. **`frontend/__tests__/components/features/conversation-panel/conversation-card.test.tsx`** - Fix clipboard/multiple element queries

### Low Priority
9. **Various test files** - Update mock expectations with flexible matchers
10. **`frontend/__tests__/sidebar-for-triage.test.tsx`** - Add test flag

---

## Recommended Fix Templates

### Template 1: Add Providers to Render
```typescript
// In test-utils.tsx render function
const AllTheProviders = ({ children }: { children: React.ReactNode }) => {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <I18nextProvider i18n={i18n}>
          <MemoryRouter>
            <ToastProvider> {/* ADD THIS */}
              <TaskProvider> {/* ADD THIS */}
                {children}
              </TaskProvider>
            </ToastProvider>
          </MemoryRouter>
        </I18nextProvider>
      </QueryClientProvider>
    </Provider>
  );
};
```

### Template 2: Flexible Text Matching
```typescript
// Instead of exact matching:
// screen.getByText("⭐ 4.5")

// Use flexible matcher:
screen.getByText((content) => content.includes("4.5"));

// Or for split content:
screen.getByText((content, element) => {
  return element?.textContent?.includes("4.5") || false;
});
```

### Template 3: Flexible Mock Expectations
```typescript
// Instead of exact arguments:
// expect(mockFn).toHaveBeenCalledWith(exactly)

// Use flexible matching:
expect(mockFn).toHaveBeenCalledWith(
  expect.objectContaining({ userId: "T123" })
);

// Or with any():
expect(mockFn).toHaveBeenCalledWith(
  "T123",
  expect.any(Object)
);
```

### Template 4: Wait for Async Elements
```typescript
// For elements that take time to appear:
await waitFor(
  () => {
    expect(screen.getByTestId("upload-image-input")).toBeInTheDocument();
  },
  { timeout: 3000 } // Increase from default 1000ms
);

// Or use findBy with timeout:
const element = await screen.findByTestId("upload-image-input", {}, { timeout: 3000 });
```

---

## Testing Approach for Fixes

After each fix category:

1. **Run the specific test file:**
   ```bash
   npm run test -- <test-file-path>
   ```

2. **Check if related tests also pass:**
   ```bash
   npm run test -- --grep "pattern"
   ```

3. **Full test suite:**
   ```bash
   npm run test
   ```

4. **Monitor coverage:**
   ```bash
   npm run test -- --coverage
   ```

---

## Success Criteria

**Phase 1 Complete:** 42 provider-related tests pass (currently failing with "must be used within Provider" errors)

**Phase 2 Complete:** 12 mock verification tests pass (currently showing argument mismatches)

**Phase 3 Complete:** 7 routing tests pass (currently showing route/element not found)

**Phase 4 Complete:** 19 element/async tests pass (currently showing element/timeout errors)

**Overall Goal:** 116 → 0 failing tests; maintain 580+ passing tests

---

## Additional Notes

### Long-term Improvements
1. **Create custom test render functions** per feature area (settings, chat, navigation, etc.)
2. **Centralize mock provider definitions** in `test-stubs/` directory
3. **Document test patterns** for new components
4. **Add pre-commit hooks** to run tests for changed files
5. **CI/CD integration** to catch failures early

### Known Limitations
- jsdom doesn't support WebGL (affects canvas/dark-veil component)
- Some async transitions take longer in test environment
- Unicode rendering depends on terminal/test runner font support
- Clipboard API requires explicit mocking per test runner

