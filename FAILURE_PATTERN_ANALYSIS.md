# Frontend Test Failure Pattern Analysis

**Analysis Date:** Current Session  
**Test Suite:** Vitest v3.2.4  
**Total Tests:** 735 (109 failed | 576 passed | 39 skipped | 11 todo)  
**Total Test Files:** 125 (33 failed | 88 passed | 4 skipped)  
**Test Duration:** 178.14s

---

## Executive Summary

This analysis identifies the **top 10 failure patterns** from 109 failed tests across 33 test files. Fixing these 10 patterns would resolve the majority of test failures.

### Key Statistics
- **Unique Failure Patterns:** 17+
- **Most Common Pattern:** Mock function mismatch (20 occurrences)
- **Highest Impact Pattern:** Clipboard API missing (16 occurrences)
- **Files with Failures:** 121+ test files involved

---

## TOP 10 FAILURE PATTERNS (By Frequency)

### 1. **Mock Function Mismatch: `spy`**
- **Count:** 20 occurrences
- **Category:** Mocking / Test Setup
- **Description:** Test spy expectations don't match actual function calls
- **Root Cause:** Mock function arguments or call signatures have changed
- **Files Affected:** `custom-toast-handlers.test.ts`, `launch-microagent-modal.test.tsx`, settings-related tests
- **Example Test Names:**
  - `custom-toast-handlers.test.ts > toast display duration`
  - `launch-microagent-modal.test.tsx > microagent modal tests`
  - `settings-form.test.tsx > saveSettings spy tests`
- **Impact:** HIGH - Affects multiple test suites
- **Fix Priority:** 1
- **Solution:** Review mock setup in test files, ensure spy calls match actual function signatures

---

### 2. **Clipboard API Not Available**
- **Count:** 16 occurrences
- **Category:** Browser API Mocking
- **Description:** `navigator.clipboard` is undefined in test environment
- **Root Cause:** Clipboard API not mocked in jsdom test environment
- **Files Affected:** `conversation-card.test.tsx`, `expandable-message.test.tsx`, and related component tests
- **Example Error:**
  ```
  TypeError: Cannot read properties of undefined (reading 'clipboard')
  at resetClipboardStubOnView (node_modules/@testing-library/user-event/dist/esm/utils/dataTransfer/Clipboard.js:115:42)
  ```
- **Impact:** VERY HIGH - Affects 16+ tests related to copy/paste operations
- **Fix Priority:** 2
- **Solution:** Mock `navigator.clipboard` in test setup or conftest.py

---

### 3. **Missing Mock Export: `Tag` from `lucide-react`**
- **Count:** 10 occurrences
- **Category:** Icon Library Mocking
- **Description:** The `Tag` icon component is not exported by the `lucide-react` mock
- **Root Cause:** Incomplete vi.mock() for lucide-react - missing specific icon exports
- **Files Affected:** `memory-card.test.tsx` (10 consecutive failures)
- **Example Error:**
  ```
  Error: [vitest] No "Tag" export is defined on the "lucide-react" mock.
  Did you forget to return it from "vi.mock"?
  ```
- **Impact:** HIGH - Blocks entire test suite for MemoryCard component
- **Fix Priority:** 3
- **Solution:** Update lucide-react mock to include all required icon exports (Tag, Download, Info, ExternalLink, etc.)

---

### 4. **Unable to Find Element: `data-testid="upload-image-input"`**
- **Count:** 5 occurrences
- **Category:** DOM Query / Element Rendering
- **Description:** Test attempts to find element that isn't rendered or has different testid
- **Root Cause:** DOM structure mismatch, missing element in rendered output, or incorrect testid
- **Files Affected:** `interactive-chat-box.test.tsx`, related component tests
- **Example Error:**
  ```
  TestingLibraryElementError: Unable to find an element by: [data-testid="upload-image-input"]
  ```
- **Impact:** HIGH - Component test failures
- **Fix Priority:** 4
- **Solution:** Verify DOM structure, check if element is conditionally rendered, update test selectors

---

### 5. **useLocation() Hook Not in Router Context**
- **Count:** 5 occurrences
- **Category:** Route/Context Setup
- **Description:** Component using `useLocation()` from react-router-dom is not wrapped in test provider
- **Root Cause:** Test renders component without BrowserRouter or test wrapper
- **Files Affected:** `accept-tos.test.tsx` (at least 4 consecutive failures), route-related tests
- **Example Error:**
  ```
  Error: useLocation() may be used only in the context of a <Router> component
  ```
- **Impact:** HIGH - Affects all TOS/routing acceptance tests
- **Fix Priority:** 5
- **Solution:** Wrap component in BrowserRouter or custom test providers in test setup

---

### 6. **Found Multiple Elements: `data-testid="ellipsis-button"`**
- **Count:** 5 occurrences
- **Category:** DOM Query / Test Specificity
- **Description:** Test uses `getByTestId()` but multiple elements have the same testid
- **Root Cause:** Test renders multiple instances of component (list, grid, etc.) with same testid
- **Files Affected:** `expandable-message.test.tsx`, `conversation-card.test.tsx`, component tests
- **Example Error:**
  ```
  TestingLibraryElementError: Found multiple elements by: [data-testid="ellipsis-button"]
  (If this is intentional, then use the `*AllBy*` variant of the query...)
  ```
