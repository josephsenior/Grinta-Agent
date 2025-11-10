import { useState } from "react";
import { Database, Plus } from "lucide-react";
import { BrandButton } from "#/components/features/settings/brand-button";
import { DatabaseConnectionForm } from "#/components/features/settings/database-connections/database-connection-form";
import { DatabaseConnectionsList } from "#/components/features/settings/database-connections/database-connections-list";
import { ConfirmationModal } from "#/components/shared/modals/confirmation-modal";
import {
  useCreateDatabaseConnection,
  useDeleteDatabaseConnection,
} from "#/hooks/query/use-database-connections";
import type { DatabaseType, DatabaseConnection } from "#/types/database";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";

type View =
  | "list"
  | "add-postgresql"
  | "add-mongodb"
  | "add-mysql"
  | "add-redis"
  | "edit";

function DatabaseSettingsScreen() {
  const controller = useDatabaseSettingsController();

  return (
    <div className="px-11 py-9 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Database className="w-8 h-8 text-brand-500" />
          <div>
            <h2 className="text-2xl font-bold text-foreground">
              Database Connections
            </h2>
            <p className="text-sm text-foreground-secondary mt-1">
              Configure connections to PostgreSQL, MongoDB, MySQL, and Redis
            </p>
          </div>
        </div>

        {controller.view === "list" && (
          <div className="flex items-center gap-2">
            <div className="relative">
              <BrandButton
                variant="primary"
                type="button"
                testId="add-database-connection"
                onClick={controller.toggleAddDropdown}
                className="flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Database
              </BrandButton>

              {/* Dropdown menu */}
              {controller.showAddDropdown && (
                <>
                  {/* Backdrop to close dropdown */}
                  <div
                    className="fixed inset-0 z-40"
                    onClick={controller.closeAddDropdown}
                  />
                  <div className="absolute right-0 top-full mt-2 w-48 bg-black border border-violet-500/20 rounded-lg shadow-lg overflow-hidden z-50">
                    <button
                      type="button"
                      onClick={() =>
                        controller.handleAddConnection("postgresql")
                      }
                      className="w-full px-4 py-2 text-left text-foreground hover:bg-black transition-colors flex items-center gap-2"
                    >
                      <Database className="w-4 h-4 text-brand-500" />
                      PostgreSQL
                    </button>
                    <button
                      type="button"
                      onClick={() => controller.handleAddConnection("mongodb")}
                      className="w-full px-4 py-2 text-left text-foreground hover:bg-black transition-colors flex items-center gap-2"
                    >
                      <Database className="w-4 h-4 text-brand-500" />
                      MongoDB
                    </button>
                    <button
                      type="button"
                      onClick={() => controller.handleAddConnection("mysql")}
                      className="w-full px-4 py-2 text-left text-foreground hover:bg-black transition-colors flex items-center gap-2"
                    >
                      <Database className="w-4 h-4 text-brand-500" />
                      MySQL
                    </button>
                    <button
                      type="button"
                      onClick={() => controller.handleAddConnection("redis")}
                      className="w-full px-4 py-2 text-left text-foreground hover:bg-black transition-colors flex items-center gap-2"
                    >
                      <Database className="w-4 h-4 text-brand-500" />
                      Redis
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      {controller.view === "list" && (
        <DatabaseConnectionsList
          onEdit={controller.handleEdit}
          onDelete={controller.handleDeleteClick}
        />
      )}

      {controller.view === "add-postgresql" && (
        <DatabaseConnectionForm
          type="postgresql"
          onSubmit={controller.handleSaveConnection}
          onCancel={controller.handleCancel}
        />
      )}

      {controller.view === "add-mongodb" && (
        <DatabaseConnectionForm
          type="mongodb"
          onSubmit={controller.handleSaveConnection}
          onCancel={controller.handleCancel}
        />
      )}

      {controller.view === "add-mysql" && (
        <DatabaseConnectionForm
          type="mysql"
          onSubmit={controller.handleSaveConnection}
          onCancel={controller.handleCancel}
        />
      )}

      {controller.view === "add-redis" && (
        <DatabaseConnectionForm
          type="redis"
          onSubmit={controller.handleSaveConnection}
          onCancel={controller.handleCancel}
        />
      )}

      {controller.view === "edit" && controller.editingConnection && (
        <DatabaseConnectionForm
          type={controller.editingConnection.type}
          existingConnection={controller.editingConnection}
          onSubmit={controller.handleSaveConnection}
          onCancel={controller.handleCancel}
        />
      )}

      {/* Delete Confirmation Modal */}
      {controller.deleteConfirmOpen && (
        <ConfirmationModal
          text="Are you sure you want to delete this database connection? This action cannot be undone."
          onConfirm={controller.handleConfirmDelete}
          onCancel={controller.closeDeleteDialog}
        />
      )}
    </div>
  );
}

export default DatabaseSettingsScreen;

function useDatabaseSettingsController() {
  const [view, setView] = useState<View>("list");
  const [editingConnection, setEditingConnection] =
    useState<DatabaseConnection | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [connectionToDelete, setConnectionToDelete] = useState<string | null>(
    null,
  );
  const [showAddDropdown, setShowAddDropdown] = useState(false);

  const { mutate: createConnection } = useCreateDatabaseConnection();
  const { mutate: deleteConnection } = useDeleteDatabaseConnection();

  const handleAddConnection = (type: DatabaseType) => {
    setView(`add-${type}` as View);
    setShowAddDropdown(false);
  };

  const handleEdit = (connection: DatabaseConnection) => {
    setEditingConnection(connection);
    setView("edit");
  };

  const handleDeleteClick = (connectionId: string) => {
    setConnectionToDelete(connectionId);
    setDeleteConfirmOpen(true);
  };

  const handleConfirmDelete = () => {
    if (!connectionToDelete) {
      return;
    }

    deleteConnection(connectionToDelete, {
      onSuccess: () => {
        displaySuccessToast("Database connection deleted successfully");
        setDeleteConfirmOpen(false);
        setConnectionToDelete(null);
      },
      onError: (error) => {
        displayErrorToast(
          `Failed to delete connection: ${error instanceof Error ? error.message : "Unknown error"}`,
        );
      },
    });
  };

  const handleSaveConnection = (connectionData: any) => {
    createConnection(connectionData, {
      onSuccess: () => {
        displaySuccessToast("Database connection saved successfully");
        setView("list");
        setEditingConnection(null);
      },
      onError: (error) => {
        displayErrorToast(
          `Failed to save connection: ${error instanceof Error ? error.message : "Unknown error"}`,
        );
      },
    });
  };

  const handleCancel = () => {
    setView("list");
    setEditingConnection(null);
  };

  const toggleAddDropdown = () => setShowAddDropdown((prev) => !prev);
  const closeAddDropdown = () => setShowAddDropdown(false);
  const closeDeleteDialog = () => setDeleteConfirmOpen(false);

  return {
    view,
    editingConnection,
    deleteConfirmOpen,
    showAddDropdown,
    handleAddConnection,
    handleEdit,
    handleDeleteClick,
    handleConfirmDelete,
    handleSaveConnection,
    handleCancel,
    toggleAddDropdown,
    closeAddDropdown,
    closeDeleteDialog,
    setShowAddDropdown,
  };
}
