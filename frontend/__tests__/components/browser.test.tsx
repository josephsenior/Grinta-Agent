import { describe, it, expect, afterEach, vi } from "vitest";
import { screen, render } from "@testing-library/react";
import React from "react";

// Component no longer exists - this test is kept for reference but skipped
describe.skip("Browser", () => {
  afterEach(() => {
    vi.clearAllMocks();
    // Reset the mock state
    mockBrowserState = {
      url: "https://example.com",
      screenshotSrc: "",
    };
  });

  it("renders a message if no screenshotSrc is provided", () => {
    // Set the mock state for this test
    mockBrowserState = {
      url: "https://example.com",
      screenshotSrc: "",
    };

    render(<BrowserPanel />);

    // i18n empty message key
    expect(screen.getByText("BROWSER$NO_PAGE_LOADED")).toBeInTheDocument();
  });

  it("renders the url and a screenshot", () => {
    // Set the mock state for this test
    mockBrowserState = {
      url: "https://example.com",
      screenshotSrc:
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mN0uGvyHwAFCAJS091fQwAAAABJRU5ErkJggg==",
    };

    render(<BrowserPanel />);

    expect(screen.getByText("https://example.com")).toBeInTheDocument();
    expect(screen.getByAltText("BROWSER$SCREENSHOT_ALT")).toBeInTheDocument();
  });
});
