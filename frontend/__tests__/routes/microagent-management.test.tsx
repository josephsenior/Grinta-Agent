import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import MicroagentManagement, { clientLoader } from "#/routes/microagent-management";
import { renderWithProviders } from "../../test-utils";
import { queryClient } from "#/query-client-config";

const { getConfigMock } = vi.hoisted(() => ({
  getConfigMock: vi.fn(),
}));

vi.mock("#/api/forge", () => ({
  default: {
    getConfig: getConfigMock,
  },
}));

vi.mock("#/components/features/microagent-management/microagent-management-content", () => ({
  MicroagentManagementContent: () => <div data-testid="microagent-management-content" />,
}));

vi.mock("#/context/conversation-subscriptions-provider", () => ({
  ConversationSubscriptionsProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="conversation-provider">{children}</div>
  ),
}));

vi.mock("#/wrapper/event-handler", () => ({
  EventHandler: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="event-handler">{children}</div>
  ),
}));


describe("microagent-management route", () => {
  beforeEach(() => {
    queryClient.clear();
    getConfigMock.mockReset();
  });

  it("preloads config when missing", async () => {
    getConfigMock.mockResolvedValue({ APP_MODE: "oss" } as any);

    await expect(clientLoader()).resolves.toBeNull();
    expect(getConfigMock).toHaveBeenCalledTimes(1);
    expect(queryClient.getQueryData(["config"])).toEqual({ APP_MODE: "oss" });
  });

  it("skips network call when config already cached", async () => {
    queryClient.setQueryData(["config"], { APP_MODE: "saas" });

    await expect(clientLoader()).resolves.toBeNull();
    expect(getConfigMock).not.toHaveBeenCalled();
  });

  it("renders nested providers and content", () => {
    renderWithProviders(<MicroagentManagement />);

    const provider = screen.getByTestId("conversation-provider");
    expect(provider).toBeInTheDocument();
    const eventHandler = screen.getByTestId("event-handler");
    expect(eventHandler).toBeInTheDocument();
    expect(provider).toContainElement(eventHandler);
    const content = screen.getByTestId("microagent-management-content");
    expect(eventHandler).toContainElement(content);
  });
});
