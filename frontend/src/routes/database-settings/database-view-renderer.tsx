import React from "react";
import { DatabaseConnectionForm } from "#/components/features/settings/database-connections/database-connection-form";
import type { DatabaseType, DatabaseConnection } from "#/types/database";

type NewDatabaseConnection = Omit<
  DatabaseConnection,
  "id" | "createdAt" | "updatedAt"
>;

interface DatabaseViewRendererProps {
  view: string;
  editingConnection?: DatabaseConnection | null;
  onSave: (data: NewDatabaseConnection) => void;
  onCancel: () => void;
}

export function DatabaseViewRenderer({
  view,
  editingConnection,
  onSave,
  onCancel,
}: DatabaseViewRendererProps) {
  const getDatabaseType = (): DatabaseType | null => {
    if (view === "add-postgresql") return "postgresql";
    if (view === "add-mongodb") return "mongodb";
    if (view === "add-mysql") return "mysql";
    if (view === "add-redis") return "redis";
    if (view.startsWith("edit-")) {
      return view.replace("edit-", "") as DatabaseType;
    }
    return null;
  };

  const databaseType = getDatabaseType();

  if (!databaseType) {
    return null;
  }

  return (
    <DatabaseConnectionForm
      type={databaseType}
      onSubmit={onSave as (connection: any) => void}
      onCancel={onCancel}
      existingConnection={editingConnection}
    />
  );
}
