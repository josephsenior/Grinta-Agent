import React from "react";
import { renderHook, act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const createConversationMock = vi.fn();
const subscribeMock = vi.fn();
const unsubscribeMock = vi.fn();
const isSubscribedMock = vi.fn();
const renderConversationStartingToastMock = vi.fn();
const dismissMock = vi.fn();
const getConversationMock = vi.fn();

vi.mock("#/hooks/mutation/use-create-conversation", () => ({
  useCreateConversation: () => ({ mutate: createConversationMock, isPending: false }),
}));

vi.mock("#/hooks/use-user-providers", () => ({
  useUserProviders: () => ({ providers: new Set(["github"]) }),
}));

vi.mock("#/context/conversation-subscriptions-provider", () => ({
  useConversationSubscriptions: () => ({
    subscribeToConversation: subscribeMock,
    unsubscribeFromConversation: unsubscribeMock,
    isSubscribedToConversation: isSubscribedMock,
    activeConversationIds: ["1"],
  }),
}));

vi.mock("#/components/features/chat/microagent/microagent-status-toast", () => ({
  renderConversationStartingToast: renderConversationStartingToastMock,
}));

vi.mock("#/utils/safe-hot-toast", () => ({
  __esModule: true,
  default: { dismiss: dismissMock },
}));

vi.mock("#/api/forge", () => ({
  __esModule: true,
  default: {
    getConversation: getConversationMock,
  },
}));

describe("useCreateConversationAndSubscribeMultiple", () => {
  const createWrapper = () => {
    const queryClient = new QueryClient();
    return ({ children }: { children: React.ReactNode }) =>
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        children,
      );
  };

  beforeEach(() => {
    vi.useFakeTimers();
    createConversationMock.mockReset();
    subscribeMock.mockReset();
    unsubscribeMock.mockReset();
    isSubscribedMock.mockReset();
    renderConversationStartingToastMock.mockReset();
    getConversationMock.mockReset();
    dismissMock.mockReset();
    vi.resetModules();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("creates conversation and subscribes when ready", async () => {
    createConversationMock.mockImplementation((_payload, opts) => {
      opts.onSuccess({
        conversation_id: "conv-1",
        session_api_key: "session",
        url: "https://example.com/api/conversations/conv-1",
      });
    });

    getConversationMock.mockResolvedValueOnce({ status: "STARTING" });
    getConversationMock.mockResolvedValueOnce({
      status: "RUNNING",
      session_api_key: "session",
      url: "https://example.com/api/conversations/conv-1",
    });

    const wrapper = createWrapper();
    const { useCreateConversationAndSubscribeMultiple } = await import("#/hooks/use-create-conversation-and-subscribe-multiple");
    const { result } = renderHook(() => useCreateConversationAndSubscribeMultiple(), { wrapper });
    const successCallback = vi.fn();

    act(() => {
      result.current.createConversationAndSubscribe({
        query: "hi",
        conversationInstructions: "stuff",
        repository: { name: "repo", gitProvider: "github" as any },
        onSuccessCallback: successCallback,
      });
    });

    expect(successCallback).toHaveBeenCalledWith("conv-1");

    await act(async () => {
      await vi.runOnlyPendingTimersAsync();
      await vi.runOnlyPendingTimersAsync();
    });

    expect(subscribeMock).toHaveBeenCalledWith(
      expect.objectContaining({
        conversationId: "conv-1",
        sessionApiKey: "session",
        baseUrl: "example.com",
      }),
    );
  });

  it("falls back to backend host when URL is relative", async () => {
    createConversationMock.mockImplementation((_payload, opts) => {
      opts.onSuccess({
        conversation_id: "conv-relative",
        session_api_key: null,
        url: "/api/conversations/conv-relative",
      });
    });

    getConversationMock.mockResolvedValueOnce({
      status: "RUNNING",
      session_api_key: null,
      url: "/api/conversations/conv-relative",
    });

    const wrapper = createWrapper();
    const { useCreateConversationAndSubscribeMultiple } = await import("#/hooks/use-create-conversation-and-subscribe-multiple");
    const { result } = renderHook(() => useCreateConversationAndSubscribeMultiple(), { wrapper });

    act(() => {
      result.current.createConversationAndSubscribe({
        query: "hi",
        conversationInstructions: "stuff",
        repository: { name: "repo", gitProvider: "github" as any },
      });
    });

    await act(async () => {
      await vi.runOnlyPendingTimersAsync();
    });

    expect(subscribeMock).toHaveBeenCalled();
  });

  it("handles STOPPED status by dismissing toast and cleaning up", async () => {
    createConversationMock.mockImplementation((_payload, opts) => {
      opts.onSuccess({
        conversation_id: "conv-stop",
        session_api_key: null,
        url: "",
      });
    });

    getConversationMock.mockResolvedValueOnce({ status: "STOPPED" });

    const wrapper = createWrapper();
    const { useCreateConversationAndSubscribeMultiple } = await import("#/hooks/use-create-conversation-and-subscribe-multiple");
    const { result } = renderHook(() => useCreateConversationAndSubscribeMultiple(), { wrapper });

    act(() => {
      result.current.createConversationAndSubscribe({
        query: "hi",
        conversationInstructions: "stuff",
        repository: { name: "repo", gitProvider: "github" as any },
      });
    });

    await act(async () => {
      await vi.runOnlyPendingTimersAsync();
    });

    expect(dismissMock).toHaveBeenCalledWith("starting-conv-stop");
  });

  it("returns helper utilities from hook", async () => {
    const wrapper = createWrapper();
    const { useCreateConversationAndSubscribeMultiple } = await import("#/hooks/use-create-conversation-and-subscribe-multiple");
    const { result } = renderHook(() => useCreateConversationAndSubscribeMultiple(), { wrapper });

    expect(result.current.unsubscribeFromConversation).toBe(unsubscribeMock);
    expect(result.current.isSubscribedToConversation).toBe(isSubscribedMock);
    expect(result.current.activeConversationIds).toEqual(["1"]);
    expect(result.current.isPending).toBe(false);
  });
});
