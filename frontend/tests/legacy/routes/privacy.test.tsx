import { describe, it, expect } from "vitest";
import { screen, within } from "@testing-library/react";
import Privacy from "#/routes/privacy";
import { renderWithProviders } from "../../test-utils";

function renderPrivacy() {
  return renderWithProviders(<Privacy />);
}

describe("Privacy route", () => {
  it("renders the page title and last updated text", () => {
    renderPrivacy();

    expect(screen.getByTestId("page-title")).toHaveTextContent("COMMON$PRIVACY_POLICY");
    expect(screen.getByText("PRIVACY$LAST_UPDATED")).toBeInTheDocument();
  });

  it("shows the placeholder policy description", () => {
    renderPrivacy();

    expect(screen.getByText("PRIVACY$PLACEHOLDER")).toBeInTheDocument();
  });

  it("lists the key policy sections", () => {
    renderPrivacy();

    const headings = screen.getAllByRole("heading", { level: 2 });
    const textContent = headings.map((heading) => heading.textContent);
    expect(textContent).toEqual([
      "PRIVACY$DATA_COLLECTION",
      "PRIVACY$DATA_USAGE",
      "PRIVACY$RETENTION",
      "PRIVACY$SECURITY",
    ]);

    const prose = screen.getByRole("main");
    const listItems = within(prose).getAllByText(/PRIVACY\$/);
    expect(listItems.length).toBeGreaterThanOrEqual(5);
  });
});
