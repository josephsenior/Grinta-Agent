import { screen } from "@testing-library/react";
import { useParams } from "react-router-dom";
import { vi, describe, test, expect, beforeEach } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import { ChatInterface } from "./chat-interface";
import { useWsClient } from "#/context/ws-client-provider";
import { useOptimisticUserMessage } from "#/hooks/use-optimistic-user-message";
import { useWSErrorMessage } from "#/hooks/use-ws-error-message";
import { useConfig } from "#/hooks/query/use-config";
import { useGetTrajectory } from "#/hooks/mutation/use-get-trajectory";
import { useUploadFiles } from "#/hooks/mutation/use-upload-files";
import { ForgeAction } from "#/types/core/actions";
import { renderWithProviders } from "../../../../test-utils";

// Mock the hooks
vi.mock("#/context/ws-client-provider");
vi.mock("#/hooks/use-optimistic-user-message");
vi.mock("#/hooks/use-ws-error-message");
vi.mock("react-router");
vi.mock("#/hooks/query/use-config");
vi.mock("#/hooks/mutation/use-get-trajectory");
vi.mock("#/hooks/mutation/use-upload-files");
vi.mock("react-redux", async () => {
  const actual =
    await vi.importActual<typeof import("react-redux")>("react-redux");
  return {
    ...actual,
    useSelector: vi.fn(() => ({
      curAgentState: "AWAITING_USER_INPUT",
      selectedRepository: null,
      replayJson: null,
    })),
    useDispatch: vi.fn(() => vi.fn()),
  };
});

describe("ChatInterface", () => {
  // Helper to cast imported mocks to vitest mock objects for easier stubbing
  const asViMock = (fn: unknown) => fn as ReturnType<typeof vi.fn>;

  // Create a new QueryClient for each test
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });

    // Default mock implementations
    asViMock(useWsClient).mockReturnValue({
      send: vi.fn(),
      isLoadingMessages: false,
      parsedEvents: [],
      hydratedEventIds: new Set(),
    });
    asViMock(useOptimisticUserMessage).mockReturnValue({
      setOptimisticUserMessage: vi.fn(),
      getOptimisticUserMessage: vi.fn(() => null),
    });
    asViMock(useWSErrorMessage).mockReturnValue({
      getErrorMessage: vi.fn(() => null),
      setErrorMessage: vi.fn(),
      removeErrorMessage: vi.fn(),
    });
    asViMock(useParams).mockReturnValue({
      conversationId: "test-id",
    });
    asViMock(useConfig).mockReturnValue({
      data: { APP_MODE: "local" },
    });
    asViMock(useGetTrajectory).mockReturnValue({
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
      isLoading: false,
    });
    asViMock(useUploadFiles).mockReturnValue({
      mutateAsync: vi
        .fn()
        .mockResolvedValue({ skipped_files: [], uploaded_files: [] }),
      isLoading: false,
    });
  });

  // Helper function to render with QueryClientProvider
  const renderChatInterface = (ui: React.ReactElement) =>
    renderWithProviders(ui, { queryClient });

  test("should show chat suggestions when there are no events", () => {
    asViMock(useWsClient).mockReturnValue({
      send: vi.fn(),
      isLoadingMessages: false,
      parsedEvents: [],
      hydratedEventIds: new Set(),
    });

    renderChatInterface(<ChatInterface />);

    // ChatSuggestions were removed from the ChatInterface UI. Ensure no suggestions
    // container is present to match the current component behavior.
    expect(screen.queryByTestId("chat-suggestions")).not.toBeInTheDocument();
  });

  test("should show chat suggestions when there are only environment events", () => {
    const environmentEvent: ForgeAction = {
      id: 1,
      source: "environment",
      action: "system",
      args: {
        content: "source .Forge/setup.sh",
        tools: null,
        Forge_version: null,
        agent_class: null,
      },
      message: "Running setup script",
      timestamp: "2025-07-01T00:00:00Z",
    };

    asViMock(useWsClient).mockReturnValue({
      send: vi.fn(),
      isLoadingMessages: false,
      parsedEvents: [environmentEvent],
      hydratedEventIds: new Set(),
    });

    renderChatInterface(<ChatInterface />);

    // ChatSuggestions were removed from the ChatInterface UI. Ensure no suggestions
    // container is present to match the current component behavior.
    expect(screen.queryByTestId("chat-suggestions")).not.toBeInTheDocument();
  });

  test("should hide chat suggestions when there is a user message", () => {
    const userEvent: ForgeAction = {
      id: 1,
      source: "user",
      action: "message",
      args: {
        content: "Hello",
        image_urls: [],
        file_urls: [],
      },
      message: "Hello",
      timestamp: "2025-07-01T00:00:00Z",
    };

    asViMock(useWsClient).mockReturnValue({
      send: vi.fn(),
      isLoadingMessages: false,
      parsedEvents: [userEvent],
      hydratedEventIds: new Set(),
    });

    renderChatInterface(<ChatInterface />);

    // Check if ChatSuggestions is not rendered with user events
    expect(screen.queryByTestId("chat-suggestions")).not.toBeInTheDocument();
  });

  test("should hide chat suggestions when there is an optimistic user message", () => {
    asViMock(useOptimisticUserMessage).mockReturnValue({
      setOptimisticUserMessage: vi.fn(),
      getOptimisticUserMessage: vi.fn(() => "Optimistic message"),
    });

    renderChatInterface(<ChatInterface />);

    // Check if ChatSuggestions is not rendered with optimistic user message
    expect(screen.queryByTestId("chat-suggestions")).not.toBeInTheDocument();
  });
});
