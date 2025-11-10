import React from "react";
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import ConversationRedirect from "#/routes/conversation-redirect";
import { renderWithProviders } from "../../test-utils";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("ConversationRedirect route", () => {
  it("navigates to /conversations on mount", () => {
    renderWithProviders(<ConversationRedirect />);

    expect(mockNavigate).toHaveBeenCalledWith("/conversations", { replace: true });
  });

  it("renders a redirecting placeholder", () => {
    renderWithProviders(<ConversationRedirect />);

    expect(screen.getByText("Redirecting to conversations...")).toBeInTheDocument();
  });
});
