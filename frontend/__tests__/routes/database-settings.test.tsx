import React from "react";
import { describe, it, beforeEach, afterEach, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DatabaseSettingsScreen from "#/routes/database-settings";
import { renderWithProviders } from "../../test-utils";

const createMutation = vi.fn();
const deleteMutation = vi.fn();

vi.mock("#/hooks/query/use-database-connections", () => ({
  useCreateDatabaseConnection: () => ({ mutate: createMutation }),
  useDeleteDatabaseConnection: () => ({ mutate: deleteMutation }),
}));

vi.mock("#/components/features/settings/database-connections/database-connections-list", () => ({
  DatabaseConnectionsList: ({
    onEdit,
    onDelete,
  }: {
    onEdit: (connection: unknown) => void;
    onDelete: (id?: string) => void;
  }) => (
    <div data-testid="connections-list">
      <button type="button" onClick={() => onEdit({ id: "1", name: "Conn" })}>
        Edit Connection
      </button>
      <button type="button" onClick={() => onDelete("2")}>Delete Connection</button>
      <button type="button" onClick={() => onDelete(undefined)}>Delete Missing ID</button>
    </div>
  ),
}));

vi.mock("#/components/features/settings/database-connections/database-connection-form", () => ({
  DatabaseConnectionForm: ({ type, connection, onSubmit, onCancel }: any) => (
    <div data-testid="connection-form">
      <span data-testid="form-type">{type || connection?.name}</span>
      <button
         type="button"
         onClick={() => onSubmit({ type: type ?? connection?.type ?? "postgresql" })}
       >
         Save Form
       </button>
      <button type="button" onClick={onCancel}>
        Cancel Form
      </button>
    </div>
  ),
}));

vi.mock("#/components/shared/modals/confirmation-modal", () => ({
  ConfirmationModal: ({ isOpen, onConfirm, onCancel, children }: any) =>
    isOpen ? (
      <div data-testid="confirmation-modal">
        {children}
        <button type="button" onClick={onConfirm}>
          Confirm Delete
        </button>
        <button type="button" onClick={onCancel}>
          Cancel Delete
        </button>
      </div>
    ) : null,
}));

vi.mock("#/utils/custom-toast-handlers", () => ({
  displaySuccessToast: vi.fn(),
  displayErrorToast: vi.fn(),
}));

import { displaySuccessToast, displayErrorToast } from "#/utils/custom-toast-handlers";

describe("DatabaseSettingsScreen", () => {
  beforeEach(() => {
    createMutation.mockReset();
    deleteMutation.mockReset();
    vi.mocked(displaySuccessToast).mockReset();
    vi.mocked(displayErrorToast).mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders list view by default and opens the add dropdown", async () => {
    const user = userEvent.setup();

    createMutation.mockImplementation((_data, options) => {
      options?.onSuccess?.();
    });

    renderWithProviders(<DatabaseSettingsScreen />);

    expect(screen.getByTestId("connections-list")).toBeInTheDocument();

    const addButton = screen.getByTestId("add-database-connection");
    await user.click(addButton);

    const postgresOption = await screen.findByRole("button", { name: /PostgreSQL/i });
    await user.click(postgresOption);

    expect(screen.getByTestId("connection-form")).toBeInTheDocument();
    expect(screen.getByTestId("form-type")).toHaveTextContent("postgresql");

    await user.click(screen.getByText("Save Form"));

    expect(createMutation).toHaveBeenCalledWith({ type: "postgresql" }, expect.any(Object));
    expect(displaySuccessToast).toHaveBeenCalledWith("Database connection saved successfully");
    expect(screen.getByTestId("connections-list")).toBeInTheDocument();
  });

  it("shows an error toast when saving a connection fails", async () => {
    const user = userEvent.setup();

    createMutation.mockImplementation((_data, options) => {
      options?.onError?.(new Error("boom"));
      options?.onError?.("oops");
    });

    renderWithProviders(<DatabaseSettingsScreen />);

    await user.click(screen.getByTestId("add-database-connection"));
    await user.click(await screen.findByRole("button", { name: /MongoDB/i }));
    await user.click(screen.getByText("Save Form"));

    expect(displayErrorToast).toHaveBeenCalledWith("Failed to save connection: boom");
    expect(displayErrorToast).toHaveBeenCalledWith("Failed to save connection: Unknown error");
  });

  it("enters edit mode and cancels back to list", async () => {
    const user = userEvent.setup();

    createMutation.mockImplementation((_data, options) => {
      options?.onSuccess?.();
    });

    renderWithProviders(<DatabaseSettingsScreen />);

    await user.click(screen.getByText("Edit Connection"));

    expect(screen.getByTestId("connection-form")).toBeInTheDocument();
    await user.click(screen.getByText("Cancel Form"));
    expect(screen.getByTestId("connections-list")).toBeInTheDocument();
  });

  it("handles delete success and error flows", async () => {
    const user = userEvent.setup();

    deleteMutation.mockImplementation((_id, options) => {
      options?.onSuccess?.();
    });

    renderWithProviders(<DatabaseSettingsScreen />);

    await user.click(screen.getByText("Delete Connection"));
    expect(screen.getByTestId("confirmation-modal")).toBeInTheDocument();

    await user.click(screen.getByText("Confirm Delete"));
    expect(deleteMutation).toHaveBeenCalledWith("2", expect.any(Object));
    expect(displaySuccessToast).toHaveBeenCalledWith("Database connection deleted successfully");
    expect(screen.queryByTestId("confirmation-modal")).not.toBeInTheDocument();

    deleteMutation.mockImplementation((_id, options) => {
      options?.onError?.(new Error("missing"));
      options?.onError?.("oops");
    });

    await user.click(screen.getByText("Delete Connection"));
    await user.click(screen.getByText("Confirm Delete"));

    expect(displayErrorToast).toHaveBeenCalledWith("Failed to delete connection: missing");
    expect(displayErrorToast).toHaveBeenCalledWith("Failed to delete connection: Unknown error");

    await user.click(screen.getByText("Cancel Delete"));
    expect(screen.queryByTestId("confirmation-modal")).not.toBeInTheDocument();
  });

  it("does nothing when delete confirmation lacks an id", async () => {
    const user = userEvent.setup();

    renderWithProviders(<DatabaseSettingsScreen />);

    await user.click(screen.getByText("Delete Missing ID"));
    expect(screen.getByTestId("confirmation-modal")).toBeInTheDocument();

    await user.click(screen.getByText("Confirm Delete"));

    expect(deleteMutation).not.toHaveBeenCalled();
    expect(displaySuccessToast).not.toHaveBeenCalled();
    expect(displayErrorToast).not.toHaveBeenCalled();
    expect(screen.getByTestId("confirmation-modal")).toBeInTheDocument();

    await user.click(screen.getByText("Cancel Delete"));
    expect(screen.queryByTestId("confirmation-modal")).not.toBeInTheDocument();
  });

  it("closes the add dropdown when the backdrop is clicked", async () => {
    const user = userEvent.setup();

    renderWithProviders(<DatabaseSettingsScreen />);

    const addButton = screen.getByTestId("add-database-connection");
    await user.click(addButton);
    await screen.findByRole("button", { name: /PostgreSQL/i });

    const backdrop = document.querySelector(".fixed.inset-0") as HTMLElement | null;
    expect(backdrop).toBeTruthy();
    if (backdrop) {
      await user.click(backdrop);
    }

    expect(screen.queryByRole("button", { name: /PostgreSQL/i })).not.toBeInTheDocument();
  });

  it("opens the mysql form", async () => {
    const user = userEvent.setup();

    createMutation.mockImplementation((_data, options) => {
      options?.onSuccess?.();
    });

    renderWithProviders(<DatabaseSettingsScreen />);

    const addButton = screen.getByTestId("add-database-connection");
    await user.click(addButton);
    const mysqlOption = await screen.findByRole("button", { name: /MySQL/i });
    await user.click(mysqlOption);
    expect(screen.getByTestId("form-type")).toHaveTextContent("mysql");
  });

  it("opens the redis form", async () => {
    const user = userEvent.setup();

    createMutation.mockImplementation((_data, options) => {
      options?.onSuccess?.();
    });

    renderWithProviders(<DatabaseSettingsScreen />);

    const addButton = screen.getByTestId("add-database-connection");
    await user.click(addButton);
    const redisOption = await screen.findByRole("button", { name: /Redis/i });
    await user.click(redisOption);
    expect(screen.getByTestId("form-type")).toHaveTextContent("redis");
  });
});
