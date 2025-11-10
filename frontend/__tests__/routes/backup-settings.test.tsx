import { describe, it, beforeEach, afterEach, expect, vi } from "vitest";
import { screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import BackupSettingsScreen from "#/routes/backup-settings";
import { renderWithProviders } from "../../test-utils";

const toastSuccessSpy = vi.fn();
const toastErrorSpy = vi.fn();
const removeToastSpy = vi.fn();

vi.mock("#/components/shared/toast", () => ({
  useToast: () => ({
    toasts: [],
    removeToast: removeToastSpy,
    success: toastSuccessSpy,
    error: toastErrorSpy,
  }),
  ToastContainer: ({ toasts }: { toasts: unknown[] }) => (
    <div data-testid="toast-container">toasts:{toasts.length}</div>
  ),
}));

describe("BackupSettingsScreen", () => {
  const originalFetch = global.fetch;
  const originalCreateElement = document.createElement.bind(document);
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;

  beforeEach(() => {
    toastSuccessSpy.mockReset();
    toastErrorSpy.mockReset();
    removeToastSpy.mockReset();
    global.fetch = originalFetch;
    document.createElement = originalCreateElement;
    if (originalCreateObjectURL) {
      URL.createObjectURL = originalCreateObjectURL;
    } else {
      // jsdom may not define createObjectURL; ensure it exists for tests
      Object.defineProperty(URL, "createObjectURL", {
        value: vi.fn(),
        configurable: true,
        writable: true,
      });
    }
    if (originalRevokeObjectURL) {
      URL.revokeObjectURL = originalRevokeObjectURL;
    } else {
      Object.defineProperty(URL, "revokeObjectURL", {
        value: vi.fn(),
        configurable: true,
        writable: true,
      });
    }
  });

  afterEach(() => {
    global.fetch = originalFetch;
    document.createElement = originalCreateElement;
    if (originalCreateObjectURL) {
      URL.createObjectURL = originalCreateObjectURL;
    } else {
      // remove temporary stub if we created one
      delete (URL as unknown as Record<string, unknown>).createObjectURL;
    }
    if (originalRevokeObjectURL) {
      URL.revokeObjectURL = originalRevokeObjectURL;
    } else {
      delete (URL as unknown as Record<string, unknown>).revokeObjectURL;
    }
  });

  it("renders the core sections", () => {
    renderWithProviders(<BackupSettingsScreen />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Backup & Restore" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Export Your Data" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Import Your Data" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "Backup Best Practices" }),
    ).toBeInTheDocument();
  });

  it("exports data successfully", async () => {
    const blob = new Blob(["{}"], { type: "application/json" });
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(blob),
    } as unknown as Response);
    const createObjectURLMock = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:export");
    const revokeObjectURLMock = vi.spyOn(URL, "revokeObjectURL").mockReturnValue();
    const appendChildSpy = vi.spyOn(document.body, "appendChild");
    const removeChildSpy = vi.spyOn(document.body, "removeChild");

    const anchorClickSpies: Array<any> = [];
    const createElementSpy = vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      if (tag === "a") {
        const anchor = originalCreateElement(tag) as HTMLAnchorElement;
        anchorClickSpies.push(vi.spyOn(anchor, "click"));
        return anchor;
      }
      return originalCreateElement(tag);
    });

    renderWithProviders(<BackupSettingsScreen />);

    await userEvent.click(screen.getByRole("button", { name: "Export All Data" }));

    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith("/api/global-export/"));
    expect(anchorClickSpies.length).toBeGreaterThan(0);
    expect(anchorClickSpies[0]).toHaveBeenCalled();
    expect(createObjectURLMock).toHaveBeenCalledWith(blob);
    expect(revokeObjectURLMock).toHaveBeenCalled();
    expect(toastSuccessSpy).toHaveBeenCalledWith("Successfully exported all data!");

    anchorClickSpies.forEach((spy) => spy.mockRestore());
    createElementSpy.mockRestore();
    appendChildSpy.mockRestore();
    removeChildSpy.mockRestore();
    createObjectURLMock.mockRestore();
    revokeObjectURLMock.mockRestore();
  });

  it("handles export failures", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      blob: () => Promise.resolve(new Blob()),
    } as unknown as Response);
    global.fetch = fetchMock;

    renderWithProviders(<BackupSettingsScreen />);

    await userEvent.click(screen.getByRole("button", { name: "Export All Data" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(toastErrorSpy).toHaveBeenCalledWith("Failed to export data. Please try again.");
  });

  it("imports data successfully", async () => {
    vi.useFakeTimers();
    const user = userEvent.setup({
      advanceTimers: async (ms) => {
        vi.advanceTimersByTime(ms);
      },
    });
    const fileContents = JSON.stringify({
      memories: { imported: 2, updated: 1 },
      prompts: { imported: 1, updated: 0 },
    });
    const file = new File([fileContents], "backup.json", {
      type: "application/json",
    });
    Object.defineProperty(file, "text", {
      configurable: true,
      value: () => Promise.resolve(fileContents),
    });
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          memories: { imported: 2, updated: 1 },
          prompts: { imported: 1, updated: 0 },
        }),
    } as unknown as Response);
    global.fetch = fetchMock;

    let changeHandler: ((event: Event) => void) | null = null;
    const createElementSpy = vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      if (tag === "input") {
        const inputStub: any = {
          type: "",
          accept: "",
          click: () => {
            changeHandler?.({ target: { files: [file] } } as unknown as Event);
          },
        };
        Object.defineProperty(inputStub, "onchange", {
          configurable: true,
          get: () => changeHandler,
          set: (handler) => {
            changeHandler = handler as (event: Event) => void;
          },
        });
        Object.defineProperty(inputStub, "files", {
          configurable: true,
          get: () => [file],
        });
        return inputStub as HTMLInputElement;
      }
      return originalCreateElement(tag);
    });

    const reloadMock = vi.fn();
    const locationGetSpy = vi.spyOn(window, "location", "get").mockReturnValue({
      ...window.location,
      reload: reloadMock,
    });

    renderWithProviders(<BackupSettingsScreen />);

    await user.click(screen.getByRole("button", { name: "Import Data" }));

    expect(changeHandler).toBeTruthy();
    await act(async () => {
      await changeHandler?.({ target: { files: [file] } } as unknown as Event);
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/global-export/", expect.any(Object)));
    expect(toastSuccessSpy).toHaveBeenCalledWith(
      "Successfully imported 3 new items and updated 1 existing items!",
    );

    vi.runAllTimers();
    expect(reloadMock).toHaveBeenCalled();
    vi.useRealTimers();

    createElementSpy.mockRestore();
    locationGetSpy.mockRestore();
  });

  it("handles import failures", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
    } as unknown as Response);
    global.fetch = fetchMock;

    let changeHandler: ((event: Event) => void) | null = null;
    const failureFileContents = JSON.stringify({});
    const file = new File([failureFileContents], "backup.json", {
      type: "application/json",
    });
    Object.defineProperty(file, "text", {
      configurable: true,
      value: () => Promise.resolve(failureFileContents),
    });
    const createElementSpy = vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      if (tag === "input") {
        const inputStub: any = {
          type: "",
          accept: "",
          click: () => {
            changeHandler?.({ target: { files: [file] } } as unknown as Event);
          },
        };
        Object.defineProperty(inputStub, "onchange", {
          configurable: true,
          get: () => changeHandler,
          set: (handler) => {
            changeHandler = handler as (event: Event) => void;
          },
        });
        Object.defineProperty(inputStub, "files", {
          configurable: true,
          get: () => [file],
        });
        return inputStub as HTMLInputElement;
      }
      return originalCreateElement(tag);
    });

    const user = userEvent.setup();

    renderWithProviders(<BackupSettingsScreen />);

    await user.click(screen.getByRole("button", { name: "Import Data" }));

    expect(changeHandler).toBeTruthy();
    await act(async () => {
      await changeHandler?.({ target: { files: [file] } } as unknown as Event);
    });

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(toastErrorSpy).toHaveBeenCalledWith(
      "Failed to import data. Please check the file format.",
    );

    createElementSpy.mockRestore();
  });
});

