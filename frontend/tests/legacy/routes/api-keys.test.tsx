import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import ApiKeysScreen from "#/routes/api-keys";
import { renderWithProviders } from "../../test-utils";

describe("ApiKeys route", () => {
  it("renders the API keys manager", () => {
    renderWithProviders(<ApiKeysScreen />);

    expect(screen.getByText("SETTINGS$Forge_API_KEYS")).toBeInTheDocument();
    expect(screen.getByText("SETTINGS$CREATE_API_KEY")).toBeInTheDocument();
  });
});

