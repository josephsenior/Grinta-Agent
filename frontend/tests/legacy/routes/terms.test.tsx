import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import Terms from "#/routes/terms";
import { renderWithProviders } from "../../test-utils";

function renderTerms() {
  return renderWithProviders(<Terms />);
}

describe("Terms route", () => {
  it("renders the page title and last updated text", () => {
    renderTerms();

    expect(screen.getByTestId("page-title")).toHaveTextContent("TOS$TERMS");
    expect(screen.getByText("TOS$LAST_UPDATED")).toBeInTheDocument();
  });

  it("displays the placeholder description", () => {
    renderTerms();

    expect(screen.getByText("TOS$PLACEHOLDER")).toBeInTheDocument();
  });

  it("lists the four primary terms sections", () => {
    renderTerms();

    const headings = screen.getAllByRole("heading", { level: 2 });
    const textContent = headings.map((heading) => heading.textContent);
    expect(textContent).toEqual([
      "TOS$SECTION_1",
      "TOS$SECTION_2",
      "TOS$SECTION_3",
      "TOS$SECTION_4",
    ]);
  });
});