- **Impact:** MEDIUM-HIGH - Affects component variants/list rendering
- **Fix Priority:** 6
- **Solution:** Use `getAllByTestId()`, `queryAllByTestId()`, or add more specific selectors (e.g., within container query)

---

### 7. **Found Multiple Elements: `data-testid="context-menu"`**
- **Count:** 4 occurrences
- **Category:** DOM Query / Test Specificity
- **Description:** Multiple context menu elements rendered, need to specify which one
- **Root Cause:** Context menus in lists or multiple component instances
- **Files Affected:** Component dropdown/context menu tests
- **Impact:** MEDIUM - Similar issue to #6
- **Fix Priority:** 7
- **Solution:** Use `getAllByTestId()` with index, or query within specific container

---

### 8. **Unable to Find Element: `data-testid="home-screen"`**
- **Count:** 2 occurrences
- **Category:** Navigation / Route Rendering
- **Description:** Home screen component not rendered or not navigated to in test
- **Root Cause:** Navigation not working in test, async state not awaited, missing route setup
- **Files Affected:** `task-card.test.tsx` (navigation test), route tests
- **Example Error:**
  ```
  TestingLibraryElementError: Unable to find an element by: [data-testid="conversation-screen"]
  (in navigation test)
  ```
- **Impact:** MEDIUM - Navigation-related tests
- **Fix Priority:** 8
- **Solution:** Ensure router setup, await navigation changes with `findByTestId()` or `waitFor()`

---

### 9. **Unable to Find Element: `data-testid="header-launch-button"`**
- **Count:** 2 occurrences
- **Category:** DOM Query / Conditional Rendering
- **Description:** Button not present in rendered DOM
- **Root Cause:** Button only rendered under certain conditions not met in test
- **Files Affected:** Header component tests
- **Impact:** LOW-MEDIUM - Specific component tests
- **Fix Priority:** 9
- **Solution:** Check conditional rendering logic, ensure test props/state match expected conditions

---

### 10. **Found Multiple Elements: `data-testid="conversation-card"`**
- **Count:** 2 occurrences
- **Category:** DOM Query / Test Specificity
- **Description:** Multiple conversation cards rendered in list
- **Root Cause:** List test needs to target specific card or use getAllByTestId
- **Files Affected:** Conversation panel tests
- **Impact:** LOW - Same pattern as #6 and #7
- **Fix Priority:** 10
- **Solution:** Use more specific selectors or `getAllByTestId()` with index

---

## Other Notable Patterns

### WebGL Context Creation Failed (2 occurrences)
- **Description:** Canvas-based component (DarkVeil) needs WebGL context mock
- **Solution:** Mock Canvas/WebGL in test environment

### State Update Not Wrapped in act() (ActionSuggestions component)
- **Description:** Async state updates not wrapped in React's act() function
- **Solution:** Wrap state updates/navigation in `act()` or use `waitFor()`

### Unicode/Emoji Text Split Across Elements (2 occurrences)
- **Description:** Text like "★ 4.5" or emoji appears in multiple DOM elements
- **Solution:** Use text matching function instead of exact string match

---

## Fix Priority Roadmap

| Priority | Pattern | Count | Est. Tests Fixed | Effort |
|----------|---------|-------|-----------------|--------|
| 1 | Mock spy fixes | 20 | ~20 | Medium |
| 2 | Clipboard API mock | 16 | ~16 | Low |
| 3 | lucide-react mock exports | 10 | ~10 | Low |
| 4 | Element queries (unable to find) | 12 | ~12 | Medium |
| 5 | Router context wrapper | 5 | ~5 | Low |
| 6-7 | Multiple element queries | 9 | ~9 | Low |
| 8-10 | Navigation/rendering edge cases | 6 | ~6 | Medium |

**Total Potential Tests Fixed:** ~88+ of 109 failed tests

---

## Implementation Strategy

### Phase 1: Quick Wins (Low Effort, High Impact)
1. ✅ Fix Clipboard API mock (16 tests)
2. ✅ Add missing lucide-react icon exports (10 tests)
3. ✅ Add Router wrapper to test setup (5 tests)

### Phase 2: Medium Effort
4. Review and fix mock spy calls (20 tests)
5. Fix multiple element query selectors (9 tests)

### Phase 3: Navigation & Edge Cases
6. Fix navigation/routing tests (6 tests)
7. Handle conditional rendering edge cases

---

## Files to Investigate/Fix

**Critical Files:**
- `conftest.py` or `vitest.config.ts` - Add global mocks for Clipboard API
- `__tests__/test-utils.tsx` - Review test render/setup functions
- Individual test files listed above

**Test Files with Most Failures:**
- `__tests__/components/features/conversation-panel/conversation-card.test.tsx` (multiple patterns)
- `src/components/features/memory/__tests__/memory-card.test.tsx` (10 failures from lucide-react mock)
- `__tests__/routes/accept-tos.test.tsx` (5 failures from Router context)
- `src/components/features/settings/mcp-settings/__tests__/mcp-marketplace-card.test.tsx`

---

## Next Steps

1. **Create test utilities helper** with proper mock setup (Clipboard, Router context, lucide-react)
2. **Update conftest/vitest config** with global mocks
3. **Fix high-frequency patterns** first (Mock spies, Clipboard API)
4. **Incrementally fix remaining patterns** by priority
5. **Re-run test suite** after each phase to verify improvements

---

*Generated from analysis of test-results-detailed.txt (23,379 lines)*
