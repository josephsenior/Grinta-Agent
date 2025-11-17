import React from "react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "../../src/routes/conversation";

const navigateMock = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
}));

const dispatchMock = vi.fn();
vi.mock("react-redux", () => ({
  useDispatch: () => dispatchMock,
}));

const useConversationIdMock = vi.fn();
vi.mock("#/hooks/use-conversation-id", () => ({
  useConversationId: () => useConversationIdMock(),
}));

const useConversationConfigMock = vi.fn();
vi.mock("#/hooks/query/use-conversation-config", () => ({
  useConversationConfig: () => useConversationConfigMock(),
}));

const useBatchFeedbackMock = vi.fn();
vi.mock("#/hooks/query/use-batch-feedback", () => ({
  useBatchFeedback: () => useBatchFeedbackMock(),
}));

const useAutoNavigateToAppMock = vi.fn();
vi.mock("#/hooks/use-auto-navigate-to-app", () => ({
  useAutoNavigateToApp: () => useAutoNavigateToAppMock(),
}));

const useDocumentTitleFromStateMock = vi.fn();
vi.mock("#/hooks/use-document-title-from-state", () => ({
  useDocumentTitleFromState: () => useDocumentTitleFromStateMock(),
}));

const settingsResult = { data: {} } as { data: Record<string, unknown> | undefined };
vi.mock("#/hooks/query/use-settings", () => ({
  useSettings: () => settingsResult,
}));

const activeConversationResult = {
  data: { conversation_id: "conv-123", status: "RUNNING" },
  isFetched: true,
  refetch: vi.fn(),
};
vi.mock("#/hooks/query/use-active-conversation", () => ({
  useActiveConversation: () => activeConversationResult,
}));

const isAuthedResult = { data: true } as { data: boolean | undefined };
vi.mock("#/hooks/query/use-is-authed", () => ({
  useIsAuthed: () => isAuthedResult,
}));

const userProvidersResult = { providers: [] as string[] };
vi.mock("#/hooks/use-user-providers", () => ({
  useUserProviders: () => userProvidersResult,
}));

const displayErrorToastMock = vi.fn();
vi.mock("#/utils/custom-toast-handlers", () => ({
  displayErrorToast: (...args: unknown[]) => displayErrorToastMock(...args),
}));

const { clearTerminalMock, clearJupyterMock } = vi.hoisted(() => {
  const clearTerminalMock = vi.fn(() => ({ type: "clear-terminal" }));
  const clearJupyterMock = vi.fn(() => ({ type: "clear-jupyter" }));
  return { clearTerminalMock, clearJupyterMock };
});

vi.mock("#/state/command-slice", () => ({
  clearTerminal: clearTerminalMock,
}));

vi.mock("#/state/jupyter-slice", () => ({
  clearJupyter: clearJupyterMock,
}));

vi.mock("#/hooks/use-effect-once", () => ({
  useEffectOnce: (callback: () => void) => {
    React.useEffect(() => {
      callback();
    }, []);
  },
}));

const startConversationMock = vi.fn((...args: any[]) => Promise.resolve());
vi.mock("#/api/forge", () => ({
  default: {
    startConversation: (...args: unknown[]) => startConversationMock(...args),
  },
}));

vi.mock("#/context/task-context", () => ({
  TaskProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="task-provider">{children}</div>
  ),
}));

vi.mock("#/context/conversation-subscriptions-provider", () => ({
  ConversationSubscriptionsProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="subscriptions-provider">{children}</div>
  ),
}));

vi.mock("#/context/ws-client-provider", () => ({
  WsClientProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="ws-client">{children}</div>
  ),
}));

vi.mock("#/components/features/conversation/conversation-tabs", () => ({
  ConversationTabs: () => <div data-testid="conversation-tabs" />,
}));

vi.mock("#/components/layout/resizable-panel", () => ({
  Orientation: { HORIZONTAL: "horizontal" },
  ResizablePanel: ({ firstChild, secondChild }: { firstChild: React.ReactNode; secondChild: React.ReactNode }) => (
    <div data-testid="resizable-panel">
      <div data-testid="resizable-first">{firstChild}</div>
      <div data-testid="resizable-second">{secondChild}</div>
    </div>
  ),
}));

