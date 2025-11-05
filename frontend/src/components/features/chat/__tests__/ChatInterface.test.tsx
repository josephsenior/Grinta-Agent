import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { BrowserRouter } from "react-router-dom";
import { configureStore } from "@reduxjs/toolkit";
import { ChatInterfaceRefactored } from "../chat-interface-refactored";
import { TaskProvider } from "#/context/task-context";

// Mock dependencies
jest.mock("#/hooks/use-chat-interface-state");
jest.mock("#/hooks/use-chat-keyboard-shortcuts");
jest.mock("#/hooks/use-chat-message-handlers");
jest.mock("#/hooks/use-chat-feedback-actions");
jest.mock("#/utils/use-filtered-events");

// Mock store
const mockStore = configureStore({
  reducer: {
    agent: () => ({ curAgentState: "IDLE" }),
    metrics: () => ({ totalCost: 0, totalTokens: 0 }),
  },
});

// Mock hooks
const mockUseChatInterfaceState = require("#/hooks/use-chat-interface-state").useChatInterfaceState;
const mockUseChatKeyboardShortcuts = require("#/hooks/use-chat-keyboard-shortcuts").useChatKeyboardShortcuts;
const mockUseChatMessageHandlers = require("#/hooks/use-chat-message-handlers").useChatMessageHandlers;
const mockUseChatFeedbackActions = require("#/hooks/use-chat-feedback-actions").useChatFeedbackActions;
const mockUseFilteredEvents = require("#/utils/use-filtered-events").useFilteredEvents;

describe("ChatInterfaceRefactored", () => {
  const defaultMockState = {
    curAgentState: "IDLE",
    isAwaitingUserConfirmation: false,
    parsedEvents: [],
    isLoadingMessages: false,
    tasks: [],
    isTaskPanelOpen: false,
    toggleTaskPanel: jest.fn(),
    config: {},
    t: (key: string) => key,
    navigate: jest.fn(),
    send: jest.fn(),
    uploadFiles: jest.fn(),
    scrollRef: { current: null },
    scrollDomToBottom: jest.fn(),
    onChatBodyScroll: jest.fn(),
    hitBottom: false,
    autoScroll: true,
    setAutoScroll: jest.fn(),
    setHitBottom: jest.fn(),
    isMobileMenuOpen: false,
    setIsMobileMenuOpen: jest.fn(),
    messageToSend: "",
    setMessageToSend: jest.fn(),
    lastUserMessage: null,
    setLastUserMessage: jest.fn(),
    showShortcutsPanel: false,
    setShowShortcutsPanel: jest.fn(),
    isInputFocused: false,
    setIsInputFocused: jest.fn(),
    showOrchestrationPanel: false,
    setShowOrchestrationPanel: jest.fn(),
    showTechnicalDetails: false,
    setShowTechnicalDetails: jest.fn(),
    steps: [],
    isOrchestrating: false,
    hasSteps: false,
    optimisticUserMessage: null,
    errorMessage: null,
    setOptimisticUserMessage: jest.fn(),
    getOptimisticUserMessage: jest.fn(),
  };

  const defaultMockKeyboardShortcuts = {
    isSearchOpen: false,
    setIsSearchOpen: jest.fn(),
    bookmarksHook: {
      isOpen: false,
      setIsOpen: jest.fn(),
    },
  };

  const defaultMockMessageHandlers = {
    handleSendMessage: jest.fn(),
    handleStop: jest.fn(),
    handleAskAboutCode: jest.fn(),
    handleRunCode: jest.fn(),
    handleGoBack: jest.fn(),
  };

  const defaultMockFeedbackActions = {
    feedbackPolarity: "positive" as const,
    setFeedbackPolarity: jest.fn(),
    feedbackModalIsOpen: false,
    setFeedbackModalIsOpen: jest.fn(),
    onClickShareFeedbackActionButton: jest.fn(),
    onClickExportTrajectoryButton: jest.fn(),
  };

  beforeEach(() => {
    mockUseChatInterfaceState.mockReturnValue(defaultMockState);
    mockUseChatKeyboardShortcuts.mockReturnValue(defaultMockKeyboardShortcuts);
    mockUseChatMessageHandlers.mockReturnValue(defaultMockMessageHandlers);
    mockUseChatFeedbackActions.mockReturnValue(defaultMockFeedbackActions);
    mockUseFilteredEvents.mockReturnValue([]);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  const renderWithProviders = (component: React.ReactElement) => {
    return render(
      <Provider store={mockStore}>
        <BrowserRouter>
          <TaskProvider>
            {component}
          </TaskProvider>
        </BrowserRouter>
      </Provider>
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
      expect.any(Function) // setShowShortcutsPanel
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
      undefined // conversationId
    );
  });

  it("shows task panel when tasks are present", () => {
    const mockStateWithTasks = {
      ...defaultMockState,
      tasks: [
        { id: "1", title: "Test task", status: "todo" },
      ],
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
    
    expect(defaultMockKeyboardShortcuts.setIsSearchOpen).toHaveBeenCalledWith(true);
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
