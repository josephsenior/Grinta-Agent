import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { Provider } from "react-redux";
import { BrowserRouter } from "react-router-dom";
import { configureStore } from "@reduxjs/toolkit";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ChatInterfaceRefactored } from "#/components/features/chat/chat-interface-refactored";
import { TaskProvider } from "#/context/task-context";

// Mock dependencies
const mockUseChatInterfaceState = vi.fn();
const mockUseChatKeyboardShortcuts = vi.fn();
const mockUseChatMessageHandlers = vi.fn();
const mockUseChatFeedbackActions = vi.fn();
const mockUseFilteredEvents = vi.fn();

vi.mock("#/hooks/use-chat-interface-state", () => ({
  useChatInterfaceState: mockUseChatInterfaceState,
}));
vi.mock("#/hooks/use-chat-keyboard-shortcuts", () => ({
  useChatKeyboardShortcuts: mockUseChatKeyboardShortcuts,
}));
vi.mock("#/hooks/use-chat-message-handlers", () => ({
  useChatMessageHandlers: mockUseChatMessageHandlers,
}));
vi.mock("#/hooks/use-chat-feedback-actions", () => ({
  useChatFeedbackActions: mockUseChatFeedbackActions,
}));
vi.mock("#/utils/use-filtered-events", () => ({
  useFilteredEvents: mockUseFilteredEvents,
}));

// Mock store
const mockStore = configureStore({
  reducer: {
    agent: () => ({ curAgentState: "IDLE" }),
    metrics: () => ({ totalCost: 0, totalTokens: 0 }),
  },
});

