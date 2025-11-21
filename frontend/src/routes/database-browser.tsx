import { useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Database } from "lucide-react";
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
import { AppLayout } from "#/components/layout/AppLayout";
import { AuthGuard } from "#/components/features/auth/auth-guard";
import { Button } from "#/components/ui/button";
import { Card } from "#/components/ui/card";

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
      <AuthGuard>
        <AppLayout>
          <div className="space-y-8">
            {/* Page Title: Database Browser */}
            <div>
              <h1 className="text-[2.25rem] font-bold text-[#FFFFFF] leading-[1.2] mb-2">
                Database Browser
              </h1>
            </div>

            {/* No Connection Selected */}
            <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)] text-center">
              <Database className="w-12 h-12 text-[#94A3B8] mx-auto mb-4 opacity-50" />
              <h2 className="text-xl font-semibold text-[#FFFFFF] mb-2">
                No Connection Selected
              </h2>
              <p className="text-sm text-[#94A3B8] mb-4">
                Please select a database connection to browse
              </p>
              <Button
                onClick={() => navigate("/settings/databases")}
                className="bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed] text-white rounded-lg px-6 py-3 hover:brightness-110 active:brightness-95"
              >
                Go to Database Settings
              </Button>
            </Card>
          </div>
        </AppLayout>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <AppLayout>
        <div className="flex flex-col h-full min-h-0 space-y-6">
          {/* Page Title: Database Browser */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-[2.25rem] font-bold text-[#FFFFFF] leading-[1.2] mb-2">
                Database Browser
              </h1>
              <div className="flex items-center gap-3 mt-2">
                <div className="flex items-center gap-2">
                  <Database className="w-5 h-5 text-[#8b5cf6]" />
                  <span className="text-sm font-medium text-[#FFFFFF]">
                    {connection.name}
                  </span>
                </div>
                <span className="text-xs text-[#94A3B8]">•</span>
                <span className="text-xs text-[#94A3B8]">
                  {connection.type.toUpperCase()}
                </span>
                <span className="text-xs text-[#94A3B8]">•</span>
                <span className="text-xs text-[#94A3B8]">
                  {connection.host}:{connection.port}
                </span>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                    connection.status === "connected"
                      ? "bg-[rgba(16,185,129,0.12)] text-[#10B981]"
                      : "bg-[rgba(148,163,184,0.12)] text-[#94A3B8]"
                  }`}
                >
                  {connection.status || "untested"}
                </span>
              </div>
            </div>
          </div>

          {/* Main content: Schema Browser + Query Editor/Results */}
          <div className="flex flex-1 gap-6 min-h-0 overflow-hidden">
            {/* Left sidebar - Schema Browser */}
            <div className="w-64 flex-shrink-0 border border-[#1a1a1a] rounded-xl bg-[#000000] overflow-hidden">
              <SchemaBrowser
                connection={connection}
                onTableSelect={handleTableSelect}
              />
            </div>

            {/* Right side - Query Editor and Results */}
            <div className="flex-1 flex flex-col gap-6 min-h-0">
              {/* Query Editor */}
              <div className="flex-1 min-h-0 border border-[#1a1a1a] rounded-xl bg-[#000000] overflow-hidden">
                <QueryEditor
                  onExecute={handleExecuteQuery}
                  isExecuting={isPending}
                  defaultQuery={currentQuery}
                />
              </div>

              {/* Query Results */}
              <div className="flex-1 min-h-0 border border-[#1a1a1a] rounded-xl bg-[#000000] overflow-hidden">
                <QueryResults
                  results={queryResults ?? null}
                  isLoading={isPending}
                  error={queryResults?.error || null}
                />
              </div>
            </div>
          </div>
        </div>
      </AppLayout>
    </AuthGuard>
  );
}

export default DatabaseBrowserScreen;
