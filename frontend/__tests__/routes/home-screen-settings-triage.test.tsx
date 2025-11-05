// This triage test ensures the Sidebar sees a 404 settings error by mocking
// the useSettings hook before importing the application modules.
import React from "react";
import { screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
// Update the import path to the correct location of your test utilities
import { MemoryRouter } from "react-router-dom";
import {
  renderWithProviders,
  setPlaywrightFlag,
  mockSettings404,
} from "../../test-utils";

// Now import app modules that depend on those hooks
import { Sidebar } from "#/components/features/sidebar/sidebar";

// Mock the settings hook at module initialization so any module that
// imports it will receive the mocked value synchronously.
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

// Mock config hook to return OSS so the Sidebar will attempt to open the modal
vi.mock("#/hooks/query/use-config", () => ({
  useConfig: () => ({
    data: { APP_MODE: "oss", FEATURE_FLAGS: { HIDE_LLM_SETTINGS: false } },
    isLoading: false,
  }),
}));

// Mock the settings modal to render a predictable test id for assertions
vi.mock("#/components/shared/modals/settings/settings-modal", () => ({
  SettingsModal: (props: any) =>
    React.createElement("div", { "data-testid": "ai-config-modal" }),
}));

describe("HomeScreen settings triage (mocked useSettings)", () => {
  it("Sidebar should open settings modal when useSettings reports 404", async () => {
    // Ensure Playwright test flag is set so Sidebar will render modal even if effect timing differs
    setPlaywrightFlag(true);

    const usedMsw = mockSettings404();
    if (!usedMsw) {
      __TEST_APP_MODE = "oss";
      __TEST_SETTINGS_ERROR_STATUS = 404;
    }

    renderWithProviders(
      React.createElement(
        MemoryRouter,
        { initialEntries: ["/"] },
        React.createElement(Sidebar, null),
      ),
    );

    const modal = await screen.findByTestId("ai-config-modal");
    expect(modal).toBeInTheDocument();

    setPlaywrightFlag(false);
    __TEST_APP_MODE = undefined;
    __TEST_SETTINGS_ERROR_STATUS = undefined;
  });
});
