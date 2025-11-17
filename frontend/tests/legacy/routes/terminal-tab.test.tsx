import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import TerminalTab from "#/routes/terminal-tab";
import { renderWithProviders } from "../../test-utils";

vi.mock("#/components/features/terminal/terminal", () => ({
  default: () => <div data-testid="terminal-component">terminal</div>,
}));

describe("TerminalTab route", () => {
  it("renders the terminal layout container", () => {
    const { container } = renderWithProviders(<TerminalTab />);

    expect(container.firstChild).toHaveClass("h-full");
    expect(container.firstChild).toHaveClass("flex");
  });

  it("lazy loads and renders the terminal component", async () => {
    renderWithProviders(<TerminalTab />);

    expect(await screen.findByTestId("terminal-component")).toBeInTheDocument();
  });
});
