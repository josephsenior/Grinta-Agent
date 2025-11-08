import { render, screen } from "@testing-library/react";
import { it, describe, expect, vi, beforeEach, afterEach } from "vitest";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import AcceptTOS from "#/routes/accept-tos";
import * as CaptureConsent from "#/utils/handle-capture-consent";
import { Forge } from "#/api/forge-axios";

// Mock the axios instance
vi.mock("#/api/forge-axios", () => ({
  Forge: {
    post: vi.fn(),
  },
}));

// Mock the toast handlers
vi.mock("#/utils/custom-toast-handlers", () => ({
  displayErrorToast: vi.fn(),
}));

// Create a wrapper with QueryClientProvider and BrowserRouter
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return function ({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          {children}
        </BrowserRouter>
      </QueryClientProvider>
    );
  };
};

describe("AcceptTOS", () => {
  beforeEach(() => {
    vi.stubGlobal("location", { href: "" });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetAllMocks();
  });

  it("should render a TOS checkbox that is unchecked by default", () => {
    render(<AcceptTOS />, { wrapper: createWrapper() });

    const checkbox = screen.getByRole("checkbox");
    const continueButton = screen.getByRole("button", { name: "TOS$CONTINUE" });

    expect(checkbox).not.toBeChecked();
    expect(continueButton).toBeDisabled();
  });

  it("should enable the continue button when the TOS checkbox is checked", async () => {
    const user = userEvent.setup();
    render(<AcceptTOS />, { wrapper: createWrapper() });

    const checkbox = screen.getByRole("checkbox");
    const continueButton = screen.getByRole("button", { name: "TOS$CONTINUE" });

    expect(continueButton).toBeDisabled();

    await user.click(checkbox);

    expect(continueButton).not.toBeDisabled();
  });

  it("should set user analytics consent to true when the user accepts TOS", async () => {
    const handleCaptureConsentSpy = vi.spyOn(
      CaptureConsent,
      "handleCaptureConsent",
    );

    // Mock the API response
    vi.mocked(Forge.post).mockResolvedValue({
      data: { redirect_url: "/" },
    });

    const user = userEvent.setup();
    render(<AcceptTOS />, { wrapper: createWrapper() });

    const checkbox = screen.getByRole("checkbox");
    await user.click(checkbox);

    const continueButton = screen.getByRole("button", { name: "TOS$CONTINUE" });
    await user.click(continueButton);

    // Wait for the mutation to complete
    await new Promise(process.nextTick);

    expect(handleCaptureConsentSpy).toHaveBeenCalledWith(true);
    expect(Forge.post).toHaveBeenCalledWith("/api/accept_tos", {
      redirect_url: "/",
    });
  });

  it("should handle external redirect URLs", async () => {
    // Mock the API response with an external URL
    const externalUrl = "https://example.com/callback";
    vi.mocked(Forge.post).mockResolvedValue({
      data: { redirect_url: externalUrl },
    });

    const user = userEvent.setup();
    render(<AcceptTOS />, { wrapper: createWrapper() });

    const checkbox = screen.getByRole("checkbox");
    await user.click(checkbox);

    const continueButton = screen.getByRole("button", { name: "TOS$CONTINUE" });
    await user.click(continueButton);

    // Wait for the mutation to complete
    await new Promise(process.nextTick);

    expect(window.location.href).toBe(externalUrl);
  });
});
