import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, vi, expect } from "vitest";
import { MemoryCard } from "../memory-card";
import type { Memory } from "#/types/memory";

// Mock lucide-react
vi.mock("lucide-react", () => ({
  Edit: () => <div data-testid="edit-icon" />,
  Trash2: () => <div data-testid="trash-icon" />,
  MoreVertical: () => <div data-testid="more-icon" />,
  Lightbulb: () => <div data-testid="lightbulb-icon" />,
  Palette: () => <div data-testid="palette-icon" />,
  Building2: () => <div data-testid="building-icon" />,
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
    render(<MemoryCard {...defaultProps} />);

    expect(screen.getByText("Test Memory")).toBeInTheDocument();
    expect(screen.getByText("This is a test memory content")).toBeInTheDocument();
  });

  it("should display tags", () => {
    render(<MemoryCard {...defaultProps} />);

    expect(screen.getByText("#python")).toBeInTheDocument();
    expect(screen.getByText("#async")).toBeInTheDocument();
    expect(screen.getByText("#testing")).toBeInTheDocument();
  });

  it("should show category badge for technical", () => {
    render(<MemoryCard {...defaultProps} />);

    expect(screen.getByText("Technical")).toBeInTheDocument();
  });

  it("should show category badge for preference", () => {
    const prefMemory: Memory = { ...mockMemory, category: "preference" };
    render(<MemoryCard {...defaultProps} memory={prefMemory} />);

    expect(screen.getByText("Preference")).toBeInTheDocument();
  });

  it("should show category badge for project", () => {
    const projMemory: Memory = { ...mockMemory, category: "project" };
    render(<MemoryCard {...defaultProps} memory={projMemory} />);

    expect(screen.getByText("Project")).toBeInTheDocument();
  });

  it("should call onEdit when edit button is clicked", async () => {
    const user = userEvent.setup();
    render(<MemoryCard {...defaultProps} />);

    const editButton = screen.getByLabelText("Edit memory");
    await user.click(editButton);

    expect(defaultProps.onEdit).toHaveBeenCalledWith(mockMemory);
  });

  it("should call onDelete when delete button is clicked", async () => {
    const user = userEvent.setup();
    render(<MemoryCard {...defaultProps} />);

    const deleteButton = screen.getByLabelText("Delete memory");
    await user.click(deleteButton);

    expect(defaultProps.onDelete).toHaveBeenCalledWith("mem-1");
  });

  it("should truncate long content with line-clamp", () => {
    const longContent = "A".repeat(500);
    const longMemory = { ...mockMemory, content: longContent };

    const { container } = render(<MemoryCard {...defaultProps} memory={longMemory} />);

    // Check that the content element has line-clamp class
    const contentElement = container.querySelector(".line-clamp-3");
    expect(contentElement).toBeInTheDocument();
  });

  it("should show limited tags when more than 5", () => {
    const manyTagsMemory = {
      ...mockMemory,
      tags: ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7"],
    };

    render(<MemoryCard {...defaultProps} memory={manyTagsMemory} />);

    expect(screen.getByText("#tag1")).toBeInTheDocument();
    expect(screen.getByText("#tag5")).toBeInTheDocument();
    expect(screen.getByText("+2")).toBeInTheDocument();
  });

  it("should display formatted date", () => {
    render(<MemoryCard {...defaultProps} />);

    // Should show updated_at date in some form
    expect(screen.getByText(/Updated:/)).toBeInTheDocument();
  });
});

