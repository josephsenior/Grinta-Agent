import React from "react";
import { screen } from "@testing-library/react";
import { it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import {
  renderWithProviders,
  setPlaywrightFlag,
  mockSettings404,
} from "test-utils";
// Import the real Sidebar implementation and mock its dependencies so the
// component runs under test without pulling in heavy app transforms.
import { Sidebar } from "#/components/features/sidebar/sidebar";
// Mock heavy UI modules that trigger the react-router Vite plugin during transform
// so tests can run without processing the full application routing preamble.
vi.mock("#/components/shared/modals/settings/settings-modal", () => ({
  SettingsModal: (props: any) =>
    React.createElement("div", { "data-testid": "ai-config-modal" }),
}));
vi.mock("#/components/shared/loading-spinner", () => ({
  LoadingSpinner: (props: any) =>
    React.createElement("div", { "data-testid": "loading-spinner" }),
}));

// Mock hooks used by Sidebar at the top so their module-level imports see
// the mocked implementations synchronously during test initialization.
vi.mock("#/hooks/query/use-settings", () => ({
  useSettings: () => ({
    data: undefined,
    error: { status: 404 },
    isError: true,
    isLoading: false,
    isFetching: false,
    isFetched: true,
  }),
}));

vi.mock("#/hooks/query/use-config", () => ({
  useConfig: () => ({
    data: { APP_MODE: "oss", FEATURE_FLAGS: { HIDE_LLM_SETTINGS: false } },
    isLoading: false,
  }),
}));

vi.mock("#/hooks/query/use-git-user", () => ({ useGitUser: () => ({}) }));
// rely on the global vitest setup which installs @testing-library/jest-dom/vitest

it("sidebar forced-open modal appears when test flag set", async () => {
  // Simulate a Playwright run so the Sidebar effect path is taken
  setPlaywrightFlag(true);

  // Prefer mocking at the network layer for deterministic behaviour.
  // If MSW is available, register a one-off 404 for GET /api/settings.
  // Fall back to mocking the hooks if MSW isn't present.
  const usedMsw = mockSettings404();
  if (!usedMsw) {
    // If MSW isn't available, set lightweight globals that TestSidebar reads
    __TEST_APP_MODE = "oss";
    __TEST_SETTINGS_ERROR_STATUS = 404;
  }

  // Render the real Sidebar wrapped in a MemoryRouter so useLocation/useNavigate
  // hooks work during the test.
  renderWithProviders(
    React.createElement(
      MemoryRouter,
      { initialEntries: ["/"] },
      React.createElement(Sidebar, null),
    ),
  );
  // The SettingsModal renders into a portal; search the document body
  const modal = await screen.findByTestId(
    "ai-config-modal",
    {},
    { timeout: 2000 },
  );
  expect(modal).toBeInTheDocument();
  setPlaywrightFlag(false);
  // clean up
  __TEST_APP_MODE = undefined;
  __TEST_SETTINGS_ERROR_STATUS = undefined;
});
