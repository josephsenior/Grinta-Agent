import { useState } from "react";
import {
  ChevronRight,
  ChevronDown,
  Table,
  Database,
  Key,
  Loader2,
  FileJson,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useDatabaseSchema } from "#/hooks/query/use-database-connections";
import type { DatabaseConnection, SchemaInfo } from "#/types/database";

interface SchemaBrowserProps {
  connection: DatabaseConnection;
  onTableSelect?: (tableName: string) => void;
}

export function SchemaBrowser({
  connection,
  onTableSelect,
}: SchemaBrowserProps) {
  const { t } = useTranslation();
  const { data: schema, isLoading, error } = useDatabaseSchema(connection.id);
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());

  // Type assertion to use SchemaInfo type which has proper object types
  const schemaInfo = schema as SchemaInfo | undefined;

  const toggleTable = (tableName: string) => {
    const newExpanded = new Set(expandedTables);
    if (newExpanded.has(tableName)) {
      newExpanded.delete(tableName);
    } else {
      newExpanded.add(tableName);
    }
    setExpandedTables(newExpanded);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin text-violet-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-error-500 text-sm">
        <p className="font-medium">
          {t("schemaBrowser.failedToLoadSchema", "Failed to load schema")}
        </p>
        <p className="mt-1 opacity-80">{String(error)}</p>
      </div>
    );
  }

  // Render SQL database schema (PostgreSQL, MySQL)
  if (schemaInfo?.tables) {
    return (
      <div className="p-4 space-y-2">
        <div className="flex items-center gap-2 text-xs font-medium text-foreground-secondary uppercase mb-3">
          <Database className="w-4 h-4" />
          {t("schemaBrowser.tables", "Tables")} ({schemaInfo.tables.length})
        </div>
        {schemaInfo.tables.map((table) => (
          <div key={table.name} className="space-y-1">
            {/* Table name */}
            <button
              type="button"
              onClick={() => {
                toggleTable(table.name);
                onTableSelect?.(table.name);
              }}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-background-tertiary text-left group transition-colors"
            >
              {expandedTables.has(table.name) ? (
                <ChevronDown className="w-4 h-4 text-foreground-secondary flex-shrink-0" />
              ) : (
                <ChevronRight className="w-4 h-4 text-foreground-secondary flex-shrink-0" />
              )}
              <Table className="w-4 h-4 text-violet-500 flex-shrink-0" />
              <span className="font-medium text-foreground text-sm">
                {table.name}
              </span>
              {table.rowCount !== undefined && (
                <span className="ml-auto text-xs text-foreground-secondary">
                  {t("schemaBrowser.rowCount", "{{count}} rows", {
                    count: table.rowCount,
                  })}
                </span>
              )}
            </button>

            {/* Columns (when expanded) */}
            {expandedTables.has(table.name) && (
              <div className="ml-6 space-y-0.5">
                {table.columns?.map((column) => (
                  <div
                    key={column.name}
                    className="flex items-center gap-2 px-2 py-1 text-xs rounded hover:bg-background-tertiary"
                  >
                    <Key
                      className={`w-3 h-3 flex-shrink-0 ${
                        column.isPrimaryKey
                          ? "text-warning-500"
                          : "text-foreground-secondary opacity-50"
                      }`}
                    />
                    <span className="font-mono text-foreground">
                      {column.name}
                    </span>
                    <span className="text-foreground-secondary">
                      {column.type}
                    </span>
                    {!column.nullable && (
                      <span className="text-error-500 text-[10px]">
                        {t("schemaBrowser.notNull", "NOT NULL")}
                      </span>
                    )}
                    {column.isForeignKey && (
                      <span className="text-violet-500 text-[10px]">FK</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  }

  // Render MongoDB schema (collections)
  if (schemaInfo?.collections) {
    return (
      <div className="p-4 space-y-2">
        <div className="flex items-center gap-2 text-xs font-medium text-foreground-secondary uppercase mb-3">
          <FileJson className="w-4 h-4" />
          {t("schemaBrowser.collections", "Collections")} (
          {schemaInfo.collections.length})
        </div>
        {schemaInfo.collections.map((collection) => (
          <button
            key={collection.name}
            type="button"
            onClick={() => onTableSelect?.(collection.name)}
            className="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-background-tertiary text-left group transition-colors"
          >
            <FileJson className="w-4 h-4 text-violet-500 flex-shrink-0" />
            <span className="font-medium text-foreground text-sm">
              {collection.name}
            </span>
            {collection.documentCount !== undefined && (
              <span className="ml-auto text-xs text-foreground-secondary">
                {t("schemaBrowser.documentCount", "{{count}} docs", {
                  count: collection.documentCount,
                })}
              </span>
            )}
          </button>
        ))}
      </div>
    );
  }

  // Render Redis keys
  if (schemaInfo?.keys) {
    return (
      <div className="p-4 space-y-2">
        <div className="flex items-center gap-2 text-xs font-medium text-foreground-secondary uppercase mb-3">
          <Key className="w-4 h-4" />
          {t("schemaBrowser.keys", "Keys")} ({schemaInfo.keys.length})
        </div>
        {schemaInfo.keys.map((keyInfo) => (
          <button
            key={keyInfo.key}
            type="button"
            onClick={() => onTableSelect?.(keyInfo.key)}
            className="w-full flex items-center gap-2 px-2 py-1.5 rounded hover:bg-background-tertiary text-left group transition-colors"
          >
            <Key className="w-4 h-4 text-violet-500 flex-shrink-0" />
            <span className="font-mono text-foreground text-sm">
              {keyInfo.key}
            </span>
            <span className="ml-auto text-xs text-foreground-secondary">
              {keyInfo.type}
            </span>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="p-4 text-foreground-secondary text-sm text-center">
      {t("schemaBrowser.noSchemaInfo", "No schema information available")}
    </div>
  );
}