vi.mock("../../src/components/features/chat/chat-interface", () => ({
  ChatInterface: () => <div data-testid="chat-interface" />,
}));

vi.mock("../../src/wrapper/event-handler", () => ({
  EventHandler: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="event-handler">{children}</div>
  ),
}));

const originalInnerWidth = window.innerWidth;

describe("conversation route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    cleanup();
    window.innerWidth = originalInnerWidth;
    useConversationIdMock.mockReturnValue({ conversationId: "conv-123" });
    settingsResult.data = { theme: "dark" };
    activeConversationResult.data = { conversation_id: "conv-123", status: "RUNNING" };
    activeConversationResult.isFetched = true;
    activeConversationResult.refetch = vi.fn();
    isAuthedResult.data = true;
    userProvidersResult.providers = ["mock-provider"];
  });

  afterEach(() => {
    window.innerWidth = originalInnerWidth;
    cleanup();
  });

  const renderApp = () => render(<App />);

  it("displays error and navigates home when conversation is missing", async () => {
    activeConversationResult.data = null as any;
    renderApp();

    await waitFor(() => {
      expect(displayErrorToastMock).toHaveBeenCalledWith(
        "This conversation does not exist, or you do not have permission to access it.",
      );
    });
    expect(navigateMock).toHaveBeenCalledWith("/");
    expect(useConversationConfigMock).toHaveBeenCalled();
    expect(useBatchFeedbackMock).toHaveBeenCalled();
    expect(useAutoNavigateToAppMock).toHaveBeenCalled();
  });

  it("restarts stopped conversations", async () => {
    activeConversationResult.data = { conversation_id: "conv-stopped", status: "STOPPED" } as any;

    renderApp();

    await waitFor(() => expect(startConversationMock).toHaveBeenCalledWith("conv-stopped", ["mock-provider"]));
    expect(activeConversationResult.refetch).toHaveBeenCalled();
  });

  it("dispatches clear actions on mount and conversation change", async () => {
    const { rerender } = renderApp();

    await waitFor(() => expect(dispatchMock).toHaveBeenCalledTimes(4));
    expect(dispatchMock).toHaveBeenNthCalledWith(1, { type: "clear-terminal" });
    expect(dispatchMock).toHaveBeenNthCalledWith(2, { type: "clear-jupyter" });

    useConversationIdMock.mockReturnValue({ conversationId: "conv-456" });
    rerender(<App />);

    await waitFor(() => expect(dispatchMock).toHaveBeenCalledTimes(6));
    expect(dispatchMock).toHaveBeenNthCalledWith(5, { type: "clear-terminal" });
    expect(dispatchMock).toHaveBeenNthCalledWith(6, { type: "clear-jupyter" });
  });

  it("switches between desktop and mobile layouts on resize", async () => {
    window.innerWidth = 1400;
    const { container } = renderApp();

    expect(await screen.findByTestId("resizable-panel")).toBeInTheDocument();

    window.innerWidth = 800;
    window.dispatchEvent(new Event("resize"));

    await waitFor(() => expect(screen.queryByTestId("resizable-panel")).toBeNull());
    const stackedLayout = Array.from(container.querySelectorAll("div")).find((node) =>
      node.className.includes("flex") && node.className.includes("flex-col") && node.className.includes("gap-3"),
    );
    expect(stackedLayout).not.toBeNull();
  });

  it("cleans up resize listeners on unmount", () => {
    const addSpy = vi.spyOn(window, "addEventListener");
    const removeSpy = vi.spyOn(window, "removeEventListener");

    const { unmount } = renderApp();

    expect(addSpy).toHaveBeenCalledWith("resize", expect.any(Function));
    unmount();
    expect(removeSpy).toHaveBeenCalledWith("resize", expect.any(Function));

    addSpy.mockRestore();
    removeSpy.mockRestore();
  });

  it("logs settings in development mode", () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = "development";
    settingsResult.data = { theme: "dev" };
    const consoleSpy = vi.spyOn(console, "debug").mockImplementation(() => {});

    renderApp();

    expect(consoleSpy).toHaveBeenCalledWith("dev settings:", { theme: "dev" });

    consoleSpy.mockRestore();
    process.env.NODE_ENV = originalEnv;
  });
});
