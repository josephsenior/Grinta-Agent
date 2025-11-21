import { Download, Clock, Hash } from "lucide-react";
import { useTranslation } from "react-i18next";

interface QueryResultsProps {
  results: QueryResult | null;
  isLoading?: boolean;
  error?: string | null;
}

interface QueryResult {
  data?: QueryDataRow[];
  columns?: string[];
  rowCount?: number;
  executionTime?: number;
  affectedRows?: number;
  success: boolean;
  error?: string;
}

type QueryDataRow = Record<string, unknown>;

type QueryState =
  | { type: "loading" }
  | { type: "error"; message: string }
  | { type: "empty" }
  | { type: "failure"; message: string }
  | {
      type: "nonSelect";
      affectedRows?: number;
      executionTime?: number;
    }
  | {
      type: "table";
      data: QueryDataRow[];
      displayColumns: string[];
      executionTime?: number;
      rowCount?: number;
    };

const renderLoadingState = (t: ReturnType<typeof useTranslation>["t"]) => (
  <div className="flex items-center justify-center p-12">
    <div className="text-center">
      <div className="animate-spin w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full mx-auto mb-4" />
      <p className="text-sm text-foreground-secondary">
        {t("queryResults.executing", "Executing query...")}
      </p>
    </div>
  </div>
);

const renderErrorState = (
  message: string,
  t: ReturnType<typeof useTranslation>["t"],
) => (
  <div className="p-6">
    <div className="p-4 bg-error-500/10 border border-error-500 rounded-lg text-error-500">
      <p className="font-medium mb-2">
        {t("queryResults.queryError", "Query Error")}
      </p>
      <pre className="text-sm font-mono whitespace-pre-wrap">{message}</pre>
    </div>
  </div>
);

const renderEmptyState = (t: ReturnType<typeof useTranslation>["t"]) => (
  <div className="flex items-center justify-center p-12">
    <p className="text-foreground-secondary text-sm">
      {t("queryResults.runQueryToSeeResults", "Run a query to see results")}
    </p>
  </div>
);

const renderFailureState = (
  message: string,
  t: ReturnType<typeof useTranslation>["t"],
) => (
  <div className="p-6">
    <div className="p-4 bg-error-500/10 border border-error-500 rounded-lg text-error-500">
      <p className="font-medium">
        {t("queryResults.queryFailed", "Query failed")}
      </p>
      <p className="text-sm mt-1">{message}</p>
    </div>
  </div>
);

const renderNonSelectState = (
  {
    affectedRows,
    executionTime,
  }: {
    affectedRows?: number;
    executionTime?: number;
  },
  t: ReturnType<typeof useTranslation>["t"],
) => (
  <div className="p-6">
    <div className="p-4 bg-success-500/10 border border-success-500 rounded-lg text-success-500">
      <p className="font-medium">
        {t(
          "queryResults.queryExecutedSuccessfully",
          "Query executed successfully",
        )}
      </p>
      <div className="flex items-center gap-4 mt-2 text-sm">
        {typeof affectedRows === "number" && (
          <div className="flex items-center gap-1">
            <Hash className="w-4 h-4" />
            <span>
              {t("queryResults.rowsAffected", "{{count}} rows affected", {
                count: affectedRows,
              })}
            </span>
          </div>
        )}
        {typeof executionTime === "number" && (
          <div className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            <span>
              {t("queryResults.executionTime", "{{time}}s", {
                time: executionTime,
              })}
            </span>
          </div>
        )}
      </div>
    </div>
  </div>
);

const createCsvPayload = (columns: string[], data: QueryDataRow[]) =>
  [
    columns.join(","),
    ...data.map((row) =>
      columns.map((column) => JSON.stringify(row[column] ?? "")).join(","),
    ),
  ].join("\n");

const handleCsvExport = (columns: string[], data: QueryDataRow[]) => {
  const csv = createCsvPayload(columns, data);
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `query-results-${Date.now()}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
};

const renderTableState = (
  {
    data,
    displayColumns,
    executionTime,
    rowCount,
  }: Extract<QueryState, { type: "table" }>,
  t: ReturnType<typeof useTranslation>["t"],
) => (
  <div className="flex flex-col h-full">
    <div className="flex items-center justify-between p-3 border-b border-border bg-background-secondary">
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-1 text-foreground">
          <Hash className="w-4 h-4" />
          <span className="font-medium">
            {t("queryResults.rows", "{{count}} rows", {
              count: rowCount ?? data.length,
            })}
          </span>
        </div>
        {typeof executionTime === "number" && (
          <div className="flex items-center gap-1 text-foreground-secondary">
            <Clock className="w-4 h-4" />
            <span>
              {t("queryResults.executionTime", "{{time}}s", {
                time: executionTime,
              })}
            </span>
          </div>
        )}
      </div>
      <button
        type="button"
        onClick={() => handleCsvExport(displayColumns, data)}
        className="flex items-center gap-2 px-3 py-1.5 text-sm text-foreground-secondary hover:text-foreground bg-background-tertiary hover:bg-background-primary rounded transition-colors"
      >
        <Download className="w-4 h-4" />
        {t("queryResults.exportCsv", "Export CSV")}
      </button>
    </div>

    <div className="flex-1 overflow-auto">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-background-tertiary border-b border-border">
          <tr>
            {displayColumns.map((column) => (
              <th
                key={column}
                className="px-4 py-2 text-left font-medium text-foreground border-r border-border last:border-r-0"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              className="border-b border-border hover:bg-background-tertiary transition-colors"
            >
              {displayColumns.map((column) => (
                <td
                  key={column}
                  className="px-4 py-2 text-foreground border-r border-border last:border-r-0 font-mono text-xs"
                >
                  {typeof row[column] === "object"
                    ? JSON.stringify(row[column])
                    : String(row[column] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

function evaluateQueryStatus({
  isLoading,
  error,
  results,
}: {
  isLoading: boolean;
  error: string | null;
  results: QueryResult | null;
}): QueryState | null {
  if (isLoading) {
    return { type: "loading" };
  }

  if (error) {
    return { type: "error", message: error };
  }

  if (!results) {
    return { type: "empty" };
  }

  if (!results.success) {
    return { type: "failure", message: results.error ?? "Unknown error" };
  }

  if (!results.data || results.data.length === 0) {
    return {
      type: "nonSelect",
      affectedRows: results.affectedRows,
      executionTime: results.executionTime,
    };
  }

  return null;
}

function buildTableState(results: QueryResult): QueryState {
  const { data = [], columns, executionTime, rowCount } = results;
  const displayColumns =
    columns && columns.length > 0 ? columns : Object.keys(data[0] ?? {});

  return {
    type: "table",
    data,
    displayColumns,
    executionTime,
    rowCount,
  };
}

const getQueryState = ({
  isLoading,
  error,
  results,
}: {
  isLoading: boolean;
  error: string | null;
  results: QueryResult | null;
}): QueryState => {
  const earlyState = evaluateQueryStatus({ isLoading, error, results });
  if (earlyState) {
    return earlyState;
  }

  return buildTableState(results!);
};

export function QueryResults({
  results,
  isLoading = false,
  error = null,
}: QueryResultsProps) {
  const { t } = useTranslation();
  const state = getQueryState({ isLoading, error, results });

  switch (state.type) {
    case "loading":
      return renderLoadingState(t);
    case "error":
      return renderErrorState(state.message, t);
    case "empty":
      return renderEmptyState(t);
    case "failure":
      return renderFailureState(state.message, t);
    case "nonSelect":
      return renderNonSelectState(state, t);
    case "table":
      return renderTableState(state, t);
    default:
      return null;
  }
}
