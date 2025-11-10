import { useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Database, ArrowLeft } from "lucide-react";
import {
  useDatabaseConnections,
  useExecuteQuery,
} from "#/hooks/query/use-database-connections";
import { SchemaBrowser } from "#/components/features/database-browser/schema-browser";
import { QueryEditor } from "#/components/features/database-browser/query-editor";
import { QueryResults } from "#/components/features/database-browser/query-results";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";

function DatabaseBrowserScreen() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const connectionId = searchParams.get("connection");

  const { data: connections } = useDatabaseConnections();
  const {
    mutate: executeQuery,
    isPending,
    data: queryResults,
  } = useExecuteQuery();

  const [currentQuery, setCurrentQuery] = useState("");

  // Find the selected connection
  const connection = connections?.find((c) => c.id === connectionId);

  const handleExecuteQuery = (query: string) => {
    if (!connectionId) return;

    setCurrentQuery(query);
    executeQuery(
      { connectionId, query },
      {
        onSuccess: (data) => {
          if (data.success) {
            displaySuccessToast(
              `Query executed in ${data.executionTime}s - ${data.rowCount || data.affectedRows || 0} rows`,
            );
          }
        },
        onError: (error) => {
          displayErrorToast(
            `Query failed: ${error instanceof Error ? error.message : "Unknown error"}`,
          );
        },
      },
    );
  };

  const handleTableSelect = (tableName: string) => {
    // Auto-fill query when table is selected
    if (connection?.type === "mongodb") {
      setCurrentQuery(`db.${tableName}.find().limit(10)`);
    } else if (connection?.type === "redis") {
      setCurrentQuery(`GET ${tableName}`);
    } else {
      setCurrentQuery(`SELECT * FROM ${tableName} LIMIT 10;`);
    }
  };

  if (!connectionId || !connection) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background-primary">
        <div className="text-center">
          <Database className="w-12 h-12 text-foreground-secondary mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-foreground mb-2">
            No Connection Selected
          </h2>
          <p className="text-foreground-secondary mb-4">
            Please select a database connection to browse
          </p>
          <button
            type="button"
            onClick={() => navigate("/settings/databases")}
            className="px-4 py-2 bg-brand-500 text-white rounded-md hover:bg-brand-600 transition-colors"
          >
            Go to Database Settings
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-background-primary">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-background-secondary">
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="p-2 hover:bg-background-tertiary rounded-md transition-colors"
            title="Back to home"
          >
            <ArrowLeft className="w-5 h-5 text-foreground-secondary" />
          </button>
          <div className="flex items-center gap-3">
            <Database className="w-6 h-6 text-brand-500" />
            <div>
              <h1 className="text-lg font-semibold text-foreground">
                {connection.name}
              </h1>
              <p className="text-sm text-foreground-secondary">
                {connection.type.toUpperCase()} • {connection.host}:
                {connection.port}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-1 text-xs font-medium rounded ${
              connection.status === "connected"
                ? "bg-success-500/10 text-success-500"
                : "bg-foreground-secondary/10 text-foreground-secondary"
            }`}
          >
            {connection.status || "untested"}
          </span>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar - Schema Browser */}
        <div className="w-64 border-r border-border bg-background-secondary overflow-y-auto">
          <SchemaBrowser
            connection={connection}
            onTableSelect={handleTableSelect}
          />
        </div>

        {/* Right side - Query Editor and Results */}
        <div className="flex-1 flex flex-col">
          {/* Query Editor (top half) */}
          <div className="h-1/2 border-b border-border">
            <QueryEditor
              onExecute={handleExecuteQuery}
              isExecuting={isPending}
              defaultQuery={currentQuery}
            />
          </div>

          {/* Query Results (bottom half) */}
          <div className="h-1/2 bg-background-primary">
            <QueryResults
              results={queryResults}
              isLoading={isPending}
              error={queryResults?.error || null}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default DatabaseBrowserScreen;
