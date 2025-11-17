import React from "react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PromptsSettingsScreen from "#/routes/prompts-settings";
import { renderWithProviders } from "../../test-utils";

vi.mock("react-i18next", async () => {
  const actual = await vi.importActual<typeof import("react-i18next")>("react-i18next");
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string, options?: Record<string, unknown>) => key,
    }),
  };
});

const toastMock = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  toasts: [] as Array<{ id: string; message: string }>,
  removeToast: vi.fn(),
}));

const promptsFixture = vi.hoisted(() => [
  {
    id: "1",
    title: "Alpha Prompt",
    description: "Description alpha",
    content: "alpha content",
    tags: ["code"],
    category: "general",
    is_favorite: false,
  },
  {
    id: "2",
    title: "Beta Prompt",
    description: "Description beta",
    content: "beta content",
    tags: ["ai"],
    category: "coding",
    is_favorite: true,
  },
] satisfies Array<any>);

const statsFixture = vi.hoisted(() => ({
  total_prompts: 5,
  total_favorites: 2,
  prompts_by_category: { general: 3, coding: 2 },
  total_tags: 6,
}));

let currentPromptsData: Array<any> = promptsFixture;
let promptsLoading = false;
let lastPromptsArgs: any;

const usePromptsMock = vi.hoisted(() =>
  vi.fn((args?: any) => {
    lastPromptsArgs = args;
    if (promptsLoading) {
      return { data: undefined, isLoading: true };
    }
    return { data: currentPromptsData, isLoading: false };
  }),
);

const usePromptStatsMock = vi.hoisted(() => vi.fn(() => ({ data: statsFixture })));

const createMutateMock = vi.hoisted(() => vi.fn());
const updateMutateMock = vi.hoisted(() => vi.fn());
const deleteMutateMock = vi.hoisted(() => vi.fn());
const exportMutateAsyncMock = vi.hoisted(() => vi.fn());
const importMutateAsyncMock = vi.hoisted(() => vi.fn());

const getConfigMock = vi.hoisted(() => vi.fn());

vi.mock("#/api/forge", () => ({
  default: {
    getConfig: getConfigMock,
  },
}));

vi.mock("#/hooks/query/use-prompts", () => ({
  usePrompts: (...args: any[]) => usePromptsMock(...args),
  usePromptStats: () => usePromptStatsMock(),
  useCreatePrompt: () => ({ mutate: createMutateMock }),
  useUpdatePrompt: () => ({ mutate: updateMutateMock }),
  useDeletePrompt: () => ({ mutate: deleteMutateMock }),
  useExportPrompts: () => ({ mutateAsync: exportMutateAsyncMock, isPending: false }),
  useImportPrompts: () => ({ mutateAsync: importMutateAsyncMock, isPending: false }),
}));

