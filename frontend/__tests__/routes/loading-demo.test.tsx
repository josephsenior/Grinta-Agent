import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import LoadingDemoRoute from "#/routes/loading-demo";
import { renderWithProviders } from "../../test-utils";

vi.mock("#/components/shared/demo/loading-demo", () => ({
  LoadingDemo: () => <div data-testid="loading-demo" />,
}));

describe("Loading demo route", () => {
  it("renders the loading demo component", () => {
    renderWithProviders(<LoadingDemoRoute />);

    expect(screen.getByTestId("loading-demo")).toBeInTheDocument();
  });
});
