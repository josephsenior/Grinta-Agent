import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test-utils";
import MemorySettingsScreen from "#/routes/memory-settings";

const useMemoriesMock = vi.hoisted(() => vi.fn());
const useCreateMemoryMock = vi.hoisted(() => vi.fn());
const useUpdateMemoryMock = vi.hoisted(() => vi.fn());
const useDeleteMemoryMock = vi.hoisted(() => vi.fn());
const useMemoryStatsMock = vi.hoisted(() => vi.fn());
const useExportMemoriesMock = vi.hoisted(() => vi.fn());
const useImportMemoriesMock = vi.hoisted(() => vi.fn());
const displaySuccessToastMock = vi.hoisted(() => vi.fn());
const displayErrorToastMock = vi.hoisted(() => vi.fn());

vi.mock("#/hooks/query/use-memory", () => ({
  useMemories: useMemoriesMock,
  useCreateMemory: useCreateMemoryMock,
  useUpdateMemory: useUpdateMemoryMock,
  useDeleteMemory: useDeleteMemoryMock,
  useMemoryStats: useMemoryStatsMock,
  useExportMemories: useExportMemoriesMock,
  useImportMemories: useImportMemoriesMock,
}));

vi.mock("#/components/features/memory/memory-card", () => ({
  MemoryCard: ({
    memory,
    onEdit,
    onDelete,
  }: {
    memory: any;
    onEdit: (memory: any) => void;
    onDelete: (id: string) => void;
  }) => (
    <div data-testid={`memory-card-${memory.id}`}>
      <span>{memory.title}</span>
      <button
        type="button"
        data-testid={`edit-${memory.id}`}
        onClick={() => onEdit(memory)}
      >
        edit
      </button>
      <button
        type="button"
        data-testid={`delete-${memory.id}`}
        onClick={() => onDelete(memory.id)}
      >
        delete
      </button>
      <button
        type="button"
        data-testid={`delete-invalid-${memory.id}`}
        onClick={() => onDelete(undefined as unknown as string)}
      >
        delete-invalid
      </button>
    </div>
  ),
}));

vi.mock("#/components/features/memory/memory-form-modal", () => ({
  MemoryFormModal: ({
    memory,
    onSave,
    onClose,
    isLoading,
  }: {
    memory?: any;
    onSave: (data: any) => void;
    onClose: () => void;
    isLoading: boolean;
  }) => (
    <div data-testid="memory-form-modal">
      <span>{memory ? `editing-${memory.id}` : "creating"}</span>
      {isLoading && <span data-testid="form-loading">loading</span>}
      <button
        type="button"
        data-testid="modal-save"
        onClick={() => onSave({ title: "modal-value" })}
      >
        save
      </button>
      <button type="button" data-testid="modal-close" onClick={onClose}>
        close
      </button>
    </div>
  ),
}));

vi.mock("#/components/shared/modals/confirmation-modal", () => ({
  ConfirmationModal: ({
    onConfirm,
    onCancel,
    text,
  }: {
    onConfirm: () => void;
    onCancel: () => void;
    text: string;
  }) => (
    <div data-testid="confirmation-modal">
      <p>{text}</p>
      <button type="button" data-testid="confirm-delete" onClick={onConfirm}>
        confirm
      </button>
      <button type="button" data-testid="cancel-delete" onClick={onCancel}>
        cancel
      </button>
    </div>
  ),
}));

vi.mock("#/hooks/use-debounce", () => ({
  useDebounce: (value: string) => value,
}));

vi.mock("#/utils/custom-toast-handlers", () => ({
  displaySuccessToast: displaySuccessToastMock,
  displayErrorToast: displayErrorToastMock,
}));

const originalCreateElement = document.createElement;
const originalCreateObjectURL = URL.createObjectURL;
const originalRevokeObjectURL = URL.revokeObjectURL;

interface FileInputController {
  setFile: (file: { text: () => Promise<string> } | null) => void;
}

