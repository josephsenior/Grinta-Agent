import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import type { MockInstance } from "vitest";
import { screen, within, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SnippetsSettingsScreen from "#/routes/snippets-settings";
import type { CodeSnippet, SnippetStats } from "#/types/snippet";
import { SnippetLanguage, SnippetCategory } from "#/types/snippet";
import { renderWithProviders } from "../../test-utils";

const useSnippetsMock = vi.hoisted(() => vi.fn());
const useSnippetStatsMock = vi.hoisted(() => vi.fn());
const useCreateSnippetMock = vi.hoisted(() => vi.fn());
const useUpdateSnippetMock = vi.hoisted(() => vi.fn());
const useDeleteSnippetMock = vi.hoisted(() => vi.fn());
const useExportSnippetsMock = vi.hoisted(() => vi.fn());
const useImportSnippetsMock = vi.hoisted(() => vi.fn());
const useTrackSnippetUsageMock = vi.hoisted(() => vi.fn());
const useToastMock = vi.hoisted(() => vi.fn());

const toastSuccessSpy = vi.fn();
const toastErrorSpy = vi.fn();
const toastInfoSpy = vi.fn();
const toastWarningSpy = vi.fn();
const removeToastSpy = vi.fn();

const baseSnippets: CodeSnippet[] = [
  {
    id: "1",
    title: "React Component",
    description: "A sample React component snippet.",
    language: SnippetLanguage.TYPESCRIPT,
    category: SnippetCategory.UI_COMPONENT,
    code: "export const Component = () => <div>Hello</div>;",
    tags: ["react", "component"],
    is_favorite: false,
    usage_count: 5,
    created_at: "2023-01-01T00:00:00Z",
    updated_at: "2023-01-01T00:00:00Z",
    metadata: {},
    dependencies: [],
    related_snippets: [],
  },
  {
    id: "2",
    title: "Database Query",
    description: "Fetch users snippet.",
    language: SnippetLanguage.SQL,
    category: SnippetCategory.DATABASE,
    code: "SELECT * FROM users;",
    tags: ["db"],
    is_favorite: true,
    usage_count: 12,
    created_at: "2023-01-01T00:00:00Z",
    updated_at: "2023-01-01T00:00:00Z",
    metadata: {},
    dependencies: [],
    related_snippets: [],
  },
];

const stats: SnippetStats = {
  total_snippets: baseSnippets.length,
  snippets_by_language: {
    [SnippetLanguage.TYPESCRIPT]: 1,
    [SnippetLanguage.SQL]: 1,
  },
  snippets_by_category: {
    [SnippetCategory.UI_COMPONENT]: 1,
    [SnippetCategory.DATABASE]: 1,
  },
  total_favorites: 1,
  most_used_snippets: [
    [baseSnippets[1].title, baseSnippets[1].usage_count],
    [baseSnippets[0].title, baseSnippets[0].usage_count],
  ],
  total_tags: baseSnippets.reduce((sum, snippet) => sum + snippet.tags.length, 0),
};

vi.mock("#/hooks/query/use-snippets", () => ({
  useSnippets: useSnippetsMock,
  useSnippetStats: useSnippetStatsMock,
  useCreateSnippet: useCreateSnippetMock,
  useUpdateSnippet: useUpdateSnippetMock,
  useDeleteSnippet: useDeleteSnippetMock,
  useExportSnippets: useExportSnippetsMock,
  useImportSnippets: useImportSnippetsMock,
  useTrackSnippetUsage: useTrackSnippetUsageMock,
}));

vi.mock("#/components/shared/toast", () => ({
  useToast: useToastMock,
  ToastContainer: ({
    toasts,
    onRemove,
  }: {
    toasts: Array<{ id: string; type: string; message: string }>;
    onRemove: (id: string) => void;
  }) => (
    <div data-testid="toast-container">
      {toasts.map((toast) => (
        <div key={toast.id}>
          <span>{toast.message}</span>
          <button type="button" onClick={() => onRemove(toast.id)}>
            dismiss
          </button>
        </div>
      ))}
    </div>
  ),
}));

vi.mock("react-i18next", async () => {
  const actual = await vi.importActual<typeof import("react-i18next")>("react-i18next");
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => key,
    }),
  };
});

