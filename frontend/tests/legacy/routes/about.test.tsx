import { describe, it, expect } from "vitest";
import { screen, within } from "@testing-library/react";
import About from "#/routes/about";
import { renderWithProviders } from "../../test-utils";

function renderAbout() {
  return renderWithProviders(<About />);
}

describe("About route", () => {
  it("renders the translated title and mission statement", () => {
    renderAbout();

    expect(screen.getByTestId("page-title")).toHaveTextContent("ABOUT");
    expect(
      screen.getByRole("heading", { level: 2, name: "MISSION" }),
    ).toBeInTheDocument();
    expect(screen.getByText("MISSION$DESCRIPTION")).toBeInTheDocument();
  });

  it("lists all core capabilities with their default descriptions", () => {
    renderAbout();

    const list = screen.getByRole("list");
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(4);

    expect(screen.getByText("AUTOMATED_CODING")).toBeInTheDocument();
    expect(screen.getByText("TEST_GENERATION")).toBeInTheDocument();
    expect(screen.getByText("FAILURE_TAXONOMY")).toBeInTheDocument();
    expect(screen.getByText("GOVERNANCE")).toBeInTheDocument();
  });
});

