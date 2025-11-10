import React from "react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ServedApp from "#/routes/served-tab";
import { renderWithProviders } from "../../test-utils";

const mockUseActiveHost = vi.fn();

vi.mock("#/hooks/query/use-active-host", () => ({
  useActiveHost: () => mockUseActiveHost(),
}));

vi.mock("#/components/features/served-host/path-form", () => ({
  PathForm: React.forwardRef<HTMLFormElement, {
    defaultValue: string;
    onBlur: React.FocusEventHandler<HTMLInputElement>;
  }>(({ defaultValue, onBlur }, ref) => (
    <form
      ref={(node) => {
        if (typeof ref === "function") {
          ref(node);
        } else if (ref) {
          (ref as React.MutableRefObject<HTMLFormElement | null>).current = node;
        }
      }}
      className="path-form"
    >
      <input
        name="url"
        aria-label="served-url"
        defaultValue={defaultValue}
        onBlur={onBlur}
      />
    </form>
  )),
}));

describe("Served app route", () => {
  const originalOpen = window.open;

  beforeEach(() => {
    mockUseActiveHost.mockReset();
    window.open = vi.fn();
  });

  afterEach(() => {
    window.open = originalOpen;
  });

  it("shows an empty state when no active host is available", () => {
    mockUseActiveHost.mockReturnValue({ activeHost: null });

    renderWithProviders(<ServedApp />);

    expect(screen.getByText("BROWSER$SERVER_MESSAGE")).toBeInTheDocument();
  });

  it("renders controls and updates the served path", async () => {
    mockUseActiveHost.mockReturnValue({ activeHost: "http://localhost:3000" });

    renderWithProviders(<ServedApp />);

    const buttons = screen.getAllByRole("button");
    const [externalButton, refreshButton, homeButton] = buttons;

    const iframe = screen.getByTitle("SERVED_APP$TITLE");
    expect(iframe).toHaveAttribute("src", "http://localhost:3000/");

    const input = screen.getByLabelText("served-url");
    await userEvent.clear(input);
    await userEvent.type(input, "http://127.0.0.1:5000/app/path");
    input.blur();

    const updatedIframe = await screen.findByTitle("SERVED_APP$TITLE");
    expect(updatedIframe).toHaveAttribute("src", "http://127.0.0.1:5000//app/path");

    await userEvent.click(externalButton);
    expect(window.open).toHaveBeenCalledWith("http://127.0.0.1:5000//app/path", "_blank");

    await userEvent.click(refreshButton);
    expect(screen.getAllByTitle("SERVED_APP$TITLE")).toHaveLength(1);

    await userEvent.click(homeButton);
    const resetIframe = await screen.findByTitle("SERVED_APP$TITLE");
    expect(resetIframe).toHaveAttribute("src", "http://localhost:3000/");
  });
});