vi.mock("#/components/shared/toast", () => ({
  useToast: () => toastMock,
  ToastContainer: ({ toasts }: { toasts: unknown[] }) => (
    <div data-testid="toast-container" data-count={toasts.length} />
  ),
  ToastProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("#/hooks/use-debounce", () => ({
  useDebounce: <T,>(value: T) => value,
}));

const CardSkeletonGridMock = vi.hoisted(() =>
  vi.fn(({ count }: { count: number }) => (
    <div data-testid="card-skeleton" data-count={count} />
  )),
);

vi.mock("#/components/shared/card-skeleton", () => ({
  CardSkeletonGrid: CardSkeletonGridMock,
}));

vi.mock("#/components/features/prompts/prompt-card", () => ({
  PromptCard: ({
    prompt,
    onEdit,
    onDelete,
    onUse,
    onToggleFavorite,
  }: any) => (
    <div data-testid={`prompt-card-${prompt.id}`}>
      <span>{prompt.title}</span>
      <button type="button" onClick={() => onEdit(prompt)}>
        edit-{prompt.id}
      </button>
      <button type="button" onClick={() => onDelete(prompt.id)}>
        delete-{prompt.id}
      </button>
      <button type="button" onClick={() => onUse(prompt)}>
        use-{prompt.id}
      </button>
      <button type="button" onClick={() => onToggleFavorite(prompt.id, !prompt.is_favorite)}>
        favorite-{prompt.id}
      </button>
    </div>
  ),
}));

vi.mock("#/components/features/prompts/prompt-form-modal", () => ({
  PromptFormModal: ({ isOpen, onClose, onSubmit, initialData }: any) => {
    if (!isOpen) {
      return null;
    }
    return (
      <div data-testid="prompt-form-modal">
        {initialData && <span data-testid="editing-prompt">{initialData.title}</span>}
        <button
          type="button"
          onClick={() =>
            onSubmit({
              title: "submitted",
              content: "submitted content",
              description: "",
              tags: [],
              category: "general",
            })
          }
        >
          submit-form
        </button>
        <button type="button" onClick={onClose}>
          close-modal
        </button>
      </div>
    );
  },
}));

const originalCreateElement = document.createElement;
const originalAppendChild = document.body.appendChild;
const originalRemoveChild = document.body.removeChild;
let confirmStub: ReturnType<typeof vi.fn>;

describe("PromptsSettingsScreen", () => {
  beforeEach(() => {
    promptsLoading = false;
    currentPromptsData = promptsFixture;
    lastPromptsArgs = undefined;

    usePromptsMock.mockImplementation((args?: any) => {
      lastPromptsArgs = args;
      if (promptsLoading) {
        return { data: undefined, isLoading: true };
      }
      return { data: currentPromptsData, isLoading: false };
    });

    usePromptStatsMock.mockReturnValue({ data: statsFixture });

    createMutateMock.mockReset();
    updateMutateMock.mockReset();
    deleteMutateMock.mockReset();
    exportMutateAsyncMock.mockReset();
    importMutateAsyncMock.mockReset();
    toastMock.success.mockReset();
    toastMock.error.mockReset();
    toastMock.toasts = [];
    CardSkeletonGridMock.mockReset();

    Object.defineProperty(URL, "createObjectURL", {
      value: vi.fn().mockReturnValue("blob://prompts"),
      configurable: true,
      writable: true,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      value: vi.fn(),
      configurable: true,
      writable: true,
    });

    vi.spyOn(document.body, "appendChild").mockImplementation((node: any) =>
      originalAppendChild.call(document.body, node),
    );
    vi.spyOn(document.body, "removeChild").mockImplementation((node: any) =>
      originalRemoveChild.call(document.body, node),
    );

    confirmStub = vi.fn(() => true);
    vi.stubGlobal("confirm", confirmStub);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.createElement = originalCreateElement;
    document.body.appendChild = originalAppendChild;
    document.body.removeChild = originalRemoveChild;
    delete (URL as any).createObjectURL;
    delete (URL as any).revokeObjectURL;
  });

  it("shows loading skeleton while prompts load", async () => {
    promptsLoading = true;
    renderWithProviders(<PromptsSettingsScreen />);

    expect(usePromptsMock).toHaveBeenCalled();
    await waitFor(() => expect(CardSkeletonGridMock).toHaveBeenCalled());
  });

  it("renders empty state and submits create prompt", async () => {
    currentPromptsData = [];
    createMutateMock.mockImplementation((_data, options) => {
      options?.onSuccess?.();
    });

    const user = userEvent.setup();
    const { getByText, getByTestId } = renderWithProviders(<PromptsSettingsScreen />);

    expect(getByText("PROMPTS$EMPTY_STATE")).toBeInTheDocument();

    await user.click(getByText("PROMPTS$CREATE_FIRST"));
    expect(getByTestId("prompt-form-modal")).toBeInTheDocument();

    await user.click(getByText("submit-form"));

    expect(createMutateMock).toHaveBeenCalledWith(
      expect.objectContaining({ title: "submitted" }),
      expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) }),
    );
    expect(toastMock.success).toHaveBeenCalledWith("Prompt created successfully!");

    createMutateMock.mockImplementation((_data, options) => {
      options?.onError?.();
    });

    await user.click(getByText("submit-form"));
    expect(toastMock.error).toHaveBeenCalledWith("Failed to create prompt");
  });

  it("filters prompts by search, category, and favorites", async () => {
    const user = userEvent.setup();
    const {
      getByTestId,
      getByPlaceholderText,
      queryByTestId,
      getByText,
      getByDisplayValue,
    } = renderWithProviders(<PromptsSettingsScreen />);

    expect(getByTestId("prompt-card-1")).toBeInTheDocument();
    expect(getByTestId("prompt-card-2")).toBeInTheDocument();

    await user.type(getByPlaceholderText("PROMPTS$SEARCH_PLACEHOLDER"), "Beta");
    expect(queryByTestId("prompt-card-1")).not.toBeInTheDocument();
    expect(getByTestId("prompt-card-2")).toBeInTheDocument();

    await user.clear(getByPlaceholderText("PROMPTS$SEARCH_PLACEHOLDER"));
    await user.type(getByPlaceholderText("PROMPTS$SEARCH_PLACEHOLDER"), "zzz");
    expect(getByText("PROMPTS$NO_RESULTS")).toBeInTheDocument();

    await user.clear(getByPlaceholderText("PROMPTS$SEARCH_PLACEHOLDER"));

    await user.selectOptions(getByDisplayValue("PROMPTS$ALL_CATEGORIES"), "coding");
    expect(lastPromptsArgs).toEqual(
      expect.objectContaining({ category: "coding", is_favorite: undefined }),
    );

    await user.click(getByText("PROMPTS$FAVORITES_ONLY"));
    expect(lastPromptsArgs).toEqual(
      expect.objectContaining({ is_favorite: true, category: "coding" }),
    );
  });

  it("handles edit, update, delete, favorite toggle, and use prompt", async () => {
    const user = userEvent.setup();

    updateMutateMock.mockImplementation((_payload, options) => {
      options?.onSuccess?.();
    });
    deleteMutateMock.mockImplementation((_id, options) => {
      options?.onSuccess?.();
    });

    const {
      findByText,
      getByTestId,
      getByText,
    } = renderWithProviders(<PromptsSettingsScreen />);

    await user.click(await findByText("edit-1"));
    expect(getByTestId("prompt-form-modal")).toBeInTheDocument();
    expect(getByTestId("editing-prompt")).toHaveTextContent("Alpha Prompt");

    await user.click(getByText("submit-form"));
    expect(updateMutateMock).toHaveBeenCalledWith(
      {
        promptId: "1",
        data: expect.objectContaining({ title: "submitted" }),
      },
      expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) }),
    );
    expect(toastMock.success).toHaveBeenCalledWith("Prompt updated successfully!");

    await user.click(getByText("favorite-2"));
    expect(updateMutateMock).toHaveBeenNthCalledWith(2, {
      promptId: "2",
      data: { is_favorite: false },
    });

    await user.click(getByText("delete-1"));
    expect(deleteMutateMock).toHaveBeenCalledWith(
      "1",
      expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) }),
    );
    expect(toastMock.success).toHaveBeenCalledWith("Prompt deleted");

    deleteMutateMock.mockImplementation((_id, options) => {
      options?.onError?.();
    });

    await user.click(getByText("delete-1"));
    expect(toastMock.error).toHaveBeenCalledWith("Failed to delete prompt");

    await user.click(getByText("close-modal"));
    await user.click(getByText("use-2"));
    await waitFor(() =>
      expect(toastMock.success).toHaveBeenCalledWith("PROMPTS$COPIED_TO_CLIPBOARD"),
    );
  });

  it("does not delete a prompt when confirmation is cancelled", async () => {
    const user = userEvent.setup();
    confirmStub.mockReturnValueOnce(false);

    const { getByText } = renderWithProviders(<PromptsSettingsScreen />);

    await user.click(getByText("delete-1"));

    expect(deleteMutateMock).not.toHaveBeenCalled();
    expect(toastMock.success).not.toHaveBeenCalledWith("Prompt deleted");
  });

  it("handles export success and failure", async () => {
    const user = userEvent.setup();

    let anchorClick: ReturnType<typeof vi.spyOn> | undefined;
    document.createElement = vi.fn().mockImplementation((tag: string) => {
      if (tag === "a") {
        const anchor = originalCreateElement.call(document, tag) as HTMLAnchorElement;
        anchorClick = vi.spyOn(anchor, "click");
        anchorClick.mockImplementation(() => {});
        return anchor;
      }
      return originalCreateElement.call(document, tag);
    });

    exportMutateAsyncMock.mockResolvedValue({ prompts: [{ id: "1" }] });

    const { getByText } = renderWithProviders(<PromptsSettingsScreen />);

    await user.click(getByText("PROMPTS$EXPORT"));

    await waitFor(() => expect(exportMutateAsyncMock).toHaveBeenCalledTimes(1));
    expect(anchorClick).toBeDefined();
    expect(anchorClick?.mock.calls.length).toBeGreaterThan(0);
    expect(toastMock.success).toHaveBeenCalledWith("Exported 1 prompts!");

    exportMutateAsyncMock.mockRejectedValueOnce(new Error("fail"));
    await user.click(getByText("PROMPTS$EXPORT"));
    await waitFor(() => expect(toastMock.error).toHaveBeenCalledWith("Failed to export prompts"));
  });

  it("handles import success and error", async () => {
    const user = userEvent.setup();

    const file = {
      text: vi.fn().mockResolvedValue(JSON.stringify({ example: true })),
    } as unknown as File;

    document.createElement = vi.fn().mockImplementation((tag: string) => {
      if (tag === "input") {
        const input = originalCreateElement.call(document, tag) as HTMLInputElement;
        Object.defineProperty(input, "files", {
          value: [file],
        });
        input.click = vi.fn(() => {
          input.onchange?.({ target: input } as unknown as Event);
        });
        return input;
      }
      return originalCreateElement.call(document, tag);
    });

    importMutateAsyncMock.mockResolvedValue({ imported: 2, updated: 1 });

    const { getByText } = renderWithProviders(<PromptsSettingsScreen />);

    await user.click(getByText("PROMPTS$IMPORT"));

    await waitFor(() =>
      expect(importMutateAsyncMock).toHaveBeenCalledWith({ example: true }),
    );
    expect(toastMock.success).toHaveBeenCalledWith(
      "PROMPTS$IMPORT_SUCCESS",
    );

    file.text = vi.fn().mockResolvedValue("{ invalid json }");
    importMutateAsyncMock.mockRejectedValueOnce(new Error("boom"));

    await user.click(getByText("PROMPTS$IMPORT"));

    await waitFor(() => expect(toastMock.error).toHaveBeenCalledWith("PROMPTS$IMPORT_ERROR"));
  });

  it("skips import workflow when no file is selected", async () => {
    const user = userEvent.setup();

    document.createElement = vi.fn().mockImplementation((tag: string) => {
      if (tag === "input") {
        const input = originalCreateElement.call(document, tag) as HTMLInputElement;
        Object.defineProperty(input, "files", {
          value: undefined,
        });
        input.click = vi.fn(() => {
          input.onchange?.({ target: input } as unknown as Event);
        });
        return input;
      }
      return originalCreateElement.call(document, tag);
    });

    const { getByText } = renderWithProviders(<PromptsSettingsScreen />);

    await user.click(getByText("PROMPTS$IMPORT"));

    expect(importMutateAsyncMock).not.toHaveBeenCalled();
    expect(toastMock.success).not.toHaveBeenCalledWith("PROMPTS$IMPORT_SUCCESS");
    expect(toastMock.error).not.toHaveBeenCalledWith("PROMPTS$IMPORT_ERROR");
  });
});
