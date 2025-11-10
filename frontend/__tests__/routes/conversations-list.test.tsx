import React from "react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ConversationsList, { hydrateFallback } from "#/routes/conversations-list";

const navigateMock = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => navigateMock,
}));

vi.mock("lucide-react", () => ({
  MessageSquare: () => <svg data-testid="message-square" />,
  ChevronRight: () => <svg data-testid="chevron-right" />,
}));

vi.mock("#/components/shared/ClientFormattedDate", () => ({
  __esModule: true,
  default: ({ iso }: { iso: string }) => <span data-testid="formatted-date">{iso}</span>,
}));

const paginatedConversationsMock = vi.fn();
vi.mock("#/hooks/query/use-paginated-conversations", () => ({
  usePaginatedConversations: (...args: unknown[]) => paginatedConversationsMock(...args),
}));

describe("conversations list route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    paginatedConversationsMock.mockReset();
  });

  const renderScreen = () => render(<ConversationsList />);

  it("shows loading state", () => {
    paginatedConversationsMock.mockReturnValue({ isLoading: true });

    renderScreen();

    expect(screen.getByText(/Loading conversations/i)).toBeInTheDocument();
  });

  it("shows error state", () => {
    paginatedConversationsMock.mockReturnValue({ isLoading: false, isError: true });

    renderScreen();

    expect(screen.getByText(/Failed to load conversations/i)).toBeInTheDocument();
  });

  it("renders conversations and navigates on click", async () => {
    paginatedConversationsMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        pages: [
          {
            results: [
              {
                conversation_id: "abc123456789",
                title: "Planning Session",
                selected_repository: "repo/name",
                created_at: "2025-01-01T00:00:00Z",
              },
            ],
          },
        ],
      },
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    });

    renderScreen();

    expect(await screen.findByTestId("conversations-list")).toBeInTheDocument();
    expect(screen.getByText("Planning Session")).toBeInTheDocument();
    expect(screen.getByText("repo/name")).toBeInTheDocument();
    expect(screen.getByTestId("formatted-date")).toHaveTextContent("2025-01-01T00:00:00Z");

    await userEvent.click(screen.getByRole("button", { name: /Planning Session/i }));
    expect(navigateMock).toHaveBeenCalledWith("/conversations/abc123456789");
  });

  it("falls back to generated title when missing", async () => {
    paginatedConversationsMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        pages: [
          {
            results: [
              {
                conversation_id: "abcdef123456",
                title: "",
                selected_repository: null,
                created_at: "2025-02-02T00:00:00Z",
              },
            ],
          },
        ],
      },
      hasNextPage: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
    });

    renderScreen();

    expect(await screen.findByText(/Conversation abcdef12/i)).toBeInTheDocument();
  });

  it("loads more conversations when paginating", async () => {
    const fetchNextPage = vi.fn();
    paginatedConversationsMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: { pages: [{ results: [] }] },
      hasNextPage: true,
      fetchNextPage,
      isFetchingNextPage: false,
    });

    renderScreen();

    const loadMoreButton = await screen.findByRole("button", { name: /Load more/i });
    await userEvent.click(loadMoreButton);

    expect(fetchNextPage).toHaveBeenCalled();
  });

  it("disables load more while fetching", () => {
    paginatedConversationsMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: { pages: [{ results: [] }] },
      hasNextPage: true,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: true,
    });

    renderScreen();

    const loadMoreButton = screen.getByRole("button", { name: /Loading…/i });
    expect(loadMoreButton).toBeDisabled();
  });

  it("exports hydrate fallback markup", () => {
    const { container } = render(<div>{hydrateFallback}</div>);
    const fallback = container.querySelector(".route-loading");
    expect(fallback).toBeInTheDocument();
    expect(fallback?.getAttribute("aria-hidden")).toBe("true");
  });
});
