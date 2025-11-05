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

type View = "list" | "add-postgresql" | "add-mongodb" | "add-mysql" | "add-redis" | "edit";

function DatabaseSettingsScreen() {
  const [view, setView] = useState<View>("list");
  const [editingConnection, setEditingConnection] =
    useState<DatabaseConnection | null>(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [connectionToDelete, setConnectionToDelete] = useState<string | null>(
    null,
  );
  const [showAddDropdown, setShowAddDropdown] = useState(false);

  const { mutate: createConnection, isPending: isCreating } =
    useCreateDatabaseConnection();
  const { mutate: deleteConnection, isPending: isDeleting } =
    useDeleteDatabaseConnection();

  const handleAddConnection = (type: DatabaseType) => {
    setView(`add-${type}` as View);
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
    if (connectionToDelete) {
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
    }
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

        {view === "list" && (
          <div className="flex items-center gap-2">
            <div className="relative">
              <BrandButton
                variant="primary"
                type="button"
                testId="add-database-connection"
                onClick={() => setShowAddDropdown(!showAddDropdown)}
                className="flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Database
              </BrandButton>
              
              {/* Dropdown menu */}
              {showAddDropdown && (
                <>
                  {/* Backdrop to close dropdown */}
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setShowAddDropdown(false)}
                  />
                  <div className="absolute right-0 top-full mt-2 w-48 bg-black border border-violet-500/20 rounded-lg shadow-lg overflow-hidden z-50">
                    <button
                      type="button"
                      onClick={() => {
                        handleAddConnection("postgresql");
                        setShowAddDropdown(false);
                      }}
                      className="w-full px-4 py-2 text-left text-foreground hover:bg-black transition-colors flex items-center gap-2"
                    >
                      <Database className="w-4 h-4 text-brand-500" />
                      PostgreSQL
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        handleAddConnection("mongodb");
                        setShowAddDropdown(false);
                      }}
                      className="w-full px-4 py-2 text-left text-foreground hover:bg-black transition-colors flex items-center gap-2"
                    >
                      <Database className="w-4 h-4 text-brand-500" />
                      MongoDB
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        handleAddConnection("mysql");
                        setShowAddDropdown(false);
                      }}
                      className="w-full px-4 py-2 text-left text-foreground hover:bg-black transition-colors flex items-center gap-2"
                    >
                      <Database className="w-4 h-4 text-brand-500" />
                      MySQL
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        handleAddConnection("redis");
                        setShowAddDropdown(false);
                      }}
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
      {view === "list" && (
        <DatabaseConnectionsList onEdit={handleEdit} onDelete={handleDeleteClick} />
      )}

      {view === "add-postgresql" && (
        <DatabaseConnectionForm
          type="postgresql"
          onSubmit={handleSaveConnection}
          onCancel={handleCancel}
        />
      )}

      {view === "add-mongodb" && (
        <DatabaseConnectionForm
          type="mongodb"
          onSubmit={handleSaveConnection}
          onCancel={handleCancel}
        />
      )}

      {view === "add-mysql" && (
        <DatabaseConnectionForm
          type="mysql"
          onSubmit={handleSaveConnection}
          onCancel={handleCancel}
        />
      )}

      {view === "add-redis" && (
        <DatabaseConnectionForm
          type="redis"
          onSubmit={handleSaveConnection}
          onCancel={handleCancel}
        />
      )}

      {view === "edit" && editingConnection && (
        <DatabaseConnectionForm
          type={editingConnection.type}
          onSubmit={handleSaveConnection}
          onCancel={handleCancel}
          existingConnection={editingConnection}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmOpen && (
        <ConfirmationModal
          text="Are you sure you want to delete this database connection? This action cannot be undone."
          onConfirm={handleConfirmDelete}
          onCancel={() => {
            setDeleteConfirmOpen(false);
            setConnectionToDelete(null);
          }}
        />
      )}
    </div>
  );
}

export default DatabaseSettingsScreen;

