import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, vi, expect } from "vitest";
import { PromptFormModal } from "../prompt-form-modal";
import { PromptCategory } from "#/types/prompt";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Mock lucide-react
vi.mock("lucide-react", () => ({
  X: () => <div data-testid="x-icon" />,
  Plus: () => <div data-testid="plus-icon" />,
  Trash2: () => <div data-testid="trash-icon" />,
  HelpCircle: () => <div data-testid="help-icon" />,
}));

describe("PromptFormModal", () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onSubmit: vi.fn(),
  };

  it("should not render when isOpen is false", () => {
    render(<PromptFormModal {...defaultProps} isOpen={false} />);

    expect(screen.queryByText("PROMPTS$CREATE_PROMPT")).not.toBeInTheDocument();
  });

  it("should render create mode when no initialData", () => {
    render(<PromptFormModal {...defaultProps} />);

    expect(screen.getByText("PROMPTS$CREATE_PROMPT")).toBeInTheDocument();
    expect(screen.getByText("PROMPTS$CREATE")).toBeInTheDocument();
  });

  it("should render edit mode when initialData is provided", () => {
    const initialData = {
      id: "test-1",
      title: "Test Prompt",
      description: "Test description",
      category: PromptCategory.CODING,
      content: "Test content",
      variables: [],
      tags: [],
      is_favorite: false,
      usage_count: 0,
      created_at: "2025-01-01T00:00:00Z",
      updated_at: "2025-01-01T00:00:00Z",
      metadata: {},
    };

    render(<PromptFormModal {...defaultProps} initialData={initialData} />);

    expect(screen.getByText("PROMPTS$EDIT_PROMPT")).toBeInTheDocument();
    expect(screen.getByText("PROMPTS$UPDATE")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Test Prompt")).toBeInTheDocument();
  });

  it("should submit form with valid data", async () => {
    const user = userEvent.setup();
    render(<PromptFormModal {...defaultProps} />);

    // Fill in required fields
    const titleInput = screen.getByLabelText(/PROMPTS\$TITLE/);
    const contentInput = screen.getByLabelText(/PROMPTS\$CONTENT/);

    await user.type(titleInput, "New Prompt");
    await user.type(contentInput, "Test content here");

    // Submit form
    const submitButton = screen.getByText("PROMPTS$CREATE");
    await user.click(submitButton);

    await waitFor(() => {
      expect(defaultProps.onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "New Prompt",
          content: "Test content here",
        }),
      );
      expect(defaultProps.onClose).toHaveBeenCalled();
    });
  });

  it("should add and remove variables", async () => {
    const user = userEvent.setup();
    render(<PromptFormModal {...defaultProps} />);

    // Add variable
    const addVariableButton = screen.getByText("PROMPTS$ADD_VARIABLE");
    await user.click(addVariableButton);

    // Fill variable fields
    const nameInput = screen.getByPlaceholderText("PROMPTS$VARIABLE_NAME");
    await user.type(nameInput, "testVar");

    const defaultValueInput = screen.getByPlaceholderText(
      "PROMPTS$DEFAULT_VALUE",
    );
    await user.type(defaultValueInput, "defaultValue");

    // Remove variable
    const removeButton = screen.getByLabelText("Remove variable");
    await user.click(removeButton);

    await waitFor(() => {
      expect(screen.queryByDisplayValue("testVar")).not.toBeInTheDocument();
    });
  });

  it("should add and remove tags", async () => {
    const user = userEvent.setup();
    render(<PromptFormModal {...defaultProps} />);

    // Add tag
    const tagInput = screen.getByPlaceholderText("PROMPTS$ADD_TAG_PLACEHOLDER");
    await user.type(tagInput, "test-tag");

    const addButton = screen.getByText("PROMPTS$ADD");
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByText("#test-tag")).toBeInTheDocument();
    });

    // Remove tag
    const removeButton = screen.getByLabelText("Remove test-tag");
    await user.click(removeButton);

    await waitFor(() => {
      expect(screen.queryByText("#test-tag")).not.toBeInTheDocument();
    });
  });

  it("should add tag on Enter key press", async () => {
    const user = userEvent.setup();
    render(<PromptFormModal {...defaultProps} />);

    const tagInput = screen.getByPlaceholderText("PROMPTS$ADD_TAG_PLACEHOLDER");
    await user.type(tagInput, "enter-tag{Enter}");

    await waitFor(() => {
      expect(screen.getByText("#enter-tag")).toBeInTheDocument();
    });
  });

  it("should not add duplicate tags", async () => {
    const user = userEvent.setup();
    render(<PromptFormModal {...defaultProps} />);

    const tagInput = screen.getByPlaceholderText("PROMPTS$ADD_TAG_PLACEHOLDER");
    const addButton = screen.getByText("PROMPTS$ADD");

    // Add tag first time
    await user.type(tagInput, "unique-tag");
    await user.click(addButton);

    // Try to add same tag again
    await user.type(tagInput, "unique-tag");
    await user.click(addButton);

    const tags = screen.getAllByText("#unique-tag");
    expect(tags).toHaveLength(1); // Should only appear once
  });

  it("should insert variable into content", async () => {
    const user = userEvent.setup();
    render(<PromptFormModal {...defaultProps} />);

    // Add variable
    const addVariableButton = screen.getByText("PROMPTS$ADD_VARIABLE");
    await user.click(addVariableButton);

    const nameInput = screen.getByPlaceholderText("PROMPTS$VARIABLE_NAME");
    await user.type(nameInput, "myVar");

    // Click insert button
    const insertButton = screen.getByText("PROMPTS$INSERT");
    await user.click(insertButton);

    const contentInput = screen.getByLabelText(/PROMPTS\$CONTENT/);
    expect(contentInput).toHaveValue("{{myVar}}");
  });

  it("should toggle favorite checkbox", async () => {
    const user = userEvent.setup();
    render(<PromptFormModal {...defaultProps} />);

    const checkbox = screen.getByLabelText("PROMPTS$MARK_AS_FAVORITE");
    expect(checkbox).not.toBeChecked();

    await user.click(checkbox);

    expect(checkbox).toBeChecked();
  });

  it("should disable submit when title is empty", () => {
    render(<PromptFormModal {...defaultProps} />);

    const submitButton = screen.getByText("PROMPTS$CREATE");
    expect(submitButton).toBeDisabled();
  });

  it("should close modal when close button is clicked", async () => {
    const user = userEvent.setup();
    render(<PromptFormModal {...defaultProps} />);

    const closeButton = screen.getByLabelText("Close");
    await user.click(closeButton);

    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it("should close modal when cancel button is clicked", async () => {
    const user = userEvent.setup();
    render(<PromptFormModal {...defaultProps} />);

    const cancelButton = screen.getByText("PROMPTS$CANCEL");
    await user.click(cancelButton);

    expect(defaultProps.onClose).toHaveBeenCalled();
  });
});
