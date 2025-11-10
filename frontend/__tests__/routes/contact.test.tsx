import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import Contact from "#/routes/contact";
import { renderWithProviders } from "../../test-utils";

describe("Contact route", () => {
  function renderContact() {
    return renderWithProviders(<Contact />);
  }

  it("renders the translated page title and helper text", () => {
    renderContact();

    expect(screen.getByTestId("page-title")).toHaveTextContent("CONTACT");
    expect(screen.getByText("CONTACT$HELP_TEXT")).toBeInTheDocument();
  });

  it("lists the primary contact email addresses", () => {
    renderContact();

    expect(screen.getByText("hello@Forge.pro")).toHaveAttribute(
      "href",
      "mailto:hello@Forge.pro",
    );
    expect(screen.getByText("support@Forge.pro")).toHaveAttribute(
      "href",
      "mailto:support@Forge.pro",
    );
    expect(screen.getByText("security@Forge.pro")).toHaveAttribute(
      "href",
      "mailto:security@Forge.pro",
    );
  });

  it("renders the response time note", () => {
    renderContact();

    expect(screen.getByText("CONTACT$RESPONSE_TIMES")).toBeInTheDocument();
  });
});
