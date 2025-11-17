import { describe, it, expect, beforeEach, vi } from "vitest";
import { screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ChangesTab from "#/routes/changes-tab.backup";
import { renderWithProviders } from "../../test-utils";

const mockUseGetGitChanges = vi.fn();
const mockUseStreamingChunks = vi.fn();
const mockUseLatestStreamingContent = vi.fn();
const mockUseRuntimeIsReady = vi.fn();
const mockUseConversationId = vi.fn();

vi.mock("#/hooks/query/use-get-git-changes", () => ({
  useGetGitChanges: () => mockUseGetGitChanges(),
}));

vi.mock("#/hooks/use-ws-events", () => ({
  useStreamingChunks: () => mockUseStreamingChunks(),
  useLatestStreamingContent: () => mockUseLatestStreamingContent(),
}));

vi.mock("#/hooks/use-runtime-is-ready", () => ({
  useRuntimeIsReady: () => mockUseRuntimeIsReady(),
}));

vi.mock("#/hooks/use-conversation-id", () => ({
  useConversationId: () => mockUseConversationId(),
}));

const getFilesMock = vi.hoisted(() =>
  vi.fn(async () => ["src/app.ts", "README.md"]),
);
const getFileMock = vi.hoisted(() =>
  vi.fn(async (_conversationId: string, path: string) => `content:${path}`),
);

vi.mock("#/api/forge", () => ({
  __esModule: true,
  default: {
    getFiles: getFilesMock,
    getFile: getFileMock,
  },
  getFiles: getFilesMock,
  getFile: getFileMock,
}));

vi.mock("#/components/features/diff-viewer/file-diff-viewer", () => ({
  FileDiffViewer: ({ path }: { path: string }) => (
    <div data-testid="file-diff-viewer">{path}</div>
  ),
}));

vi.mock("#/components/features/diff-viewer/streaming-file-viewer", () => ({
  StreamingFileViewer: () => <div data-testid="streaming-file-viewer" />,
}));

vi.mock("#/components/features/diff-viewer/file-tree", () => ({
  __esModule: true,
  default: ({
    onSelect,
    filteredChanges,
  }: {
    onSelect: (path: string) => void;
    filteredChanges: Array<{ path?: string }>;
  }) => {
    const firstPath = Array.isArray(filteredChanges) && filteredChanges.length > 0
      ? filteredChanges[0]?.path ?? ""
      : "";
    return (
      <div data-testid="file-tree">
        <button type="button" onClick={() => onSelect(firstPath)}>
          select-first
        </button>
      </div>
    );
  },
}));

vi.mock("#/components/shared/lazy-monaco", () => ({
  LazyMonaco: () => <div data-testid="lazy-monaco" />,
}));

const toastErrorMock = vi.hoisted(() => vi.fn());
const toastSuccessMock = vi.hoisted(() => vi.fn());

vi.mock("#/utils/toast", () => ({
  default: {
    error: toastErrorMock,
    success: toastSuccessMock,
  },
}));

describe("changes-tab.backup", () => {
  beforeEach(() => {
    mockUseStreamingChunks.mockReturnValue([]);
    mockUseLatestStreamingContent.mockReturnValue("");
    mockUseRuntimeIsReady.mockReturnValue(true);
    mockUseConversationId.mockReturnValue({ conversationId: "123" });
    getFilesMock.mockClear();
    getFileMock.mockClear();
    toastErrorMock.mockClear();
    toastSuccessMock.mockClear();
  });

  it("shows waiting message when runtime is not ready", () => {
    mockUseRuntimeIsReady.mockReturnValue(false);
    mockUseGetGitChanges.mockReturnValue({
      data: [],
      isSuccess: false,
      isLoading: false,
      error: null,
    });

    renderWithProviders(<ChangesTab />);

    expect(screen.getByText("DIFF_VIEWER$WAITING_FOR_RUNTIME")).toBeInTheDocument();
  });

  it("renders changes view with counts and allows switching to all files", async () => {
    mockUseGetGitChanges.mockReturnValue({
      data: [
        { path: "src/app.ts", status: "modified" },
        { path: "README.md", status: "new" },
      ],
      isSuccess: true,
      isLoading: false,
      error: null,
    });

    renderWithProviders(<ChangesTab />);

    expect(
      screen.getByRole("heading", { name: "WORKSPACE$CHANGES_TAB_LABEL" }),
    ).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText("WORKSPACE$SEARCH_FILES");
    await userEvent.type(searchInput, "README");
    expect(
      await screen.findByText(/WORKSPACE\$FILTERED_FROM/),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "WORKSPACE$ALL_FILES_LABEL" }));

    await waitFor(() => expect(getFilesMock).toHaveBeenCalled());
    expect(await screen.findByRole("button", { name: /src/ })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "WORKSPACE$CHANGES_TAB_LABEL" }));
  });

  it("renders diff viewer when selecting a change", async () => {
    mockUseGetGitChanges.mockReturnValue({
      data: [{ path: "src/app.ts", status: "modified" }],
      isSuccess: true,
      isLoading: false,
      error: null,
    });

    renderWithProviders(<ChangesTab />);

    const tree = await screen.findByTestId("file-tree");
    const selectButton = within(tree).getByRole("button", { name: "select-first" });
    await userEvent.click(selectButton);

    expect(screen.getByTestId("file-diff-viewer")).toBeInTheDocument();
  });

  it("toggles streaming mode and shows streaming viewer", async () => {
    mockUseGetGitChanges.mockReturnValue({
      data: [{ path: "src/app.ts", status: "modified" }],
      isSuccess: true,
      isLoading: false,
      error: null,
    });
    mockUseStreamingChunks.mockReturnValue([{ args: { is_final: false } }]);

    renderWithProviders(<ChangesTab />);

    await userEvent.click(screen.getByRole("button", { name: "WORKSPACE$TOGGLE_STREAMING" }));

    expect(screen.getByTestId("streaming-file-viewer")).toBeInTheDocument();
  });

  it("shows loading status while git changes are fetching", () => {
    mockUseRuntimeIsReady.mockReturnValue(true);
    mockUseGetGitChanges.mockReturnValue({
      data: [],
      isSuccess: false,
      isLoading: true,
      error: null,
    });

    renderWithProviders(<ChangesTab />);

    expect(screen.getByText("DIFF_VIEWER$LOADING")).toBeInTheDocument();
  });

  it("shows git repository error guidance", () => {
    mockUseRuntimeIsReady.mockReturnValue(true);
    mockUseGetGitChanges.mockReturnValue({
      data: [],
      isSuccess: false,
      isLoading: false,
      error: new Error("fatal: Not a git repository"),
    });

    renderWithProviders(<ChangesTab />);

    expect(screen.getByText("DIFF_VIEWER$NOT_A_GIT_REPO")).toBeInTheDocument();
    expect(screen.getByText("DIFF_VIEWER$ASK_OH")).toBeInTheDocument();
  });

  it("shows waiting status for missing repository (404)", () => {
    mockUseRuntimeIsReady.mockReturnValue(true);
    mockUseGetGitChanges.mockReturnValue({
      data: [],
      isSuccess: false,
      isLoading: false,
      error: new Error("404 Not Found"),
    });

    renderWithProviders(<ChangesTab />);

    expect(screen.getByText("DIFF_VIEWER$WAITING_FOR_RUNTIME")).toBeInTheDocument();
  });

  it("shows raw error message for unexpected failures", () => {
    mockUseRuntimeIsReady.mockReturnValue(true);
    mockUseGetGitChanges.mockReturnValue({
      data: [],
      isSuccess: false,
      isLoading: false,
      error: new Error("boom failure"),
    });

    renderWithProviders(<ChangesTab />);

    expect(screen.getByText("boom failure")).toBeInTheDocument();
  });

  it("loads all files, expands folders, and supports copy and download actions", async () => {
    const getFilesReturn = ["src/app.ts", "src/utils/helpers.ts", "README.md"];
    getFilesMock.mockResolvedValue(getFilesReturn);

    let resolveFileContent: ((value: string) => void) | undefined;
    getFileMock.mockImplementationOnce(
      () =>
        new Promise<string>((resolve) => {
          resolveFileContent = resolve;
        }),
    );

    mockUseGetGitChanges.mockReturnValue({
      data: [{ path: "src/app.ts", status: "modified" }],
      isSuccess: true,
      isLoading: false,
      error: null,
    });

    renderWithProviders(<ChangesTab />);

    await userEvent.click(screen.getByRole("button", { name: "WORKSPACE$ALL_FILES_LABEL" }));

    await waitFor(() => expect(getFilesMock).toHaveBeenCalled());

    const srcFolderButton = await screen.findByRole("button", { name: /src/ });
    await userEvent.click(srcFolderButton);
    const sidebar = screen.getByRole("complementary");
    const appFileNode = await within(sidebar).findByText("app.ts");
    await userEvent.click(appFileNode.closest("button") ?? appFileNode);

    expect(getFileMock).toHaveBeenCalledWith("123", "src/app.ts");

    resolveFileContent?.("console.log('hello');");

    await screen.findByTestId("lazy-monaco");

    const clipboardMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: clipboardMock },
    });

    const copyButton = screen.getByRole("button", { name: "WORKSPACE$COPY" });
    await userEvent.click(copyButton);

    await waitFor(() => expect(clipboardMock).toHaveBeenCalledWith("console.log('hello');"));
    expect(toastSuccessMock).toHaveBeenCalledWith(
      "copy-success",
      "File content copied to clipboard",
    );

    const originalCreateObjectURL = URL.createObjectURL;
    const originalRevokeObjectURL = URL.revokeObjectURL;
    const createObjectUrlMock = vi.fn(() => "blob:mock");
    const revokeObjectUrlMock = vi.fn();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      writable: true,
      value: createObjectUrlMock,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      writable: true,
      value: revokeObjectUrlMock,
    });
    const appendChildSpy = vi.spyOn(document.body, "appendChild");
    const removeChildSpy = vi.spyOn(document.body, "removeChild");
    const anchorClickSpy = vi.fn();
    const originalCreateElement = document.createElement;
    const createElementSpy = vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      if (tag === "a") {
        const anchor = originalCreateElement.call(document, tag) as HTMLAnchorElement;
        anchor.click = anchorClickSpy;
        return anchor;
      }
      return originalCreateElement.call(document, tag);
    });

    const downloadButton = screen.getByRole("button", { name: "WORKSPACE$DOWNLOAD" });
    await userEvent.click(downloadButton);

    expect(anchorClickSpy).toHaveBeenCalled();
    expect(createObjectUrlMock).toHaveBeenCalled();
    expect(revokeObjectUrlMock).toHaveBeenCalledWith("blob:mock");
    expect(toastSuccessMock).toHaveBeenCalledWith("download-success", "Downloaded src/app.ts");

    createElementSpy.mockRestore();
    appendChildSpy.mockRestore();
    removeChildSpy.mockRestore();
    if (originalCreateObjectURL) {
      Object.defineProperty(URL, "createObjectURL", {
        configurable: true,
        writable: true,
        value: originalCreateObjectURL,
      });
    } else {
      delete (URL as any).createObjectURL;
    }
    if (originalRevokeObjectURL) {
      Object.defineProperty(URL, "revokeObjectURL", {
        configurable: true,
        writable: true,
        value: originalRevokeObjectURL,
      });
    } else {
      delete (URL as any).revokeObjectURL;
    }
    delete (navigator as any).clipboard;
  });

  it("supports keyboard navigation between changes", async () => {
    mockUseGetGitChanges.mockReturnValue({
      data: [
        { path: "src/first.ts", status: "modified" },
        { path: "src/second.ts", status: "modified" },
      ],
      isSuccess: true,
      isLoading: false,
      error: null,
    });

    renderWithProviders(<ChangesTab />);

    expect(screen.getByTestId("file-diff-viewer")).toHaveTextContent("src/first.ts");

    await userEvent.keyboard("{ArrowDown}");
    await waitFor(() =>
      expect(screen.getByTestId("file-diff-viewer")).toHaveTextContent("src/second.ts"),
    );

    await userEvent.keyboard("{ArrowUp}");
    await waitFor(() =>
      expect(screen.getByTestId("file-diff-viewer")).toHaveTextContent("src/first.ts"),
    );
  });

  it("handles failures when loading all files", async () => {
    getFilesMock.mockRejectedValueOnce(new Error("load-fail"));
    mockUseGetGitChanges.mockReturnValue({
      data: [{ path: "src/app.ts", status: "modified" }],
      isSuccess: true,
      isLoading: false,
      error: null,
    });

    renderWithProviders(<ChangesTab />);

    await userEvent.click(screen.getByRole("button", { name: "WORKSPACE$ALL_FILES_LABEL" }));

    await waitFor(() => expect(getFilesMock).toHaveBeenCalled());
    expect(toastErrorMock).toHaveBeenCalledWith(
      "load-files-error",
      "Failed to load workspace files",
    );
  });

  it("handles failures when loading file content", async () => {
    getFilesMock.mockResolvedValue(["src/app.ts"]);
    getFileMock.mockRejectedValueOnce(new Error("content-fail"));
    mockUseGetGitChanges.mockReturnValue({
      data: [{ path: "src/app.ts", status: "modified" }],
      isSuccess: true,
      isLoading: false,
      error: null,
    });

    renderWithProviders(<ChangesTab />);

    await userEvent.click(screen.getByRole("button", { name: "WORKSPACE$ALL_FILES_LABEL" }));
    await waitFor(() => expect(getFilesMock).toHaveBeenCalled());

    const errorSrcFolderButton = await screen.findByRole("button", { name: /src/ });
    await userEvent.click(errorSrcFolderButton);
    const errorSidebar = screen.getByRole("complementary");
    const errorAppFileNode = await within(errorSidebar).findByText("app.ts");
    await userEvent.click(errorAppFileNode.closest("button") ?? errorAppFileNode);

    await waitFor(() =>
      expect(toastErrorMock).toHaveBeenCalledWith(
        "load-content-error",
        "Failed to load file content",
      ),
    );
  });
});

