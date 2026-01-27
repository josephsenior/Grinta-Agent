import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import Browser from "#/routes/browser-tab";
import { renderWithProviders } from "#test-utils";

vi.mock("#/components/features/browser/interactive-browser", () => ({
  InteractiveBrowser: () => <div data-testid="interactive-browser" />,
}));

describe("Browser tab route", () => {
  it("renders the interactive browser component", () => {
    renderWithProviders(<Browser />);

    expect(screen.getByTestId("interactive-browser")).toBeInTheDocument();
  });
});