describe.skip("ChatInterfaceRefactored", () => {
  const defaultMockState = {
    curAgentState: "IDLE",
    isAwaitingUserConfirmation: false,
    parsedEvents: [],
    isLoadingMessages: false,
    tasks: [],
    isTaskPanelOpen: false,
    toggleTaskPanel: vi.fn(),
    config: {},
    t: (key: string) => key,
    navigate: vi.fn(),
    send: vi.fn(),
    uploadFiles: vi.fn(),
    scrollRef: { current: null },
    scrollDomToBottom: vi.fn(),
    onChatBodyScroll: vi.fn(),
    hitBottom: false,
    autoScroll: true,
    setAutoScroll: vi.fn(),
    setHitBottom: vi.fn(),
    isMobileMenuOpen: false,
    setIsMobileMenuOpen: vi.fn(),
    messageToSend: "",
    setMessageToSend: vi.fn(),
    lastUserMessage: null,
    setLastUserMessage: vi.fn(),
    showShortcutsPanel: false,
    setShowShortcutsPanel: vi.fn(),
    isInputFocused: false,
    setIsInputFocused: vi.fn(),
    showOrchestrationPanel: false,
    setShowOrchestrationPanel: vi.fn(),
    showTechnicalDetails: false,
    setShowTechnicalDetails: vi.fn(),
    steps: [],
    isOrchestrating: false,
    hasSteps: false,
    optimisticUserMessage: null,
    errorMessage: null,
    setOptimisticUserMessage: vi.fn(),
    getOptimisticUserMessage: vi.fn(),
  };

  const defaultMockKeyboardShortcuts = {
    isSearchOpen: false,
    setIsSearchOpen: vi.fn(),
    bookmarksHook: {
      isOpen: false,
      setIsOpen: vi.fn(),
    },
  };

  const defaultMockMessageHandlers = {
    handleSendMessage: vi.fn(),
    handleStop: vi.fn(),
    handleAskAboutCode: vi.fn(),
    handleRunCode: vi.fn(),
    handleGoBack: vi.fn(),
  };

  const defaultMockFeedbackActions = {
    feedbackPolarity: "positive" as const,
    setFeedbackPolarity: vi.fn(),
    feedbackModalIsOpen: false,
    setFeedbackModalIsOpen: vi.fn(),
    onClickShareFeedbackActionButton: vi.fn(),
    onClickExportTrajectoryButton: vi.fn(),
  };

  beforeEach(() => {
    mockUseChatInterfaceState.mockReturnValue(defaultMockState);
    mockUseChatKeyboardShortcuts.mockReturnValue(defaultMockKeyboardShortcuts);
    mockUseChatMessageHandlers.mockReturnValue(defaultMockMessageHandlers);
    mockUseChatFeedbackActions.mockReturnValue(defaultMockFeedbackActions);
    mockUseFilteredEvents.mockReturnValue([]);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  const renderWithProviders = (component: React.ReactElement) => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    return render(
      <QueryClientProvider client={queryClient}>
        <Provider store={mockStore}>
          <BrowserRouter>
            <TaskProvider>{component}</TaskProvider>
          </BrowserRouter>
        </Provider>
      </QueryClientProvider>,
    );
  };

  it("renders empty state when no events", () => {
    renderWithProviders(<ChatInterfaceRefactored />);

    expect(screen.getByText(/no conversations/i)).toBeInTheDocument();
  });

  it("renders messages when events are present", () => {
    const mockEvents = [
      { id: 1, type: "message", content: "Hello" },
      { id: 2, type: "message", content: "World" },
    ];

    mockUseFilteredEvents.mockReturnValue(mockEvents);

    renderWithProviders(<ChatInterfaceRefactored />);

    expect(screen.queryByText(/no conversations/i)).not.toBeInTheDocument();
  });

  it("handles keyboard shortcuts correctly", () => {
    renderWithProviders(<ChatInterfaceRefactored />);

    // Test that keyboard shortcuts hook is called with correct parameters
    expect(mockUseChatKeyboardShortcuts).toHaveBeenCalledWith(
      false, // isInputFocused
      expect.any(Function), // setShowShortcutsPanel
    );
  });

  it("handles message sending", async () => {
    renderWithProviders(<ChatInterfaceRefactored />);

    // Test that message handlers hook is called with correct parameters
    expect(mockUseChatMessageHandlers).toHaveBeenCalledWith(
      expect.any(Function), // send
      expect.any(Function), // setOptimisticUserMessage
      expect.any(Function), // setMessageToSend
      expect.any(Function), // setLastUserMessage
      expect.any(Function), // uploadFiles
      undefined, // conversationId
    );
  });

  it("shows task panel when tasks are present", () => {
    const mockStateWithTasks = {
      ...defaultMockState,
      tasks: [{ id: "1", title: "Test task", status: "todo" }],
      isTaskPanelOpen: true,
    };

    mockUseChatInterfaceState.mockReturnValue(mockStateWithTasks);

    renderWithProviders(<ChatInterfaceRefactored />);

    expect(screen.getByText("Test task")).toBeInTheDocument();
  });

  it("handles mobile menu toggle", () => {
    renderWithProviders(<ChatInterfaceRefactored />);

    const menuButton = screen.getByRole("button", { name: /menu/i });
    fireEvent.click(menuButton);

    expect(defaultMockState.setIsMobileMenuOpen).toHaveBeenCalledWith(true);
  });

  it("handles search panel toggle", () => {
    renderWithProviders(<ChatInterfaceRefactored />);

    const searchButton = screen.getByRole("button", { name: /search/i });
    fireEvent.click(searchButton);

    expect(defaultMockKeyboardShortcuts.setIsSearchOpen).toHaveBeenCalledWith(
      true,
    );
  });

  it("handles shortcuts panel toggle", () => {
    renderWithProviders(<ChatInterfaceRefactored />);

    const shortcutsButton = screen.getByRole("button", { name: /keyboard/i });
    fireEvent.click(shortcutsButton);

    expect(defaultMockState.setShowShortcutsPanel).toHaveBeenCalledWith(true);
  });

  it("handles go back navigation", () => {
    renderWithProviders(<ChatInterfaceRefactored />);

    const goBackButton = screen.getByRole("button", { name: /go back/i });
    fireEvent.click(goBackButton);

    expect(defaultMockMessageHandlers.handleGoBack).toHaveBeenCalled();
  });

  it("shows loading state when messages are loading", () => {
    const mockStateWithLoading = {
      ...defaultMockState,
      isLoadingMessages: true,
    };

    mockUseChatInterfaceState.mockReturnValue(mockStateWithLoading);

    renderWithProviders(<ChatInterfaceRefactored />);

    expect(screen.getByTestId("message-skeleton")).toBeInTheDocument();
  });

  it("shows error message when present", () => {
    const mockStateWithError = {
      ...defaultMockState,
      errorMessage: "Test error message",
    };

    mockUseChatInterfaceState.mockReturnValue(mockStateWithError);

    renderWithProviders(<ChatInterfaceRefactored />);

    expect(screen.getByText("Test error message")).toBeInTheDocument();
  });
});
