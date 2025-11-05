import { Download, Clock, Hash } from "lucide-react";

interface QueryResultsProps {
  results: any;
  isLoading?: boolean;
  error?: string | null;
}

export function QueryResults({
  results,
  isLoading = false,
  error = null,
}: QueryResultsProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-sm text-foreground-secondary">Executing query...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="p-4 bg-error-500/10 border border-error-500 rounded-lg text-error-500">
          <p className="font-medium mb-2">Query Error</p>
          <pre className="text-sm font-mono whitespace-pre-wrap">{error}</pre>
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="flex items-center justify-center p-12">
        <p className="text-foreground-secondary text-sm">
          Run a query to see results
        </p>
      </div>
    );
  }

  const { data, columns, rowCount, executionTime, affectedRows, success } =
    results;

  if (!success) {
    return (
      <div className="p-6">
        <div className="p-4 bg-error-500/10 border border-error-500 rounded-lg text-error-500">
          <p className="font-medium">Query failed</p>
          <p className="text-sm mt-1">{results.error || "Unknown error"}</p>
        </div>
      </div>
    );
  }

  // For non-SELECT queries (INSERT, UPDATE, DELETE)
  if (!data || data.length === 0) {
    return (
      <div className="p-6">
        <div className="p-4 bg-success-500/10 border border-success-500 rounded-lg text-success-500">
          <p className="font-medium">Query executed successfully</p>
          <div className="flex items-center gap-4 mt-2 text-sm">
            {affectedRows !== undefined && (
              <div className="flex items-center gap-1">
                <Hash className="w-4 h-4" />
                <span>{affectedRows} rows affected</span>
              </div>
            )}
            {executionTime !== undefined && (
              <div className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                <span>{executionTime}s</span>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // For SELECT queries - display table
  const displayColumns = columns || Object.keys(data[0] || {});

  return (
    <div className="flex flex-col h-full">
      {/* Results header */}
      <div className="flex items-center justify-between p-3 border-b border-border bg-background-secondary">
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1 text-foreground">
            <Hash className="w-4 h-4" />
            <span className="font-medium">{rowCount || data.length} rows</span>
          </div>
          {executionTime !== undefined && (
            <div className="flex items-center gap-1 text-foreground-secondary">
              <Clock className="w-4 h-4" />
              <span>{executionTime}s</span>
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => {
            // Simple CSV export
            const csv = [
              displayColumns.join(","),
              ...data.map((row: any) =>
                displayColumns.map((col: string) => JSON.stringify(row[col] ?? "")).join(","),
              ),
            ].join("\n");
            const blob = new Blob([csv], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `query-results-${Date.now()}.csv`;
            a.click();
            URL.revokeObjectURL(url);
          }}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-foreground-secondary hover:text-foreground bg-background-tertiary hover:bg-background-primary rounded transition-colors"
        >
          <Download className="w-4 h-4" />
          Export CSV
        </button>
      </div>

      {/* Results table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-background-tertiary border-b border-border">
            <tr>
              {displayColumns.map((col: string) => (
                <th
                  key={col}
                  className="px-4 py-2 text-left font-medium text-foreground border-r border-border last:border-r-0"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row: any, rowIndex: number) => (
              <tr
                key={rowIndex}
                className="border-b border-border hover:bg-background-tertiary transition-colors"
              >
                {displayColumns.map((col: string) => (
                  <td
                    key={col}
                    className="px-4 py-2 text-foreground border-r border-border last:border-r-0 font-mono text-xs"
                  >
                    {typeof row[col] === "object"
                      ? JSON.stringify(row[col])
                      : String(row[col] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

