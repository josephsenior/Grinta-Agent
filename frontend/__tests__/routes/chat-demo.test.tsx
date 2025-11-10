import React from "react";
import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import ChatDemoRoute, { hydrateFallback } from "#/routes/chat-demo";
import { renderWithProviders } from "../../test-utils";

vi.mock("#/components/features/chat/chat-interface-demo", () => ({
  ChatInterfaceDemo: () => <div data-testid="chat-interface-demo" />,
}));

describe("chat-demo route", () => {
  it("renders the chat interface demo", () => {
    renderWithProviders(<ChatDemoRoute />);

    expect(screen.getByTestId("chat-interface-demo")).toBeInTheDocument();
  });

  it("exposes a static hydrate fallback", () => {
    const { container } = renderWithProviders(<>{hydrateFallback}</>);

    const fallback = container.querySelector(".route-loading");
    expect(fallback).not.toBeNull();
    expect(fallback?.getAttribute("aria-hidden")).toBe("true");
  });
});