const setupFileInputMock = (): FileInputController => {
  let currentFile: { text: () => Promise<string> } | null = null;

  document.createElement = vi.fn().mockImplementation((tag: string) => {
    if (tag === "input") {
      const input = originalCreateElement.call(
        document,
        tag,
      ) as HTMLInputElement & { onclick?: () => void };

      Object.defineProperty(input, "files", {
        configurable: true,
        get: () => (currentFile ? [currentFile] : []),
      });

      input.click = () => {
        const event = new Event("change");
        Object.defineProperty(event, "target", {
          configurable: true,
          value: input,
        });
        input.onchange?.(event as unknown as Event);
      };

      return input;
    }
    return originalCreateElement.call(document, tag);
  });

  return {
    setFile: (file) => {
      currentFile = file;
    },
  };
};

const baseMemories = [
  {
    id: "mem-1",
    title: "Project Overview",
    content: "Project details",
    category: "project",
    tags: ["project"],
    usageCount: 5,
  },
  {
    id: "mem-2",
    title: "Preferred stack",
    content: "React and TypeScript",
    category: "technical",
    tags: ["tech"],
    usageCount: 10,
  },
  {
    id: "mem-3",
    title: "Color theme",
    content: "Dark mode",
    category: "preference",
    tags: ["ui"],
    usageCount: 1,
  },
];

