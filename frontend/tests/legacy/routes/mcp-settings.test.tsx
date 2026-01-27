import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "#test-utils";
import MCPSettingsScreen, {
  confirmServerDeletion,
  createTemplateInstaller,
} from "#/routes/mcp-settings";
import { MCPConfig } from "#/types/settings";
import type { MCPMarketplaceItem } from "#/types/mcp-marketplace";

const useSettingsMock = vi.hoisted(() => vi.fn());
const useAddMcpServerMock = vi.hoisted(() => vi.fn());
const useUpdateMcpServerMock = vi.hoisted(() => vi.fn());
const useDeleteMcpServerMock = vi.hoisted(() => vi.fn());
const displaySuccessToastMock = vi.hoisted(() => vi.fn());
const displayErrorToastMock = vi.hoisted(() => vi.fn());

vi.mock("#/hooks/query/use-settings", () => ({
  useSettings: useSettingsMock,
}));

vi.mock("#/hooks/mutation/use-add-mcp-server", () => ({
  useAddMcpServer: useAddMcpServerMock,
}));

vi.mock("#/hooks/mutation/use-update-mcp-server", () => ({
  useUpdateMcpServer: useUpdateMcpServerMock,
}));

vi.mock("#/hooks/mutation/use-delete-mcp-server", () => ({
  useDeleteMcpServer: useDeleteMcpServerMock,
}));

vi.mock("#/components/features/settings/mcp-settings/mcp-server-list", () => ({
  MCPServerList: ({
    servers,
    onEdit,
    onDelete,
  }: {
    servers: Array<{ id: string }>;
    onEdit: (server: any) => void;
    onDelete: (id: string) => void;
  }) => (
    <div data-testid="server-list">
      {servers.map((server) => (
        <div key={server.id} data-testid={`server-row-${server.id}`}>
          <button
            type="button"
            data-testid={`edit-${server.id}`}
            onClick={() => onEdit(server)}
          >
            edit
          </button>
          <button
            type="button"
            data-testid={`delete-${server.id}`}
            onClick={() => onDelete(server.id)}
          >
            delete
          </button>
        </div>
      ))}
    </div>
  ),
}));

vi.mock("#/components/features/settings/mcp-settings/mcp-server-form", () => ({
  MCPServerForm: ({
    mode,
    onSubmit,
    onCancel,
  }: {
    mode: "add" | "edit";
    onSubmit: (server: any) => void;
    onCancel: () => void;
  }) => (
    <div data-testid={`mcp-form-${mode}`}>
      <button
        type="button"
        data-testid="form-submit"
        onClick={() =>
          onSubmit({
            id: mode === "add" ? "new-server" : "existing-server",
            type: "sse",
          })
        }
      >
        submit
      </button>
      <button type="button" data-testid="form-cancel" onClick={onCancel}>
        cancel
      </button>
    </div>
  ),
}));

vi.mock("#/components/features/settings/mcp-settings/mcp-marketplace", () => ({
  MCPMarketplace: ({
    onInstall,
    installedServers,
  }: {
    onInstall: (item: any) => void;
    installedServers: string[];
  }) => (
    <div data-testid="marketplace">
      <span>{installedServers.join(",")}</span>
      <button
        type="button"
        data-testid="install-template"
        onClick={() =>
          onInstall({
            type: "sse",
            name: "Template",
            config: { command: "cmd", args: [], env: {}, url: "https://example" },
          })
        }
      >
        install
      </button>
    </div>
  ),
}));

