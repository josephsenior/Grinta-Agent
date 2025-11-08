import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import { Messages } from "#/components/features/chat/messages";
import {
  AssistantMessageAction,
  ForgeAction,
  UserMessageAction,
} from "#/types/core/actions";
import { ForgeObservation } from "#/types/core/observations";
import Forge from "#/api/forge";
import { Conversation } from "#/api/forge.types";
import { renderWithProviders } from "../../../../test-utils";

vi.mock("react-router", () => ({
  useParams: () => ({ conversationId: "123" }),
}));

// Provide a minimal ws-client-provider mock so hydratedEventIds is available
vi.mock("#/context/ws-client-provider", () => ({
  useWsClient: () => ({
    send: vi.fn(),
    status: "CONNECTED",
    isLoadingMessages: false,
    parsedEvents: [],
    // mark assistant message (id 0) as hydrated so animations don't hide it
    hydratedEventIds: new Set<string>(["0"]),
  }),
}));

let queryClient: QueryClient;

const renderMessages = ({
  messages,
}: {
  messages: (ForgeAction | ForgeObservation)[];
}) => {
  const { rerender, ...rest } = renderWithProviders(
    <Messages messages={messages} isAwaitingUserConfirmation={false} />,
    {
      queryClient,
    },
  );

  const rerenderMessages = (
    newMessages: (ForgeAction | ForgeObservation)[],
  ) => {
    rerender(
      <Messages messages={newMessages} isAwaitingUserConfirmation={false} />,
    );
  };

  return { ...rest, rerender: rerenderMessages };
};

describe("Messages", () => {
  beforeEach(() => {
    queryClient = new QueryClient();
  });

  const assistantMessage: AssistantMessageAction = {
    id: 0,
    action: "message",
    source: "agent",
    message: "Hello, Assistant!",
    timestamp: new Date().toISOString(),
    args: {
      image_urls: [],
      file_urls: [],
    thought: "Hello, Assistant!",
      wait_for_response: false,
    },
  };

  const userMessage: UserMessageAction = {
    id: 1,
    action: "message",
    source: "user",
    message: "Hello, User!",
    timestamp: new Date().toISOString(),
    args: { content: "Hello, User!", image_urls: [], file_urls: [] },
  };

  it("should render", () => {
    renderMessages({ messages: [userMessage, assistantMessage] });

    expect(screen.getByText("Hello, User!")).toBeInTheDocument();
    expect(screen.getByText("Hello, Assistant!")).toBeInTheDocument();
  });

  it("should render a launch to microagent action button on chat messages only if it is a user message", () => {
    const getConversationSpy = vi.spyOn(Forge, "getConversation");
    const mockConversation: Conversation = {
      conversation_id: "123",
      title: "Test Conversation",
      status: "RUNNING",
      runtime_status: "STATUS$READY",
      created_at: new Date().toISOString(),
      last_updated_at: new Date().toISOString(),
      selected_branch: null,
      selected_repository: null,
      git_provider: "github",
      session_api_key: null,
      url: null,
    };

    getConversationSpy.mockResolvedValue(mockConversation);

    renderMessages({
      messages: [userMessage, assistantMessage],
    });

    expect(screen.getByText("Hello, User!")).toBeInTheDocument();
    expect(screen.getByText("Hello, Assistant!")).toBeInTheDocument();
  });
});
