import { render, screen, waitFor } from "@testing-library/react";
import { it, describe, expect, vi, beforeEach, afterEach } from "vitest";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );

  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});
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

// Create a wrapper with QueryClientProvider and MemoryRouter
const createWrapper = (initialEntry = "/accept?redirect_url=/") => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialEntry]}>
          {children}
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
};

describe("AcceptTOS", () => {
  beforeEach(() => {
    vi.stubGlobal("location", { href: "" });
    mockNavigate.mockReset();
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
    const externalUrl = "https://example.com/callback";
    vi.mocked(Forge.post).mockResolvedValue({
      data: { redirect_url: externalUrl },
    });

    const user = userEvent.setup();
    render(<AcceptTOS />, { wrapper: createWrapper() });

    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "TOS$CONTINUE" }));

    await new Promise(process.nextTick);

    expect(window.location.href).toBe(externalUrl);
  });

  it("should navigate internally when given a relative redirect URL", async () => {
    vi.mocked(Forge.post).mockResolvedValue({
      data: { redirect_url: "/dashboard" },
    });

    const user = userEvent.setup();
    render(<AcceptTOS />, {
      wrapper: createWrapper("/accept?redirect_url=/projects"),
    });

    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "TOS$CONTINUE" }));

    await new Promise(process.nextTick);

    expect(mockNavigate).toHaveBeenCalledWith("/dashboard");
  });

  it("should fall back to the redirect query parameter when the API omits redirect_url", async () => {
    vi.mocked(Forge.post).mockResolvedValue({
      data: {},
    });

    const user = userEvent.setup();
    render(<AcceptTOS />, {
      wrapper: createWrapper("/accept?redirect_url=/workspace"),
    });

    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "TOS$CONTINUE" }));

    await new Promise(process.nextTick);

    expect(mockNavigate).toHaveBeenCalledWith("/workspace");
  });

  it("should default to the home redirect when no query parameter is provided", async () => {
    vi.mocked(Forge.post).mockResolvedValue({
      data: {},
    });

    const user = userEvent.setup();
    render(<AcceptTOS />, { wrapper: createWrapper("/accept") });

    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "TOS$CONTINUE" }));

    await new Promise(process.nextTick);

    expect(Forge.post).toHaveBeenCalledWith("/api/accept_tos", {
      redirect_url: "/",
    });
  });

  it("should redirect to home when the request fails", async () => {
    vi.mocked(Forge.post).mockRejectedValue(new Error("Network error"));

    const user = userEvent.setup();
    render(<AcceptTOS />, {
      wrapper: createWrapper("/accept?redirect_url=/workspace"),
    });

    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: "TOS$CONTINUE" }));

    await new Promise(process.nextTick);

    expect(window.location.href).toBe("/");
  });

  it("should show a loading state while submitting", async () => {
    let resolveMutation: ((value: { data: { redirect_url: string } }) => void) | undefined;
    const mutationPromise = new Promise<{ data: { redirect_url: string } }>(
      (resolve) => {
        resolveMutation = resolve;
      },
    );

    vi.mocked(Forge.post).mockReturnValue(mutationPromise);

    const user = userEvent.setup();
    render(<AcceptTOS />, { wrapper: createWrapper("/accept") });

    await user.click(screen.getByRole("checkbox"));
    const button = screen.getByRole("button", { name: "TOS$CONTINUE" });
    await user.click(button);

    expect(button).toHaveTextContent("HOME$LOADING");
    expect(button).toBeDisabled();

    resolveMutation?.({ data: { redirect_url: "/" } });
    await waitFor(() => expect(button).toHaveTextContent("TOS$CONTINUE"));
  });
});