describe("SnippetsSettingsScreen", () => {
  let createMutation: ReturnType<typeof vi.fn>;
  let updateMutation: ReturnType<typeof vi.fn>;
  let deleteMutation: ReturnType<typeof vi.fn>;
  let exportMutation: ReturnType<typeof vi.fn>;
  let importMutation: ReturnType<typeof vi.fn>;
  let trackMutation: ReturnType<typeof vi.fn>;
let clipboardWriteTextSpy: MockInstance;
  let originalCreateObjectURL: typeof URL.createObjectURL;
  let originalRevokeObjectURL: typeof URL.revokeObjectURL;
let confirmSpy: MockInstance;
let consoleErrorSpy: MockInstance;

  const renderScreen = () => renderWithProviders(<SnippetsSettingsScreen />);

  beforeEach(() => {
    createMutation = vi.fn();
    updateMutation = vi.fn();
    deleteMutation = vi.fn();
    exportMutation = vi.fn();
    importMutation = vi.fn();
    trackMutation = vi.fn();

    useSnippetsMock.mockReturnValue({
      data: baseSnippets,
      isLoading: false,
    });
    useSnippetStatsMock.mockReturnValue({
      data: stats,
      isLoading: false,
    });
    useCreateSnippetMock.mockReturnValue({
      mutate: createMutation,
      isPending: false,
    });
    useUpdateSnippetMock.mockReturnValue({
      mutate: updateMutation,
      isPending: false,
    });
    useDeleteSnippetMock.mockReturnValue({
      mutate: deleteMutation,
    });
    useExportSnippetsMock.mockReturnValue({
      mutateAsync: exportMutation,
      isPending: false,
    });
    useImportSnippetsMock.mockReturnValue({
      mutateAsync: importMutation,
      isPending: false,
    });
    useTrackSnippetUsageMock.mockReturnValue({
      mutate: trackMutation,
    });

    useToastMock.mockReturnValue({
      toasts: [],
      removeToast: removeToastSpy,
      success: toastSuccessSpy,
      error: toastErrorSpy,
      info: toastInfoSpy,
      warning: toastWarningSpy,
    });

    clipboardWriteTextSpy = vi.spyOn(navigator.clipboard, "writeText");
    clipboardWriteTextSpy.mockResolvedValue(undefined);

    originalCreateObjectURL = URL.createObjectURL;
    originalRevokeObjectURL = URL.revokeObjectURL;
    URL.createObjectURL = vi.fn(() => "blob:snippets");
    URL.revokeObjectURL = vi.fn();

    confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.clearAllMocks();
    clipboardWriteTextSpy.mockRestore();
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
    confirmSpy.mockRestore();
    consoleErrorSpy.mockRestore();
  });

  it("renders loading skeleton", () => {
    useSnippetsMock.mockReturnValueOnce({ data: [], isLoading: true });
    const { container } = renderScreen();
    expect(container.querySelector(".animate-pulse")).not.toBeNull();
  });

  it("filters snippets by search and favorites", async () => {
    const user = userEvent.setup();
    renderScreen();

    const searchInput = screen.getByPlaceholderText("Search snippets...");
    await user.type(searchInput, "React");

    expect(
      screen.getByRole("heading", { name: "React Component" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Database Query" }),
    ).not.toBeInTheDocument();

    await user.clear(searchInput);
    const favoritesToggle = screen.getByRole("button", {
      name: /Favorites Only/,
    });
    await user.click(favoritesToggle);

    const calls = useSnippetsMock.mock.calls;
    const latestArgs = calls[calls.length - 1]?.[0] ?? {};
    expect(latestArgs.is_favorite).toBe(true);
  });

  it("opens the create snippet modal and submits", async () => {
    const user = userEvent.setup();
    createMutation.mockImplementation((_payload, options) => {
      options?.onSuccess?.();
    });

    renderScreen();

    await user.click(screen.getByRole("button", { name: "New Snippet" }));
    await user.type(screen.getByLabelText(/Title/), "New Snippet");
    await user.type(screen.getByLabelText(/Code/), "console.log('hi');");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(createMutation).toHaveBeenCalled();
    expect(toastSuccessSpy).toHaveBeenCalledWith("Snippet created successfully!");
  });

  it("edits and updates a snippet with tag management", async () => {
    const user = userEvent.setup();
    updateMutation.mockImplementation((_payload, options) => {
      options?.onSuccess?.();
    });

    renderScreen();

    const menuButton = getMenuButton("1");
    await user.click(menuButton);
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await screen.findByRole("heading", { name: "Edit Snippet" });

    const titleField = screen.getByLabelText(/Title/);
    await user.clear(titleField);
    await user.type(titleField, "React Component Updated");

    const descriptionField = screen.getByLabelText("Description");
    await user.clear(descriptionField);
    await user.type(descriptionField, "Updated description for snippet.");

    const languageSelect = screen.getByLabelText("Language");
    await user.selectOptions(languageSelect, SnippetLanguage.JAVASCRIPT);

    const categorySelect = screen.getByLabelText("Category");
    await user.selectOptions(categorySelect, SnippetCategory.UTILITY);

    const favoriteCheckbox = screen.getByLabelText("Mark as favorite");
    await user.click(favoriteCheckbox);

    await user.type(screen.getByPlaceholderText("Add a tag..."), "newtag");
    await user.keyboard("{Enter}");
    await user.click(screen.getByRole("button", { name: "Add" }));

    const tagChip = screen.getByText("#react").closest("span");
    if (tagChip) {
      const removeButton = tagChip.querySelector("button");
      if (removeButton) {
        await user.click(removeButton);
      }
    }

    fireEvent.submit(screen.getByTestId("snippet-form"));

    await waitFor(() => expect(updateMutation).toHaveBeenCalled());
    expect(toastSuccessSpy).toHaveBeenCalledWith("Snippet updated successfully!");
  });

  it("deletes a snippet and handles failure", async () => {
    const user = userEvent.setup();
    deleteMutation.mockImplementation((_payload, options) => {
      options?.onSuccess?.();
    });

    renderScreen();

    const deleteMenuButton = getMenuButton("2");
    await user.click(deleteMenuButton);
    await user.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() =>
      expect(deleteMutation).toHaveBeenCalledWith(
        "2",
        expect.objectContaining({ onSuccess: expect.any(Function) }),
      ),
    );
    expect(toastSuccessSpy).toHaveBeenCalledWith("Snippet deleted");

    deleteMutation.mockImplementation((_payload, options) => {
      options?.onError?.(new Error("fail"));
    });

    toastErrorSpy.mockClear();
    const reopenMenuButton = getMenuButton("2");
    await user.click(reopenMenuButton);
    await user.click(screen.getByRole("button", { name: "Delete" }));

    await waitFor(() => expect(toastErrorSpy).toHaveBeenCalledWith("Failed to delete snippet"));
  });

  it("copies snippet code and tracks usage", async () => {
    const user = userEvent.setup();
    renderScreen();

    const useButtons = screen.getAllByRole("button", { name: "Use Snippet" });
    await user.click(useButtons[0]);

    expect(trackMutation).toHaveBeenCalledWith("1");
    expect(toastSuccessSpy).toHaveBeenCalledWith("Code copied to clipboard!");
    expect(clipboardWriteTextSpy).toHaveBeenCalledWith(baseSnippets[0].code);
  });

  it("handles snippet action menu interactions including copy", async () => {
    const user = userEvent.setup();
    renderScreen();

    const menuButton = getMenuButton("1");
    await user.click(menuButton);

    const overlay = document.querySelector("div.fixed.inset-0.z-10");
    expect(overlay).not.toBeNull();
    if (overlay) {
      await user.click(overlay as HTMLElement);
    }

    await user.click(menuButton);
    await user.click(screen.getByRole("button", { name: "Copy Code" }));

    await waitFor(() => expect(clipboardWriteTextSpy).toHaveBeenCalledWith(baseSnippets[0].code));
    expect(screen.getByText("Copied!")).toBeInTheDocument();
  });

  it("updates filters for language and category selections", async () => {
    const user = userEvent.setup();
    renderScreen();

    const languageSelect = screen.getByDisplayValue("All Languages");
    await user.selectOptions(languageSelect, SnippetLanguage.PYTHON);

    const categorySelect = screen.getByDisplayValue("All Categories");
    await user.selectOptions(categorySelect, SnippetCategory.API);

    const calls = useSnippetsMock.mock.calls;
    const latestArgs = calls[calls.length - 1]?.[0] ?? {};
    expect(latestArgs.language).toBe(SnippetLanguage.PYTHON);
    expect(latestArgs.category).toBe(SnippetCategory.API);
  });

  it("shows error toast when snippet creation fails", async () => {
    const user = userEvent.setup();
    createMutation.mockImplementation((_payload, options) => {
      options?.onError?.(new Error("boom"));
    });

    renderScreen();

    await user.click(screen.getByRole("button", { name: "New Snippet" }));
    await user.type(screen.getByLabelText(/Title/), "Error Snippet");
    await user.type(screen.getByLabelText(/Code/), "console.log('fail');");
    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() =>
      expect(toastErrorSpy).toHaveBeenCalledWith("Failed to create snippet"),
    );
  });

  it("shows error toast when snippet update fails", async () => {
    const user = userEvent.setup();
    updateMutation.mockImplementation((_payload, options) => {
      options?.onError?.(new Error("update-fail"));
    });

    renderScreen();

    const menuButton = getMenuButton("1");
    await user.click(menuButton);
    await user.click(screen.getByRole("button", { name: "Edit" }));
    await screen.findByRole("heading", { name: "Edit Snippet" });

    fireEvent.submit(screen.getByTestId("snippet-form"));

    await waitFor(() =>
      expect(toastErrorSpy).toHaveBeenCalledWith("Failed to update snippet"),
    );
  });

  it("exports and imports snippets", async () => {
    const user = userEvent.setup();
    exportMutation.mockResolvedValue({ snippets: baseSnippets });
    importMutation.mockResolvedValue({ imported: 2, updated: 0 });

    renderScreen();

    await user.click(screen.getByRole("button", { name: "Export" }));
    expect(exportMutation).toHaveBeenCalled();
    expect(toastSuccessSpy).toHaveBeenCalledWith("Exported 2 snippets!");

    toastSuccessSpy.mockClear();
    const originalCreateElement = document.createElement;
    let changeHandler: ((event: Event) => void) | undefined;
    document.createElement = vi.fn().mockImplementation((tag: string) => {
      if (tag === "input") {
        const input = originalCreateElement.call(document, tag) as HTMLInputElement;
        const file = new File([JSON.stringify({ snippets: baseSnippets })], "snippets.json", {
          type: "application/json",
        });
        Object.defineProperty(file, "text", {
          configurable: true,
          value: async () => JSON.stringify({ snippets: baseSnippets }),
        });
        Object.defineProperty(input, "files", {
          configurable: true,
          get: () => [file],
        });
        input.click = () => {
          changeHandler?.({ target: { files: [file] } } as unknown as Event);
        };
        return new Proxy(input, {
          set(target, prop, value) {
            if (prop === "onchange") {
              changeHandler = value as (event: Event) => void;
              return true;
            }
            // @ts-expect-error dynamic assignment
            target[prop] = value;
            return true;
          },
        });
      }
      return originalCreateElement.call(document, tag);
    });

    await user.click(screen.getByRole("button", { name: "Import" }));

    await waitFor(() => expect(importMutation).toHaveBeenCalled());
    expect(toastSuccessSpy).toHaveBeenCalledWith("Imported 2 new and updated 0 snippets!");
    document.createElement = originalCreateElement;
  });

  it("shows error toast when snippet export fails", async () => {
    const user = userEvent.setup();
    exportMutation.mockRejectedValueOnce(new Error("export-fail"));

    renderScreen();

    await user.click(screen.getByRole("button", { name: "Export" }));

    await waitFor(() => expect(exportMutation).toHaveBeenCalled());
    await waitFor(() =>
      expect(toastErrorSpy).toHaveBeenCalledWith("Failed to export snippets"),
    );
  });

  it("skips import when no file is selected", async () => {
    const user = userEvent.setup();
    renderScreen();

    const originalCreateElement = document.createElement;
    let changeHandler: ((event: Event) => void) | undefined;
    let inputRef: HTMLInputElement | undefined;
    document.createElement = vi.fn().mockImplementation((tag: string) => {
      if (tag === "input") {
        const input = originalCreateElement.call(document, tag) as HTMLInputElement;
        inputRef = input;
        Object.defineProperty(input, "files", {
          configurable: true,
          get: () => undefined,
        });
        input.click = () => {
          changeHandler?.({ target: input } as unknown as Event);
        };
        return new Proxy(input, {
          set(target, prop, value) {
            if (prop === "onchange") {
              changeHandler = value as (event: Event) => void;
              return true;
            }
            // @ts-expect-error dynamic assignment
            target[prop] = value;
            return true;
          },
        });
      }
      return originalCreateElement.call(document, tag);
    });

    await user.click(screen.getByRole("button", { name: "Import" }));
    changeHandler?.({ target: inputRef } as unknown as Event);

    expect(importMutation).not.toHaveBeenCalled();
    expect(toastErrorSpy).not.toHaveBeenCalledWith(
      "Failed to import snippets. Please check the file format.",
    );

    document.createElement = originalCreateElement;
  });

  it("logs an error when snippet import parsing fails", async () => {
    const user = userEvent.setup();
    renderScreen();

    const originalCreateElement = document.createElement;
    let changeHandler: ((event: Event) => void) | undefined;
    document.createElement = vi.fn().mockImplementation((tag: string) => {
      if (tag === "input") {
        const input = originalCreateElement.call(document, tag) as HTMLInputElement;
        const file = new File(["bad"], "invalid.json", { type: "application/json" });
        Object.defineProperty(file, "text", {
          configurable: true,
          value: vi.fn().mockResolvedValue("{ invalid json }"),
        });
        Object.defineProperty(input, "files", {
          configurable: true,
          get: () => [file],
        });
        input.click = () => {
          changeHandler?.({ target: input } as unknown as Event);
        };
        return new Proxy(input, {
          set(target, prop, value) {
            if (prop === "onchange") {
              changeHandler = value as (event: Event) => void;
              return true;
            }
            // @ts-expect-error dynamic assignment
            target[prop] = value;
            return true;
          },
        });
      }
      return originalCreateElement.call(document, tag);
    });

    await user.click(screen.getByRole("button", { name: "Import" }));

    await waitFor(() =>
      expect(toastErrorSpy).toHaveBeenCalledWith(
        "Failed to import snippets. Please check the file format.",
      ),
    );
    expect(importMutation).not.toHaveBeenCalled();
    expect(consoleErrorSpy).toHaveBeenCalledWith("Import error:", expect.any(Error));

    document.createElement = originalCreateElement;
  });

  it("handles missing snippet data by rendering nothing", () => {
    useSnippetsMock.mockReturnValueOnce({
      data: undefined,
      isLoading: false,
    });

    renderScreen();

    expect(screen.queryAllByTestId(/snippet-card-/)).toHaveLength(0);
  });

  it("shows empty state when no snippets exist", () => {
    useSnippetsMock.mockReturnValueOnce({
      data: [],
      isLoading: false,
    });

    renderScreen();

    expect(
      screen.getByText("You don't have any snippets yet. Create your first snippet to get started!"),
    ).toBeInTheDocument();
  });

  it("responds to keyboard shortcuts for creating snippets and focusing search", async () => {
    renderScreen();

    const searchInput = screen.getByPlaceholderText("Search snippets...");

    fireEvent.keyDown(window, { key: "n", ctrlKey: true });
    await screen.findByRole("heading", { name: "Create Snippet" });

    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    await waitFor(() => expect(searchInput).toHaveFocus());
  });
});

function getMenuButton(id: string) {
  const card = screen.getByTestId(`snippet-card-${id}`);
  return within(card).getByLabelText("Snippet actions");
}