describe("MemorySettingsScreen", () => {
  let createMemorySpy: ReturnType<typeof vi.fn>;
  let updateMemorySpy: ReturnType<typeof vi.fn>;
  let deleteMemorySpy: ReturnType<typeof vi.fn>;
  let exportMemoriesSpy: ReturnType<typeof vi.fn>;
  let importMemoriesSpy: ReturnType<typeof vi.fn>;

  const renderScreen = () => renderWithProviders(<MemorySettingsScreen />);

  beforeEach(() => {
    createMemorySpy = vi.fn((input, options) => {
      options?.onSuccess?.();
    });
    updateMemorySpy = vi.fn((input, options) => {
      options?.onSuccess?.();
    });
    deleteMemorySpy = vi.fn((id, options) => {
      options?.onSuccess?.();
    });
    exportMemoriesSpy = vi.fn();
    importMemoriesSpy = vi.fn();

    useMemoriesMock.mockReturnValue({
      data: baseMemories,
      isLoading: false,
    });
    useMemoryStatsMock.mockReturnValue({
      data: {
        total: baseMemories.length,
        byCategory: {
          project: 1,
          technical: 1,
          preference: 1,
        },
        usedToday: 2,
      },
    });
    useCreateMemoryMock.mockReturnValue({
      mutate: createMemorySpy,
      isPending: false,
    });
    useUpdateMemoryMock.mockReturnValue({
      mutate: updateMemorySpy,
      isPending: false,
    });
    useDeleteMemoryMock.mockReturnValue({
      mutate: deleteMemorySpy,
    });
    useExportMemoriesMock.mockReturnValue({
      mutateAsync: exportMemoriesSpy,
    });
    useImportMemoriesMock.mockReturnValue({
      mutate: importMemoriesSpy,
    });

    displaySuccessToastMock.mockClear();
    displayErrorToastMock.mockClear();
  });

  afterEach(() => {
    document.createElement = originalCreateElement;
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
    vi.restoreAllMocks();
  });

  it("shows a loader while memories are loading", () => {
    useMemoriesMock.mockReturnValueOnce({ data: undefined, isLoading: true });

    renderScreen();

    expect(document.querySelector(".animate-spin")).not.toBeNull();
  });

  it("renders memories, filters results, and shows empty state with filters applied", async () => {
    const user = userEvent.setup();
    renderScreen();

    expect(screen.getByTestId("memory-card-mem-1")).toBeInTheDocument();
    expect(screen.getByText("Memory Management")).toBeInTheDocument();
    expect(screen.getByText("Total")).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText("Search memories...");
    await user.type(searchInput, "stack");

    expect(screen.getByTestId("memory-card-mem-2")).toBeInTheDocument();
    expect(screen.queryByTestId("memory-card-mem-1")).not.toBeInTheDocument();

    await user.clear(searchInput);
    const preferencesButton = screen.getByRole("button", { name: "Preferences" });
    await user.click(preferencesButton);

    expect(screen.getByTestId("memory-card-mem-3")).toBeInTheDocument();
    expect(screen.queryByTestId("memory-card-mem-2")).not.toBeInTheDocument();

    await user.type(searchInput, "unknown");
    const emptyState = await screen.findByText("No memories found");
    expect(
      within(emptyState.closest("div")!).getByText("Try adjusting your filters"),
    ).toBeInTheDocument();
  });

  it("opens the form modal and creates a new memory", async () => {
    const user = userEvent.setup();
    renderScreen();

    await user.click(screen.getByTestId("add-memory"));
    await screen.findByTestId("memory-form-modal");

    await user.click(screen.getByTestId("modal-save"));

    expect(createMemorySpy).toHaveBeenCalledWith(
      { title: "modal-value" },
      expect.objectContaining({
        onSuccess: expect.any(Function),
        onError: expect.any(Function),
      }),
    );
    expect(displaySuccessToastMock).toHaveBeenCalledWith("Memory created successfully");
  });

  it("shows an error toast when memory creation fails", async () => {
    const user = userEvent.setup();
    createMemorySpy.mockImplementation((_input, options) => {
      options?.onError?.(new Error("create-boom"));
    });

    renderScreen();

    await user.click(screen.getByTestId("add-memory"));
    await screen.findByTestId("memory-form-modal");
    await user.click(screen.getByTestId("modal-save"));

    expect(displayErrorToastMock).toHaveBeenCalledWith(
      "Failed to create memory: create-boom",
    );
  });

  it("edits an existing memory and handles update errors", async () => {
    const user = userEvent.setup();
    updateMemorySpy.mockImplementation((_input, options) => {
      options?.onError?.(new Error("fail"));
    });

    renderScreen();

    await user.click(screen.getByTestId("edit-mem-1"));
    await screen.findByTestId("memory-form-modal");
    await user.click(screen.getByTestId("modal-save"));

    expect(updateMemorySpy).toHaveBeenCalledWith(
      { memoryId: "mem-1", updates: { title: "modal-value" } },
      expect.objectContaining({
        onSuccess: expect.any(Function),
        onError: expect.any(Function),
      }),
    );
    expect(displayErrorToastMock).toHaveBeenCalledWith(
      "Failed to update memory: fail",
    );
  });

  it("updates an existing memory successfully and closes the modal", async () => {
    const user = userEvent.setup();
    renderScreen();

    await user.click(screen.getByTestId("edit-mem-2"));
    await screen.findByTestId("memory-form-modal");

    displaySuccessToastMock.mockClear();
    await user.click(screen.getByTestId("modal-save"));

    expect(updateMemorySpy).toHaveBeenCalledWith(
      { memoryId: "mem-2", updates: { title: "modal-value" } },
      expect.objectContaining({
        onSuccess: expect.any(Function),
        onError: expect.any(Function),
      }),
    );

    await waitFor(() =>
      expect(screen.queryByTestId("memory-form-modal")).not.toBeInTheDocument(),
    );
    expect(displaySuccessToastMock).toHaveBeenCalledWith(
      "Memory updated successfully",
    );
  });

  it("deletes a memory and shows success toast", async () => {
    const user = userEvent.setup();
    renderScreen();

    await user.click(screen.getByTestId("delete-mem-2"));
    await screen.findByTestId("confirmation-modal");
    await user.click(screen.getByTestId("confirm-delete"));

    expect(deleteMemorySpy).toHaveBeenCalledWith(
      "mem-2",
      expect.objectContaining({
        onSuccess: expect.any(Function),
        onError: expect.any(Function),
      }),
    );
    expect(displaySuccessToastMock).toHaveBeenCalledWith("Memory deleted successfully");
  });

  it("shows error toast when delete fails", async () => {
    const user = userEvent.setup();
    deleteMemorySpy.mockImplementation((_id, options) => {
      options?.onError?.(new Error("boom"));
    });

    renderScreen();

    await user.click(screen.getByTestId("delete-mem-1"));
    await screen.findByTestId("confirmation-modal");
    await user.click(screen.getByTestId("confirm-delete"));

    expect(displayErrorToastMock).toHaveBeenCalledWith(
      "Failed to delete memory: boom",
    );
  });

  it("ignores delete confirmation when no memory is selected", async () => {
    const user = userEvent.setup();
    renderScreen();

    await user.click(screen.getByTestId("delete-invalid-mem-1"));
    await screen.findByTestId("confirmation-modal");

    displaySuccessToastMock.mockClear();
    displayErrorToastMock.mockClear();
    deleteMemorySpy.mockClear();

    await user.click(screen.getByTestId("confirm-delete"));

    expect(deleteMemorySpy).not.toHaveBeenCalled();
    expect(displaySuccessToastMock).not.toHaveBeenCalled();
    expect(displayErrorToastMock).not.toHaveBeenCalled();

    await user.click(screen.getByTestId("cancel-delete"));
  });

  it("exports memories successfully and handles errors", async () => {
    const user = userEvent.setup();
    const revokeSpy = vi.fn();
    const anchorClickSpy = vi.fn();
    exportMemoriesSpy.mockResolvedValue([{ id: "mem-1" }]);

    URL.createObjectURL = vi.fn(() => "blob:mem-export");
    URL.revokeObjectURL = revokeSpy;
    document.createElement = vi.fn().mockImplementation((tag: string) => {
      if (tag === "a") {
        return {
          href: "",
          download: "",
          click: anchorClickSpy,
        };
      }
      return originalCreateElement.call(document, tag);
    });

    renderScreen();

    await user.click(screen.getByTestId("export-memories"));

    expect(exportMemoriesSpy).toHaveBeenCalled();
    expect(anchorClickSpy).toHaveBeenCalled();
    expect(displaySuccessToastMock).toHaveBeenCalledWith(
      "Memories exported successfully",
    );
    expect(revokeSpy).toHaveBeenCalledWith("blob:mem-export");

    exportMemoriesSpy.mockRejectedValueOnce(new Error("export-failed"));
    displaySuccessToastMock.mockClear();
    displayErrorToastMock.mockClear();

    await user.click(screen.getByTestId("export-memories"));

    await waitFor(() =>
      expect(displayErrorToastMock).toHaveBeenCalledWith("Failed to export memories"),
    );
  });

  it("imports memories from JSON and handles invalid files", async () => {
    const user = userEvent.setup();
    const fileController = setupFileInputMock();

    importMemoriesSpy.mockImplementation((_payload, options) => {
      options?.onSuccess?.({ imported: 1, total: 3 });
    });

    fileController.setFile({
      text: vi.fn().mockResolvedValue(JSON.stringify({ imported: 1, total: 3 })),
    });

    renderScreen();
    await user.click(screen.getByTestId("import-memories"));

    await waitFor(() =>
      expect(displaySuccessToastMock).toHaveBeenCalledWith(
        "Imported 1 memories (Total: 3)",
      ),
    );

    displaySuccessToastMock.mockClear();
    displayErrorToastMock.mockClear();

    fileController.setFile({
      text: vi.fn().mockRejectedValue(new Error("bad-json")),
    });

    await user.click(screen.getByTestId("import-memories"));

    await waitFor(() =>
      expect(displayErrorToastMock).toHaveBeenCalledWith("Invalid JSON file"),
    );
  });

  it("ignores import when no file is selected and surfaces api errors", async () => {
    const user = userEvent.setup();
    const fileController = setupFileInputMock();

    importMemoriesSpy.mockImplementation((_payload, options) => {
      options?.onError?.(new Error("import-failed"));
    });

    fileController.setFile(null);

    renderScreen();

    await user.click(screen.getByTestId("import-memories"));
    expect(displaySuccessToastMock).not.toHaveBeenCalled();
    expect(displayErrorToastMock).not.toHaveBeenCalled();

    fileController.setFile({
      text: vi.fn().mockResolvedValue(JSON.stringify({ imported: 0, total: 0 })),
    });

    await user.click(screen.getByTestId("import-memories"));

    await waitFor(() =>
      expect(displayErrorToastMock).toHaveBeenCalledWith("Failed to import memories"),
    );
  });

  it("shows empty state when no memories exist without filters", () => {
    useMemoriesMock.mockReturnValueOnce({
      data: [],
      isLoading: false,
    });

    renderScreen();

    expect(screen.getByText("No Memories Yet")).toBeInTheDocument();
    expect(screen.getByTestId("add-first-memory")).toBeInTheDocument();
  });

  it("falls back to unknown error messaging when non-error objects are thrown", async () => {
    const user = userEvent.setup();

    createMemorySpy.mockImplementation((_input, options) => {
      options?.onError?.("create-string" as unknown as Error);
    });
    updateMemorySpy.mockImplementation((_input, options) => {
      options?.onError?.(null as unknown as Error);
    });
    deleteMemorySpy.mockImplementation((_id, options) => {
      options?.onError?.(undefined as unknown as Error);
    });

    renderScreen();

    await user.click(screen.getByTestId("add-memory"));
    await screen.findByTestId("memory-form-modal");
    displayErrorToastMock.mockClear();
    await user.click(screen.getByTestId("modal-save"));
    expect(displayErrorToastMock).toHaveBeenCalledWith(
      "Failed to create memory: Unknown error",
    );
    await user.click(screen.getByTestId("modal-close"));

    await user.click(screen.getByTestId("edit-mem-1"));
    await screen.findByTestId("memory-form-modal");
    displayErrorToastMock.mockClear();
    await user.click(screen.getByTestId("modal-save"));
    expect(displayErrorToastMock).toHaveBeenCalledWith(
      "Failed to update memory: Unknown error",
    );
    await user.click(screen.getByTestId("modal-close"));

    await user.click(screen.getByTestId("delete-mem-2"));
    await screen.findByTestId("confirmation-modal");
    displayErrorToastMock.mockClear();
    await user.click(screen.getByTestId("confirm-delete"));
    expect(displayErrorToastMock).toHaveBeenCalledWith(
      "Failed to delete memory: Unknown error",
    );
  });

  it("renders stats summary fallbacks and sorts memories with missing usage counts", () => {
    useMemoriesMock.mockReturnValueOnce({
      data: [
        {
          id: "mem-4",
          title: "Undefined usage",
          content: "No usage count set",
          category: "technical",
          tags: [],
          usageCount: undefined,
        },
        {
          id: "mem-5",
          title: "Another undefined usage",
          content: "Also missing usage count",
          category: "project",
          tags: [],
          usageCount: undefined,
        },
      ],
      isLoading: false,
    });
    useMemoryStatsMock.mockReturnValueOnce({
      data: {
        total: 2,
        byCategory: undefined,
        usedToday: 0,
      },
    });

    renderScreen();

    const technicalCard = screen
      .getByText("Technical", { selector: "p" })
      .closest("div");
    expect(technicalCard).not.toBeNull();
    expect(within(technicalCard as HTMLElement).getByText("0")).toBeInTheDocument();

    const preferencesCard = screen
      .getByText("Preferences", { selector: "p" })
      .closest("div");
    expect(preferencesCard).not.toBeNull();
    expect(within(preferencesCard as HTMLElement).getByText("0")).toBeInTheDocument();

    const projectCard = screen
      .getByText("Project", { selector: "p" })
      .closest("div");
    expect(projectCard).not.toBeNull();
    expect(within(projectCard as HTMLElement).getByText("0")).toBeInTheDocument();

    expect(screen.getByTestId("memory-card-mem-4")).toBeInTheDocument();
    expect(screen.getByTestId("memory-card-mem-5")).toBeInTheDocument();
  });

  it("defaults memory count to zero when data is undefined", () => {
    useMemoriesMock.mockReturnValueOnce({
      data: undefined,
      isLoading: false,
    });

    renderScreen();

    expect(
      screen.getByRole("button", { name: "All (0)" }),
    ).toBeInTheDocument();
  });
});

