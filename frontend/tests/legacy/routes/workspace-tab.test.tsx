import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import WorkspaceFilesTab from "#/routes/workspace-tab";

const useConversationIdMock = vi.hoisted(() => vi.fn());
const getFilesMock = vi.hoisted(() => vi.fn());
const getFileMock = vi.hoisted(() => vi.fn());
const uploadFilesMock = vi.hoisted(() => vi.fn());
const toastSuccessMock = vi.hoisted(() => vi.fn());
const toastErrorMock = vi.hoisted(() => vi.fn());

vi.mock("#/hooks/use-conversation-id", () => ({
  useConversationId: () => useConversationIdMock(),
}));

vi.mock("#/api/forge", () => ({
  default: {
    getFiles: (...args: unknown[]) => getFilesMock(...args),
    getFile: (...args: unknown[]) => getFileMock(...args),
    uploadFiles: (...args: unknown[]) => uploadFilesMock(...args),
  },
}));

vi.mock("#/components/shared/lazy-monaco", () => ({
  LazyMonaco: ({
    value,
    language,
    beforeMount,
    onChange,
  }: {
    value: string;
    language: string;
    beforeMount?: (monaco: any) => void;
    onChange?: (value: string) => void;
  }) => {
    beforeMount?.({
      editor: {
        defineTheme: vi.fn(),
        setTheme: vi.fn(),
      },
    });
    onChange?.(value);

    return (
      <div data-testid="monaco" data-language={language}>
        {value}
      </div>
    );
  },
}));

vi.mock("#/utils/toast", () => ({
  default: {
    success: (...args: unknown[]) => toastSuccessMock(...args),
    error: (...args: unknown[]) => toastErrorMock(...args),
  },
}));

const mockI18n = {
  changeLanguage: vi.fn(() => Promise.resolve()),
};

vi.mock("react-i18next", async () => {
  const actual = await vi.importActual<typeof import("react-i18next")>("react-i18next");
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => key,
      i18n: mockI18n,
    }),
  };
});

