import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { Provider } from "react-redux";
import { BrowserRouter } from "react-router-dom";
import { configureStore } from "@reduxjs/toolkit";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
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

