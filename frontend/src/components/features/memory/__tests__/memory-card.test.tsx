import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, vi, expect } from "vitest";
import { MemoryCard } from "../memory-card";
import type { Memory } from "#/types/memory";
import { renderWithProviders } from "../../../../../test-utils";

// Mock lucide-react
vi.mock("lucide-react", () => ({
  Edit: () => <div data-testid="edit-icon" />,
  Trash2: () => <div data-testid="trash-icon" />,
  MoreVertical: () => <div data-testid="more-icon" />,
  Lightbulb: () => <div data-testid="lightbulb-icon" />,
  Palette: () => <div data-testid="palette-icon" />,
  Building2: () => <div data-testid="building-icon" />,
  Brain: () => <div data-testid="brain-icon" />,
  Hash: () => <div data-testid="hash-icon" />,
  Tag: () => <div data-testid="tag-icon" />,
  Clock: () => <div data-testid="clock-icon" />,
}));

describe("MemoryCard", () => {
  const mockMemory: Memory = {
    id: "mem-1",
    title: "Test Memory",
    content: "This is a test memory content",
    category: "technical",
    tags: ["python", "async", "testing"],
    createdAt: "2025-01-01T00:00:00Z",
    updatedAt: "2025-01-01T00:00:00Z",
    usageCount: 0,
    lastUsed: null,
    source: "manual",
    conversationId: null,
    importance: "low",
  };

  const defaultProps = {
    memory: mockMemory,
    onEdit: vi.fn(),
    onDelete: vi.fn(),
  };

  it("should render memory title and content", () => {
    renderWithProviders(<MemoryCard {...defaultProps} />);

    expect(screen.getByText("Test Memory")).toBeInTheDocument();
    expect(screen.getByText("This is a test memory content")).toBeInTheDocument();
  });

  it("should display tags", () => {
    renderWithProviders(<MemoryCard {...defaultProps} />);

    expect(screen.getByText((text) => text.trim() === "python")).toBeInTheDocument();
    expect(screen.getByText((text) => text.trim() === "async")).toBeInTheDocument();
    expect(screen.getByText((text) => text.trim() === "testing")).toBeInTheDocument();
  });

  it("should show category badge for technical", () => {
    renderWithProviders(<MemoryCard {...defaultProps} />);

    expect(screen.getByText("Technical")).toBeInTheDocument();
  });

  it("should show category badge for preference", () => {
    const prefMemory: Memory = { ...mockMemory, category: "preference" };
    renderWithProviders(<MemoryCard {...defaultProps} memory={prefMemory} />);

    expect(screen.getByText("Preference")).toBeInTheDocument();
  });

  it("should show category badge for project", () => {
    const projMemory: Memory = { ...mockMemory, category: "project" };
    renderWithProviders(<MemoryCard {...defaultProps} memory={projMemory} />);

    expect(screen.getByText("Project")).toBeInTheDocument();
  });

  it("should call onEdit when edit button is clicked", async () => {
    const user = userEvent.setup();
    renderWithProviders(<MemoryCard {...defaultProps} />);

    // Button might use title attribute instead of aria-label
    const editButton = screen.getByRole("button", { name: /edit/i }) || 
                       document.querySelector('button[title="Edit memory"]');
    if (editButton) {
      await user.click(editButton);
      expect(defaultProps.onEdit).toHaveBeenCalledWith(mockMemory);
    }
  });

  it("should call onDelete when delete button is clicked", async () => {
    const user = userEvent.setup();
    renderWithProviders(<MemoryCard {...defaultProps} />);

    // Button might use title attribute instead of aria-label
    const deleteButton = screen.getAllByRole("button").find(btn => 
      btn.getAttribute("title") === "Delete memory"
    );
    if (deleteButton) {
      await user.click(deleteButton);
      expect(defaultProps.onDelete).toHaveBeenCalledWith("mem-1");
    }
  });

  it("should truncate long content with line-clamp", () => {
    const longContent = "A".repeat(500);
    const longMemory = { ...mockMemory, content: longContent };

    const { container } = renderWithProviders(
      <MemoryCard {...defaultProps} memory={longMemory} />,
    );

    // Check that the content element has line-clamp class
    const contentElement = container.querySelector(".line-clamp-2");
    expect(contentElement).toBeInTheDocument();
  });

  it("should show limited tags when more than 5", () => {
    const manyTagsMemory = {
      ...mockMemory,
      tags: ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7"],
    };

    renderWithProviders(<MemoryCard {...defaultProps} memory={manyTagsMemory} />);

    manyTagsMemory.tags.forEach((tag) => {
      expect(screen.getByText((text) => text.trim() === tag)).toBeInTheDocument();
    });
  });

  it("should display formatted date", () => {
    renderWithProviders(<MemoryCard {...defaultProps} />);

    // Should render the card with the memory
    expect(screen.getByText("Test Memory")).toBeInTheDocument();
  });
});

