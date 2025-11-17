import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PricingPage from "#/routes/pricing";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";
import { useNavigate } from "react-router-dom";

vi.mock("#/hooks/mutation/use-create-conversation", () => ({
  useCreateConversation: vi.fn(),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return {
    ...actual,
    useNavigate: vi.fn(),
  };
});

vi.mock("#/components/ui/card", () => ({
  Card: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="card">{children}</div>
  ),
  CardHeader: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  CardContent: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  CardTitle: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

vi.mock("#/components/ui/badge", () => ({
  Badge: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <span data-testid="badge" className={className}>
      {children}
    </span>
  ),
}));

vi.mock("#/components/ui/button", () => ({
  Button: ({ children, ...rest }: { children: React.ReactNode }) => (
    <button {...rest}>{children}</button>
  ),
}));

const mockedUseCreateConversation = vi.mocked(useCreateConversation);
const mockedUseNavigate = vi.mocked(useNavigate);

describe("PricingPage", () => {
  const mutate = vi.fn();
  const navigate = vi.fn();

  beforeEach(() => {
    mutate.mockReset();
    navigate.mockReset();
    mockedUseCreateConversation.mockReturnValue({
      mutate,
      isPending: false,
    } as any);
    mockedUseNavigate.mockReturnValue(navigate);
  });

  it("toggles billing period between monthly and annual", async () => {
    render(<PricingPage />);

    expect(screen.getByText("Monthly")).toHaveClass("bg-brand-500");
    expect(screen.getAllByText("$15").length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole("button", { name: /Annual/ }));

    expect(screen.getByText("Annual")).toHaveClass("bg-brand-500");
    expect(screen.getAllByText(/\/year/).length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole("button", { name: "Monthly" }));
    expect(screen.getByText("Monthly")).toHaveClass("bg-brand-500");
  });

  it("creates a conversation and navigates on success", async () => {
    mutate.mockImplementation((_vars, options) => {
      options?.onSuccess?.({ conversation_id: "abc123" });
    });

    const setItem = vi.spyOn(window.localStorage.__proto__, "setItem");

    render(<PricingPage />);

    await userEvent.click(screen.getByRole("button", { name: "Start Pro Trial" }));

    await waitFor(() =>
      expect(setItem).toHaveBeenCalledWith("RECENT_CONVERSATION_ID", "abc123"),
    );
    expect(setItem).toHaveBeenCalledWith("SELECTED_PLAN", "pro");
    expect(navigate).toHaveBeenCalledWith("/conversations/abc123");

    setItem.mockRestore();
  });

  it("ignores localStorage errors when starting a plan", async () => {
    mutate.mockImplementation((_vars, options) => {
      options?.onSuccess?.({ conversation_id: "err123" });
    });

    const setItem = vi
      .spyOn(window.localStorage.__proto__, "setItem")
      .mockImplementation(() => {
        throw new Error("quota");
      });

    render(<PricingPage />);

    await userEvent.click(screen.getByRole("button", { name: "Start Pro+ Trial" }));

    await waitFor(() =>
      expect(navigate).toHaveBeenCalledWith("/conversations/err123"),
    );
    setItem.mockRestore();
  });

  it("expands and collapses FAQ items", async () => {
    render(<PricingPage />);

    const faqButton = screen.getByRole("button", {
      name: /What are platform credits\?/,
    });

    const answerContainer = faqButton.nextElementSibling as HTMLElement;
    expect(answerContainer).toHaveClass("max-h-0");

    await userEvent.click(faqButton);
    expect(answerContainer).toHaveClass("max-h-96");

    await userEvent.click(faqButton);
    expect(answerContainer).toHaveClass("max-h-0");
  });

  it("handles final call-to-action buttons", async () => {
    render(<PricingPage />);

    const startFreeButtons = screen.getAllByRole("button", { name: "Start Free" });
    await userEvent.click(startFreeButtons[startFreeButtons.length - 1]);
    expect(mutate).toHaveBeenCalledWith(
      {},
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );

    await userEvent.click(screen.getByRole("button", { name: "Contact Sales" }));
    expect(navigate).toHaveBeenCalledWith("/contact");
  });
});