describe("WorkspaceFilesTab route", () => {
  let clipboardWriteMock: ReturnType<typeof vi.fn>;
  let originalClipboard: typeof navigator.clipboard;
  let createObjectURLMock: ReturnType<typeof vi.fn>;
  let revokeObjectURLMock: ReturnType<typeof vi.fn>;
  let originalCreateObjectURL: typeof URL.createObjectURL;
  let originalRevokeObjectURL: typeof URL.revokeObjectURL;
  const defaultFiles = ["src/index.ts", "src/utils/helpers.js", "assets/logo.png"];

  const renderWorkspace = () => render(<WorkspaceFilesTab />);

  beforeEach(() => {
    useConversationIdMock.mockReset();
    getFilesMock.mockReset();
    getFileMock.mockReset();
    uploadFilesMock.mockReset();
    toastSuccessMock.mockClear();
    toastErrorMock.mockClear();

    useConversationIdMock.mockReturnValue({ conversationId: "conversation-123" });
    getFilesMock.mockResolvedValue(defaultFiles);
    getFileMock.mockResolvedValue("console.log('hello');");
    uploadFilesMock.mockResolvedValue(undefined);

    originalClipboard = navigator.clipboard;
    clipboardWriteMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: clipboardWriteMock },
    });

    originalCreateObjectURL = URL.createObjectURL;
    originalRevokeObjectURL = URL.revokeObjectURL;
    createObjectURLMock = vi.fn(() => "blob:url");
    revokeObjectURLMock = vi.fn();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: createObjectURLMock,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectURLMock,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: originalClipboard,
    });
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: originalCreateObjectURL,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: originalRevokeObjectURL,
    });
  });

  it("loads files on mount and auto-selects first file", async () => {
    renderWorkspace();

    await waitFor(() => expect(getFilesMock).toHaveBeenCalledWith("conversation-123"));
    await waitFor(() => expect(getFileMock).toHaveBeenCalledWith("conversation-123", "src/index.ts"));

    const monaco = await screen.findByTestId("monaco");
    expect(monaco).toHaveTextContent("console.log('hello');");
    expect(monaco).toHaveAttribute("data-language", "typescript");

  });

  it("shows spinner while files are loading", async () => {
    let resolveFiles: (value: string[]) => void = () => {};
    const filesPromise = new Promise<string[]>((resolve) => {
      resolveFiles = resolve;
    });
    getFilesMock.mockReturnValue(filesPromise);

    renderWorkspace();

    expect(document.querySelector(".animate-spin")).toBeInTheDocument();

    resolveFiles(defaultFiles);
    await waitFor(() => expect(document.querySelector(".animate-spin")).not.toBeInTheDocument());
  });

  it("handles load files failure with toast", async () => {
    getFilesMock.mockRejectedValue(new Error("boom"));

    renderWorkspace();

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith("load-files-error", "Failed to load workspace files"));
  });

  it("handles file content directory error", async () => {
    getFileMock.mockRejectedValue(new Error("Is a directory"));

    renderWorkspace();

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith("is-directory", "This is a folder, not a file"));
  });

  it("handles generic file content error", async () => {
    getFileMock.mockRejectedValueOnce(new Error("network"));

    renderWorkspace();

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith("load-file-error", "Failed to load file content"));
  });

  it("renders icons for code, image, document, and default files", async () => {
    getFilesMock.mockResolvedValue([
      "script.ts",
      "guides/readme.md",
      "image.png",
      "archive.bin",
    ]);

    renderWorkspace();
    await waitFor(() => expect(getFilesMock).toHaveBeenCalled());

    const codeIcon = screen.getByRole("button", { name: "script.ts" }).querySelector("svg");
    expect(codeIcon).toHaveClass("text-violet-400");

    const guidesFolder = screen.getByRole("button", { name: "guides" });
    await userEvent.click(guidesFolder);
    const docIcon = screen.getByRole("button", { name: "readme.md" }).querySelector("svg");
    expect(docIcon).toHaveClass("text-blue-400");

    const imageIcon = screen.getByRole("button", { name: "image.png" }).querySelector("svg");
    expect(imageIcon).toHaveClass("text-green-400");

    const defaultIcon = screen.getByRole("button", { name: "archive.bin" }).querySelector("svg");
    expect(defaultIcon).toHaveClass("text-gray-400");
  });

  it("falls back to plaintext when extension is unknown", async () => {
    getFilesMock.mockResolvedValue(["custom/data.abc"]);
    getFileMock.mockResolvedValue("???");

    renderWorkspace();

    await screen.findByText("plaintext");
  });

  it("normalizes object responses when loading files", async () => {
    getFilesMock.mockResolvedValue([{ path: "object/example.txt" }] as any);

    renderWorkspace();

    await waitFor(() => expect(getFileMock).toHaveBeenCalledWith("conversation-123", "object/example.txt"));
    const objectFolder = screen.getByRole("button", { name: "object" });
    await userEvent.click(objectFolder);
    expect(screen.getByRole("button", { name: "example.txt" })).toBeInTheDocument();
  });

  it("filters files using search input", async () => {
    renderWorkspace();
    await waitFor(() => expect(getFilesMock).toHaveBeenCalled());

    const searchInput = screen.getByPlaceholderText("Search files...");
    await userEvent.type(searchInput, "helper");

    const srcAfterSearch = screen.getByRole("button", { name: "src" });
    await userEvent.click(srcAfterSearch);
    const utilsButton = screen.getByRole("button", { name: "utils" });
    await userEvent.click(utilsButton);

    await waitFor(() => expect(screen.getByRole("button", { name: "helpers.js" })).toBeInTheDocument());
    const sidebar = screen.getByRole("complementary");
    expect(within(sidebar).queryByRole("button", { name: "index.ts" })).toBeNull();
  });

  it("toggles folders open and closed", async () => {
    getFilesMock.mockResolvedValue(["folder/child/file.txt"]);
    getFileMock.mockResolvedValue("text");

    renderWorkspace();
    await waitFor(() => expect(getFilesMock).toHaveBeenCalled());

    const folderButton = screen.getByRole("button", { name: "folder" });
    expect(folderButton).toBeInTheDocument();

    await userEvent.click(folderButton);
    const childFolderButton = screen.getByRole("button", { name: "child" });
    await userEvent.click(childFolderButton);
    expect(screen.getByRole("button", { name: "file.txt" })).toBeInTheDocument();

    await userEvent.click(childFolderButton);
    expect(screen.queryByRole("button", { name: "file.txt" })).not.toBeInTheDocument();
  });

  it("copies file content to clipboard and handles failure", async () => {
    renderWorkspace();
    await waitFor(() => expect(getFileMock).toHaveBeenCalled());

    const copyButton = await screen.findByRole("button", { name: /Copy/ });
    await userEvent.click(copyButton);
    expect(clipboardWriteMock).toHaveBeenCalledWith("console.log('hello');");
    expect(toastSuccessMock).toHaveBeenCalledWith("copy-success", "Copied to clipboard");

    clipboardWriteMock.mockRejectedValueOnce(new Error("clipboard"));
    await userEvent.click(copyButton);
    expect(toastErrorMock).toHaveBeenCalledWith("copy-error", "Failed to copy");
  });

  it("downloads the current file", async () => {
    const appendChildSpy = vi.spyOn(document.body, "appendChild");
    const removeChildSpy = vi.spyOn(document.body, "removeChild");

    renderWorkspace();
    await waitFor(() => expect(getFileMock).toHaveBeenCalled());

    const downloadButton = await screen.findByRole("button", { name: /Download/ });
    await userEvent.click(downloadButton);

    expect(createObjectURLMock).toHaveBeenCalled();
    expect(revokeObjectURLMock).toHaveBeenCalled();
    expect(toastSuccessMock).toHaveBeenCalledWith("download-success", "Downloaded src/index.ts");
    expect(appendChildSpy).toHaveBeenCalled();
    expect(removeChildSpy).toHaveBeenCalled();

    appendChildSpy.mockRestore();
    removeChildSpy.mockRestore();
  });

  it("does not copy or download when file content is empty", async () => {
    getFileMock.mockResolvedValueOnce("");

    renderWorkspace();
    await waitFor(() => expect(getFileMock).toHaveBeenCalled());

    const copyButton = await screen.findByRole("button", { name: /Copy/ });
    await userEvent.click(copyButton);
    expect(clipboardWriteMock).not.toHaveBeenCalled();
    expect(toastSuccessMock).not.toHaveBeenCalledWith("copy-success", expect.any(String));

    const downloadButton = await screen.findByRole("button", { name: /Download/ });
    await userEvent.click(downloadButton);
    expect(createObjectURLMock).not.toHaveBeenCalled();
  });

  it("uploads files successfully", async () => {
    getFilesMock.mockResolvedValue([]);

    renderWorkspace();
    await waitFor(() => expect(getFilesMock).toHaveBeenCalledTimes(1));

    const importButton = await screen.findByRole("button", { name: "Import Workspace" });
    const fileInput = screen.getByLabelText("Upload files");
    const clickSpy = vi.spyOn(fileInput, "click");

    await userEvent.click(importButton);
    expect(clickSpy).toHaveBeenCalled();

    const file = new File(["content"], "new.txt", { type: "text/plain" });
    await userEvent.upload(fileInput, file);

    await waitFor(() => expect(uploadFilesMock).toHaveBeenCalled());
    await waitFor(() => expect(toastSuccessMock).toHaveBeenCalledWith("upload-success", "Uploaded 1 file(s)"));
    expect(getFilesMock).toHaveBeenCalledTimes(2);
  });

  it("handles upload failure", async () => {
    getFilesMock.mockResolvedValue([]);
    uploadFilesMock.mockRejectedValue(new Error("upload"));

    renderWorkspace();
    await waitFor(() => expect(getFilesMock).toHaveBeenCalled());

    const fileInput = screen.getByLabelText("Upload files");
    const file = new File(["content"], "fail.txt", { type: "text/plain" });
    await userEvent.upload(fileInput, file);

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith("upload-error", "Failed to upload files"));
  });

  it("skips upload when no files are selected", async () => {
    getFilesMock.mockResolvedValue([]);

    renderWorkspace();
    await waitFor(() => expect(getFilesMock).toHaveBeenCalled());

    const fileInput = screen.getByLabelText("Upload files");
    fireEvent.change(fileInput, { target: { files: null } });

    expect(uploadFilesMock).not.toHaveBeenCalled();
  });

  it("shows spinner while file content loads", async () => {
    let resolveFile: ((value: string) => void) | undefined;
    getFileMock.mockImplementation(() =>
      new Promise<string>((resolve) => {
        resolveFile = resolve;
      }),
    );

    renderWorkspace();

    await waitFor(() => {
      expect(document.querySelector("section .animate-spin")).toBeInTheDocument();
    });

    resolveFile?.("loaded");
    await waitFor(() => {
      expect(document.querySelector("section .animate-spin")).toBeNull();
    });
  });

  it("handles directory errors from response data", async () => {
    getFileMock.mockRejectedValueOnce({ response: { data: "Is a directory" } });

    renderWorkspace();

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith("is-directory", "This is a folder, not a file"));
  });

  it("selects files via the tree using handleFileSelect", async () => {
    renderWorkspace();
    await waitFor(() => expect(getFilesMock).toHaveBeenCalled());

    const srcFolder = screen.getByRole("button", { name: "src" });
    await userEvent.click(srcFolder);
    const utilsFolder = screen.getByRole("button", { name: "utils" });
    await userEvent.click(utilsFolder);
    const helpersFile = screen.getByRole("button", { name: "helpers.js" });
    await userEvent.click(helpersFile);

    expect(getFileMock).toHaveBeenLastCalledWith("conversation-123", "src/utils/helpers.js");
  });

  it("does not request files when conversation id missing", () => {
    useConversationIdMock.mockReturnValue({ conversationId: undefined });

    render(<WorkspaceFilesTab />);

    expect(getFilesMock).not.toHaveBeenCalled();
  });
});
