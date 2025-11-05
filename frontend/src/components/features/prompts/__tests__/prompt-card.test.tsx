import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, vi, expect } from "vitest";
import { PromptCard } from "../prompt-card";
import { PromptCategory, type PromptTemplate } from "#/types/prompt";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, params?: any) => {
      if (key === "PROMPTS$USED_COUNT") {
        return `Used ${params?.count} times`;
      }
      return key;
    },
  }),
}));

// Mock lucide-react
vi.mock("lucide-react", () => ({
  BookOpen: () => <div data-testid="book-icon" />,
  Code: () => <div data-testid="code-icon" />,
  Edit: () => <div data-testid="edit-icon" />,
  FileText: () => <div data-testid="file-icon" />,
  Heart: ({ className }: any) => <div data-testid="heart-icon" className={className} />,
  MoreVertical: () => <div data-testid="more-icon" />,
  Star: () => <div data-testid="star-icon" />,
  Trash2: () => <div data-testid="trash-icon" />,
  Copy: () => <div data-testid="copy-icon" />,
}));

describe("PromptCard", () => {
  const mockPrompt: PromptTemplate = {
    id: "test-prompt-1",
    title: "Test Prompt",
    description: "This is a test prompt description",
    category: PromptCategory.CODING,
    content: "Write a {{language}} function to {{task}}",
    variables: [
      { name: "language", description: "Programming language", required: true },
      { name: "task", description: "What to do", required: true },
    ],
    tags: ["test", "coding", "example"],
    is_favorite: false,
    usage_count: 5,
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-01T00:00:00Z",
    metadata: {},
  };

  const defaultProps = {
    prompt: mockPrompt,
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    onUse: vi.fn(),
    onToggleFavorite: vi.fn(),
  };

  it("should render prompt title and description", () => {
    render(<PromptCard {...defaultProps} />);

    expect(screen.getByText("Test Prompt")).toBeInTheDocument();
    expect(screen.getByText("This is a test prompt description")).toBeInTheDocument();
  });

  it("should display prompt content preview", () => {
    render(<PromptCard {...defaultProps} />);

    expect(screen.getByText(/Write a {{language}} function/)).toBeInTheDocument();
  });

  it("should show tags", () => {
    render(<PromptCard {...defaultProps} />);

    expect(screen.getByText("#test")).toBeInTheDocument();
    expect(screen.getByText("#coding")).toBeInTheDocument();
    expect(screen.getByText("#example")).toBeInTheDocument();
  });

  it("should display usage count", () => {
    render(<PromptCard {...defaultProps} />);

    expect(screen.getByText("Used 5 times")).toBeInTheDocument();
  });

  it("should show favorite icon when is_favorite is true", () => {
    const favoritePrompt = { ...mockPrompt, is_favorite: true };
    render(<PromptCard {...defaultProps} prompt={favoritePrompt} />);

    const heartIcon = screen.getByTestId("heart-icon");
    expect(heartIcon).toHaveClass("fill-red-500");
  });

  it("should call onUse when use button is clicked", async () => {
    const user = userEvent.setup();
    render(<PromptCard {...defaultProps} />);

    const useButton = screen.getByText("PROMPTS$USE_PROMPT");
    await user.click(useButton);

    expect(defaultProps.onUse).toHaveBeenCalledWith(mockPrompt);
  });

  it("should open menu when more button is clicked", async () => {
    const user = userEvent.setup();
    render(<PromptCard {...defaultProps} />);

    const moreButton = screen.getByLabelText("More options");
    await user.click(moreButton);

    await waitFor(() => {
      expect(screen.getByText("PROMPTS$EDIT")).toBeInTheDocument();
      expect(screen.getByText("PROMPTS$COPY")).toBeInTheDocument();
      expect(screen.getByText("PROMPTS$DELETE")).toBeInTheDocument();
    });
  });

  it("should call onEdit when edit is clicked from menu", async () => {
    const user = userEvent.setup();
    render(<PromptCard {...defaultProps} />);

    const moreButton = screen.getByLabelText("More options");
    await user.click(moreButton);

    const editButton = await screen.findByText("PROMPTS$EDIT");
    await user.click(editButton);

    expect(defaultProps.onEdit).toHaveBeenCalledWith(mockPrompt);
  });

  it("should call onDelete when delete is clicked from menu", async () => {
    const user = userEvent.setup();
    render(<PromptCard {...defaultProps} />);

    const moreButton = screen.getByLabelText("More options");
    await user.click(moreButton);

    const deleteButton = await screen.findByText("PROMPTS$DELETE");
    await user.click(deleteButton);

    expect(defaultProps.onDelete).toHaveBeenCalledWith("test-prompt-1");
  });

  it("should call onToggleFavorite when favorite is clicked from menu", async () => {
    const user = userEvent.setup();
    render(<PromptCard {...defaultProps} />);

    const moreButton = screen.getByLabelText("More options");
    await user.click(moreButton);

    const favoriteButton = await screen.findByText("PROMPTS$ADD_FAVORITE");
    await user.click(favoriteButton);

    expect(defaultProps.onToggleFavorite).toHaveBeenCalledWith("test-prompt-1", true);
  });

  it("should copy to clipboard when copy is clicked", async () => {
    const user = userEvent.setup();
    
    // Mock clipboard API
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(),
      },
    });

    render(<PromptCard {...defaultProps} />);

    const moreButton = screen.getByLabelText("More options");
    await user.click(moreButton);

    const copyButton = await screen.findByText("PROMPTS$COPY");
    await user.click(copyButton);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockPrompt.content);
  });

  it("should close menu when clicking outside", async () => {
    const user = userEvent.setup();
    render(<PromptCard {...defaultProps} />);

    const moreButton = screen.getByLabelText("More options");
    await user.click(moreButton);

    await waitFor(() => {
      expect(screen.getByText("PROMPTS$EDIT")).toBeInTheDocument();
    });

    // Click outside (on the backdrop)
    const backdrop = screen.getByLabelText("Close menu");
    await user.click(backdrop);

    await waitFor(() => {
      expect(screen.queryByText("PROMPTS$EDIT")).not.toBeInTheDocument();
    });
  });

  it("should show limited tags with count when more than 3", () => {
    const promptWithManyTags = {
      ...mockPrompt,
      tags: ["tag1", "tag2", "tag3", "tag4", "tag5"],
    };

    render(<PromptCard {...defaultProps} prompt={promptWithManyTags} />);

    expect(screen.getByText("#tag1")).toBeInTheDocument();
    expect(screen.getByText("#tag2")).toBeInTheDocument();
    expect(screen.getByText("#tag3")).toBeInTheDocument();
    expect(screen.getByText("+2")).toBeInTheDocument();
  });

  it("should display category icon based on category type", () => {
    render(<PromptCard {...defaultProps} />);

    // Coding category should show Code icon
    expect(screen.getByTestId("code-icon")).toBeInTheDocument();
  });
});

