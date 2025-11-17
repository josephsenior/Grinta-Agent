import { renderHook, act } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { getFileMock, toastInfoMock, toastErrorMock, toastSuccessMock } = vi.hoisted(() => {
  return {
    getFileMock: vi.fn(),
    toastInfoMock: vi.fn(),
    toastErrorMock: vi.fn(),
    toastSuccessMock: vi.fn(),
  };
});

vi.mock("#/api/forge", () => ({
  default: {
    getFile: getFileMock,
  },
}));

vi.mock("#/utils/toast", () => ({
  default: {
    info: toastInfoMock,
    error: toastErrorMock,
    success: toastSuccessMock,
  },
}));

import { useFileOperations } from "#/hooks/use-file-operations";

describe("useFileOperations", () => {
  const onFilesChanged = vi.fn();
  const originalConsoleWarn = console.warn;
  const originalConsoleError = console.error;
  const warnMock = vi.fn();
  const errorMock = vi.fn();
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;

  beforeEach(() => {
    vi.clearAllMocks();
    onFilesChanged.mockClear();
    console.warn = warnMock;
    console.error = errorMock;
  });

  afterEach(() => {
    console.warn = originalConsoleWarn;
    console.error = originalConsoleError;
  });

  beforeAll(() => {
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      writable: true,
      value: vi.fn(),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      writable: true,
      value: vi.fn(),
    });
  });

  afterAll(() => {
    if (originalCreateObjectURL) {
      Object.defineProperty(URL, "createObjectURL", {
        configurable: true,
        writable: true,
        value: originalCreateObjectURL,
      });
    } else {
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete (URL as unknown as Record<string, unknown>).createObjectURL;
    }

    if (originalRevokeObjectURL) {
      Object.defineProperty(URL, "revokeObjectURL", {
        configurable: true,
        writable: true,
        value: originalRevokeObjectURL,
      });
    } else {
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete (URL as unknown as Record<string, unknown>).revokeObjectURL;
    }
  });

  it("fetches string file content", async () => {
    getFileMock.mockResolvedValueOnce("file-content");
    const { result } = renderHook(() =>
      useFileOperations({ conversationId: "123", onFilesChanged }),
    );

    let content: string | null = null;
    await act(async () => {
      content = await result.current.getFileContent("src/index.ts");
    });

    expect(content).toBe("file-content");
    expect(getFileMock).toHaveBeenCalledWith("123", "src/index.ts");
    expect(result.current.loading).toBe(false);
  });

  it("extracts code or content from object response", async () => {
    getFileMock.mockResolvedValueOnce({ code: "CODE" });
    const { result } = renderHook(() => useFileOperations({ conversationId: "c1" }));

    let content: string | null = null;
    await act(async () => {
      content = await result.current.getFileContent("main.py");
    });

    expect(content).toBe("CODE");

    getFileMock.mockResolvedValueOnce({ content: "CONTENT" });
    await act(async () => {
      content = await result.current.getFileContent("main.py");
    });

    expect(content).toBe("CONTENT");
  });

  it("returns null when object lacks code and content", async () => {
    getFileMock.mockResolvedValueOnce({ other: "value" });
    const { result } = renderHook(() => useFileOperations({ conversationId: "c1" }));

    let content: string | null = "";
    await act(async () => {
      content = await result.current.getFileContent("main.py");
    });

    expect(content).toBeNull();
  });

  it("skips special downloads directory", async () => {
    const { result } = renderHook(() => useFileOperations({ conversationId: "abc" }));

    let content: string | null = "";
    await act(async () => {
      content = await result.current.getFileContent(".downloads/log.txt");
    });

    expect(content).toBeNull();
    expect(getFileMock).not.toHaveBeenCalled();
    expect(warnMock).toHaveBeenCalledWith(
      "Skipping special directory:",
      ".downloads/log.txt",
    );
  });

  it("handles errors for dot-prefixed files without toast", async () => {
    getFileMock.mockRejectedValueOnce(new Error("boom"));
    const { result } = renderHook(() => useFileOperations({ conversationId: "c" }));

    await act(async () => {
      const value = await result.current.getFileContent(".env");
      expect(value).toBeNull();
    });

    expect(toastErrorMock).not.toHaveBeenCalled();
  });

  it("handles errors for normal files with toast", async () => {
    getFileMock.mockRejectedValueOnce(new Error("fail"));
    const { result } = renderHook(() => useFileOperations({ conversationId: "c" }));

    await act(async () => {
      const value = await result.current.getFileContent("src/app.ts");
      expect(value).toBeNull();
    });

    expect(toastErrorMock).toHaveBeenCalledWith(
      "file-content-error",
      "Failed to load file content",
    );
  });

  it("deleteFile shows toast and triggers change callback", async () => {
    const { result } = renderHook(() =>
      useFileOperations({ conversationId: "123", onFilesChanged }),
    );

    await act(async () => {
      await result.current.deleteFile("README.md");
    });

    expect(toastInfoMock).toHaveBeenCalledWith("File README.md would be deleted");
    expect(onFilesChanged).toHaveBeenCalled();
  });

  it("deleteFile error surfaces toast", async () => {
    toastInfoMock.mockImplementationOnce(() => {
      throw new Error("toast failure");
    });
    const { result } = renderHook(() =>
      useFileOperations({ conversationId: "123", onFilesChanged }),
    );

    await act(async () => {
      await result.current.deleteFile("README.md");
    });

    expect(toastErrorMock).toHaveBeenCalledWith(
      "file-delete-error",
      "Failed to delete file",
    );
  });

  it("renameFile and createFolder notify and handle errors", async () => {
    const { result } = renderHook(() =>
      useFileOperations({ conversationId: "123", onFilesChanged }),
    );

    await act(async () => {
      await result.current.renameFile("old.txt", "new.txt");
      await result.current.createFolder("docs");
    });

    expect(toastInfoMock).toHaveBeenNthCalledWith(1, "File renamed from old.txt to new.txt");
    expect(toastInfoMock).toHaveBeenNthCalledWith(2, "Folder docs would be created");

    toastInfoMock.mockImplementationOnce(() => {
      throw new Error("rename fail");
    });

    await act(async () => {
      await result.current.renameFile("oops.txt", "fail.txt");
    });

    expect(toastErrorMock).toHaveBeenCalledWith(
      "file-rename-error",
      "Failed to rename file",
    );

    toastInfoMock.mockImplementationOnce(() => {
      throw new Error("folder fail");
    });

    await act(async () => {
      await result.current.createFolder("broken");
    });

    expect(toastErrorMock).toHaveBeenCalledWith(
      "folder-create-error",
      "Failed to create folder",
    );
  });

  it("downloads file content and revokes url", async () => {
    getFileMock.mockResolvedValueOnce("download content");
    getFileMock.mockResolvedValueOnce("second content");
    const createObjectURLSpy = vi
      .spyOn(URL, "createObjectURL")
      .mockReturnValue("blob:content");
    const revokeSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    const originalCreateElement = document.createElement.bind(document);
    const clickMock = vi.fn();
    const anchors: HTMLAnchorElement[] = [];

    const createElementSpy = vi
      .spyOn(document, "createElement")
      .mockImplementation((tagName: string) => {
        const element = originalCreateElement(tagName);
        if (tagName === "a") {
          element.click = clickMock;
          anchors.push(element as HTMLAnchorElement);
        }
        return element;
      });

    const appendSpy = vi.spyOn(document.body, "appendChild");
    const removeSpy = vi.spyOn(document.body, "removeChild");

    const { result } = renderHook(() => useFileOperations({ conversationId: "c" }));

    await act(async () => {
      await result.current.downloadFile("path/to/file.txt");
      await result.current.downloadFile("folder/");
    });

    expect(createObjectURLSpy).toHaveBeenCalled();
    expect(clickMock).toHaveBeenCalled();
    expect(appendSpy).toHaveBeenCalled();
    expect(removeSpy).toHaveBeenCalled();
    expect(revokeSpy).toHaveBeenCalledWith("blob:content");
    expect(toastSuccessMock).toHaveBeenCalledWith(
      "file-download-success",
      "Downloaded path/to/file.txt",
    );
    expect(anchors[0]?.download).toBe("file.txt");
    expect(anchors[1]?.download).toBe("file");

    createElementSpy.mockRestore();
    appendSpy.mockRestore();
    removeSpy.mockRestore();
  });

  it("handles download errors", async () => {
    getFileMock.mockResolvedValueOnce("download content");
    vi.spyOn(URL, "createObjectURL").mockImplementationOnce(() => {
      throw new Error("url fail");
    });

    const { result } = renderHook(() => useFileOperations({ conversationId: "c" }));

    await act(async () => {
      await result.current.downloadFile("path/to/file.txt");
    });

    expect(toastErrorMock).toHaveBeenCalledWith(
      "file-download-error",
      "Failed to download file",
    );
  });

  it("does nothing when download content is empty", async () => {
    getFileMock.mockResolvedValueOnce(null);
    const createObjectURLSpy = vi.spyOn(URL, "createObjectURL");

    const { result } = renderHook(() => useFileOperations({ conversationId: "c" }));

    await act(async () => {
      await result.current.downloadFile("empty.txt");
    });

    expect(createObjectURLSpy).not.toHaveBeenCalled();
    expect(toastSuccessMock).not.toHaveBeenCalled();
  });
});
