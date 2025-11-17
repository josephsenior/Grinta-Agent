import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
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

type DatabaseSettingsMessages = {
  saveSuccess: string;
  deleteSuccess: string;
  saveError: (message: string) => string;
  deleteError: (message: string) => string;
};

type View =
  | "list"
  | "add-postgresql"
  | "add-mongodb"
  | "add-mysql"
  | "add-redis"
  | "edit";

type NewDatabaseConnection = Omit<
  DatabaseConnection,
  "id" | "createdAt" | "updatedAt"
>;

function useDatabaseSettingsController(messages: DatabaseSettingsMessages) {
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
        displaySuccessToast(messages.deleteSuccess);
        setDeleteConfirmOpen(false);
        setConnectionToDelete(null);
      },
      onError: (error) => {
        const message =
          error instanceof Error ? error.message : "Unknown error";
        displayErrorToast(messages.deleteError(message));
      },
    });
  };

  const handleSaveConnection = (connectionData: NewDatabaseConnection) => {
    createConnection(connectionData, {
      onSuccess: () => {
        displaySuccessToast(messages.saveSuccess);
        setView("list");
        setEditingConnection(null);
      },
      onError: (error) => {
        const message =
          error instanceof Error ? error.message : "Unknown error";
        displayErrorToast(messages.saveError(message));
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

function DatabaseSettingsScreen() {
  const { t } = useTranslation("settings");

  const messages = useMemo<DatabaseSettingsMessages>(
    () => ({
      saveSuccess: t(
        "databaseSettings.toast.saveSuccess",
        "Database connection saved successfully",
      ),
      deleteSuccess: t(
        "databaseSettings.toast.deleteSuccess",
        "Database connection deleted successfully",
      ),
      saveError: (message: string) =>
        t("databaseSettings.toast.saveError", {
          message,
          defaultValue: "Failed to save connection: {{message}}",
        }),
      deleteError: (message: string) =>
        t("databaseSettings.toast.deleteError", {
          message,
          defaultValue: "Failed to delete connection: {{message}}",
        }),
    }),
    [t],
  );

  const databaseOptions = useMemo(
    () =>
      [
        {
          type: "postgresql" as DatabaseType,
          label: t("databaseSettings.types.postgresql", "PostgreSQL"),
        },
        {
          type: "mongodb" as DatabaseType,
          label: t("databaseSettings.types.mongodb", "MongoDB"),
        },
        {
          type: "mysql" as DatabaseType,
          label: t("databaseSettings.types.mysql", "MySQL"),
        },
        {
          type: "redis" as DatabaseType,
          label: t("databaseSettings.types.redis", "Redis"),
        },
      ] satisfies Array<{ type: DatabaseType; label: string }>,
    [t],
  );

  const controller = useDatabaseSettingsController(messages);

  return (
    <div className="p-6 sm:p-8 lg:p-10 flex flex-col gap-6 lg:gap-8">
      <div className="mx-auto max-w-6xl w-full space-y-6 lg:space-y-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Database className="w-8 h-8 text-foreground-tertiary" />
            <div>
              <h2 className="text-2xl font-bold text-foreground">
                {t("databaseSettings.title", "Database Connections")}
              </h2>
              <p className="text-sm text-foreground-secondary mt-1">
                {t(
                  "databaseSettings.subtitle",
                  "Configure connections to PostgreSQL, MongoDB, MySQL, and Redis",
                )}
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
                  {t("databaseSettings.actions.addConnection", "Add Database")}
                </BrandButton>

                {controller.showAddDropdown && (
                  <>
                    <div
                      className="fixed inset-0 z-40"
                      onClick={controller.closeAddDropdown}
                      aria-hidden="true"
                    />
                    <div className="absolute right-0 top-full mt-2 w-48 bg-black/90 border border-white/10 rounded-xl shadow-lg overflow-hidden z-50 backdrop-blur-xl">
                      {databaseOptions.map((option) => (
                        <button
                          key={option.type}
                          type="button"
                          onClick={() =>
                            controller.handleAddConnection(option.type)
                          }
                          className="w-full px-4 py-2 text-left text-foreground hover:bg-black transition-colors flex items-center gap-2"
                        >
                          <Database className="w-4 h-4 text-foreground-tertiary" />
                          {option.label}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>

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

        {controller.deleteConfirmOpen && (
          <ConfirmationModal
            text={t(
              "databaseSettings.confirmDelete",
              "Are you sure you want to delete this database connection? This action cannot be undone.",
            )}
            onConfirm={controller.handleConfirmDelete}
            onCancel={controller.closeDeleteDialog}
          />
        )}
      </div>
    </div>
  );
}

export default DatabaseSettingsScreen;