vi.mock("#/components/shared/modals/confirmation-modal", () => ({
  ConfirmationModal: ({
    text,
    onConfirm,
    onCancel,
  }: {
    text: string;
    onConfirm: () => void;
    onCancel: () => void;
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

vi.mock("#/utils/custom-toast-handlers", () => ({
  displaySuccessToast: displaySuccessToastMock,
  displayErrorToast: displayErrorToastMock,
}));

vi.mock("react-i18next", async () => {
  const actual = await vi.importActual<typeof import("react-i18next")>(
    "react-i18next",
  );
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => key,
      i18n: {
        changeLanguage: () => Promise.resolve(),
      },
    }),
  };
});

const defaultConfig: MCPConfig = {
  sse_servers: [{ url: "https://sse.example", api_key: "key" }],
  stdio_servers: [
    { name: "stdio", command: "run", args: ["--help"], env: { FOO: "bar" } },
  ],
  shttp_servers: [],
};

describe("MCPSettingsScreen", () => {
  let addSpy: ReturnType<typeof vi.fn>;
  let updateSpy: ReturnType<typeof vi.fn>;
  let deleteSpy: ReturnType<typeof vi.fn>;

  const renderScreen = () => renderWithProviders(<MCPSettingsScreen />);

  beforeEach(() => {
    addSpy = vi.fn();
    updateSpy = vi.fn();
    deleteSpy = vi.fn();

    useSettingsMock.mockReturnValue({
      data: {
        MCP_CONFIG: defaultConfig,
      },
      isLoading: false,
    });
    useAddMcpServerMock.mockReturnValue({ mutate: addSpy });
    useUpdateMcpServerMock.mockReturnValue({ mutate: updateSpy });
    useDeleteMcpServerMock.mockReturnValue({ mutate: deleteSpy });

    displaySuccessToastMock.mockClear();
    displayErrorToastMock.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders skeleton when loading", () => {
    useSettingsMock.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    renderScreen();

    expect(document.querySelector(".animate-pulse")).not.toBeNull();
  });

  it("renders fallback when settings missing", async () => {
    const reloadSpy = vi.spyOn(window.location, "reload").mockImplementation(() => {});
    useSettingsMock.mockReturnValue({
      data: undefined,
      isLoading: false,
    });

    renderScreen();

    await userEvent.click(screen.getByTestId("reload-mcp-settings"));
    expect(reloadSpy).toHaveBeenCalled();
    reloadSpy.mockRestore();
  });

  it("adds a server from the form and shows success toast", async () => {
    addSpy.mockImplementation((_payload, options) => {
      options?.onSuccess?.();
    });

    renderScreen();

    await userEvent.click(screen.getByTestId("add-mcp-server-button"));
    await screen.findByTestId("mcp-form-add");
    await userEvent.click(await screen.findByTestId("form-submit"));

    expect(addSpy).toHaveBeenCalledWith(
      expect.objectContaining({ id: "new-server", type: "sse" }),
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(displaySuccessToastMock).toHaveBeenCalledWith("Server added successfully");
  });

  it("handles add server errors", async () => {
    addSpy.mockImplementation((_payload, options) => {
      options?.onError?.(new Error("nope"));
    });

    renderScreen();

    await userEvent.click(screen.getByTestId("add-mcp-server-button"));
    await userEvent.click(await screen.findByTestId("form-submit"));

    expect(displayErrorToastMock).toHaveBeenCalledWith("nope");
  });

  it("edits a server and handles update results", async () => {
    updateSpy.mockImplementation((_payload, options) => {
      options?.onSuccess?.();
    });

    renderScreen();

    await userEvent.click(screen.getByTestId("edit-sse-0"));
    await screen.findByTestId("mcp-form-edit");
    await userEvent.click(await screen.findByTestId("form-submit"));

    expect(updateSpy).toHaveBeenCalled();
    expect(displaySuccessToastMock).toHaveBeenCalledWith("Server updated successfully");

    displaySuccessToastMock.mockClear();
    updateSpy.mockImplementation((_payload, options) => {
      options?.onError?.(new Error("boom"));
    });

    await userEvent.click(screen.getByTestId("edit-sse-0"));
    await userEvent.click(await screen.findByTestId("form-submit"));
    expect(displayErrorToastMock).toHaveBeenCalledWith("boom");
  });

  it("allows cancelling edit flow", async () => {
    renderScreen();

    await userEvent.click(screen.getByTestId("edit-stdio-0"));
    await screen.findByTestId("mcp-form-edit");
    await userEvent.click(screen.getByTestId("form-cancel"));

    expect(screen.queryByTestId("mcp-form-edit")).not.toBeInTheDocument();
  });

  it("deletes a server through the confirmation modal", async () => {
    deleteSpy.mockImplementation((_payload, options) => {
      options?.onSuccess?.();
    });

    renderScreen();

    await userEvent.click(screen.getByTestId("delete-stdio-0"));
    const modal = await screen.findByTestId("confirmation-modal");
    await userEvent.click(within(modal).getByTestId("confirm-delete"));

    expect(deleteSpy).toHaveBeenCalledWith(
      "stdio-0",
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
    expect(displaySuccessToastMock).toHaveBeenCalledWith("Server deleted successfully");

    deleteSpy.mockImplementation((_payload, options) => {
      options?.onError?.("fail");
    });
    await userEvent.click(screen.getByTestId("delete-stdio-0"));
    const modalAgain = await screen.findByTestId("confirmation-modal");
    await userEvent.click(within(modalAgain).getByTestId("confirm-delete"));
    expect(displayErrorToastMock).toHaveBeenCalledWith("Failed to delete MCP server");
  });

  it("renders the marketplace view when active tab is marketplace", async () => {
    renderWithProviders(<MCPSettingsScreen initialTab="marketplace" />);

    expect(await screen.findByTestId("marketplace")).toBeInTheDocument();
    expect(screen.queryByTestId("server-list")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /My Servers/ }));
    expect(await screen.findByTestId("server-list")).toBeInTheDocument();
  });

  it("installs a marketplace template and handles errors", async () => {
    const setActiveTab = vi.fn();
    const installer = createTemplateInstaller({
      addMcpServer: addSpy,
      setActiveTab,
    });
    const template: MCPMarketplaceItem = {
      id: "test-id",
      slug: "template",
      name: "Template",
      description: "Test template",
      author: "Test",
      category: "utility" as any,
      type: "sse",
      config: { command: "cmd", args: [], env: {}, url: "https://example.com" },
    };

    addSpy.mockImplementation((_payload, options) => {
      options?.onSuccess?.();
    });

    installer(template);

    expect(addSpy).toHaveBeenCalled();
    expect(displaySuccessToastMock).toHaveBeenCalledWith("Template installed");
    expect(setActiveTab).toHaveBeenCalledWith("my-servers");

    addSpy.mockImplementation((_payload, options) => {
      options?.onError?.(new Error("install-fail"));
    });

    displayErrorToastMock.mockClear();
    installer(template);
    expect(displayErrorToastMock).toHaveBeenCalledWith("install-fail");
  });

  it("handles confirmServerDeletion guard clauses", () => {
    const setServerToDelete = vi.fn();
    const handleDeleteServer = vi.fn();

    confirmServerDeletion({
      serverToDelete: null,
      handleDeleteServer,
      setServerToDelete,
    });
    expect(displayErrorToastMock).toHaveBeenCalledWith("No server selected for deletion.");

    displayErrorToastMock.mockClear();

    confirmServerDeletion({
      serverToDelete: "x",
      // @ts-expect-error intentional to simulate missing handler
      handleDeleteServer: undefined,
      setServerToDelete,
    });
    expect(displayErrorToastMock).toHaveBeenCalledWith(
      "Unable to delete server right now.",
    );
  });
});

