import React from "react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DatabaseBrowserScreen from "#/routes/database-browser";
import { renderWithProviders } from "../../test-utils";

vi.setConfig({ hookTimeout: 30000 });

const mockNavigate = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useSearchParams: () => [mockSearchParams, vi.fn()],
  };
});

const mockUseDatabaseConnections = vi.fn();
const mockUseExecuteQuery = vi.fn();

vi.mock("#/hooks/query/use-database-connections", () => ({
  useDatabaseConnections: () => mockUseDatabaseConnections(),
  useExecuteQuery: () => mockUseExecuteQuery(),
}));

const successToast = vi.fn();
const errorToast = vi.fn();

vi.mock("#/utils/custom-toast-handlers", () => ({
  displaySuccessToast: (...args: unknown[]) => successToast(...args),
  displayErrorToast: (...args: unknown[]) => errorToast(...args),
}));

let schemaBrowserProps: any;
let latestQueryEditorProps: any;
let queryResultsProps: any;

vi.mock("#/components/features/database-browser/schema-browser", () => ({
  SchemaBrowser: (props: any) => {
    schemaBrowserProps = props;
    return <div data-testid="schema-browser" />;
  },
}));

vi.mock("#/components/features/database-browser/query-editor", () => ({
  QueryEditor: (props: any) => {
    latestQueryEditorProps = props;
    return (
      <div data-testid="query-editor">
        <span data-testid="current-query">{props.defaultQuery}</span>
      </div>
    );
  },
}));

vi.mock("#/components/features/database-browser/query-results", () => ({
  QueryResults: (props: any) => {
    queryResultsProps = props;
    return <div data-testid="query-results" />;
  },
}));

let lastExecuteOptions: { onSuccess?: (data: any) => void; onError?: (err: unknown) => void } | undefined;

beforeEach(() => {
  mockSearchParams = new URLSearchParams();
  mockNavigate.mockReset();
  successToast.mockReset();
  errorToast.mockReset();
  mockUseDatabaseConnections.mockReset();
  mockUseExecuteQuery.mockReset();
  schemaBrowserProps = undefined;
  latestQueryEditorProps = undefined;
  queryResultsProps = undefined;
  lastExecuteOptions = undefined;
});

afterEach(() => {
  schemaBrowserProps = undefined;
  latestQueryEditorProps = undefined;
  queryResultsProps = undefined;
  lastExecuteOptions = undefined;
});

describe("DatabaseBrowserScreen", () => {
  it("renders empty state when no connection is selected", async () => {
    mockUseDatabaseConnections.mockReturnValue({ data: [] });
    mockUseExecuteQuery.mockReturnValue({ mutate: vi.fn(), isPending: false, data: undefined });

    renderWithProviders(<DatabaseBrowserScreen />);

    expect(screen.getByText("No Connection Selected")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Go to Database Settings" }));
    expect(mockNavigate).toHaveBeenCalledWith("/settings/databases");
  });

  it("renders connection details and executes queries", async () => {
    mockSearchParams = new URLSearchParams([["connection", "conn-1"]]);
    const connection = {
      id: "conn-1",
      name: "Prod Database",
      type: "postgres",
      host: "db.internal",
      port: 5432,
      status: "connected",
    };
    mockUseDatabaseConnections.mockReturnValue({ data: [connection] });

    const mutateSpy = vi.fn((args: any, options: any) => {
      lastExecuteOptions = options;
      return options;
    });
    mockUseExecuteQuery.mockReturnValue({
      mutate: mutateSpy,
      isPending: false,
      data: { error: null, success: false },
    });

    renderWithProviders(<DatabaseBrowserScreen />);

    expect(screen.getByText("Prod Database")).toBeInTheDocument();
    expect(screen.getByText("POSTGRES • db.internal:5432")).toBeInTheDocument();
    expect(schemaBrowserProps.connection).toEqual(connection);
    expect(queryResultsProps.results).toEqual({ error: null, success: false });

    schemaBrowserProps.onTableSelect("users");
    await waitFor(() => expect(latestQueryEditorProps.defaultQuery).toBe("SELECT * FROM users LIMIT 10;"));

    latestQueryEditorProps.onExecute("SELECT 1");
    expect(mutateSpy).toHaveBeenCalledWith(
      { connectionId: "conn-1", query: "SELECT 1" },
      expect.any(Object),
    );

    lastExecuteOptions?.onSuccess?.({ success: true, executionTime: 1.5, rowCount: 7 });
    expect(successToast).toHaveBeenCalledWith("Query executed in 1.5s - 7 rows");

    const successCalls = successToast.mock.calls.length;
    lastExecuteOptions?.onSuccess?.({ success: false, executionTime: 0.2, rowCount: 0 });
    expect(successToast.mock.calls.length).toBe(successCalls);

    lastExecuteOptions?.onSuccess?.({ success: true, executionTime: 0.7, affectedRows: 4 });
    expect(successToast).toHaveBeenCalledWith("Query executed in 0.7s - 4 rows");

    lastExecuteOptions?.onSuccess?.({ success: true, executionTime: 0.4 });
    expect(successToast).toHaveBeenCalledWith("Query executed in 0.4s - 0 rows");

    lastExecuteOptions?.onError?.(new Error("boom"));
    expect(errorToast).toHaveBeenCalledWith("Query failed: boom");

    lastExecuteOptions?.onError?.("nope");
    expect(errorToast).toHaveBeenCalledWith("Query failed: Unknown error");

    await userEvent.click(screen.getByTitle("Back to home"));
    expect(mockNavigate).toHaveBeenCalledWith("/");
  });

  it("auto-fills queries based on connection type", async () => {
    mockSearchParams = new URLSearchParams([["connection", "mongo-1"]]);
    const connections = [
      {
        id: "mongo-1",
        name: "Mongo",
        type: "mongodb",
        host: "localhost",
        port: 27017,
        status: "connected",
      },
    ];
    mockUseDatabaseConnections.mockReturnValue({ data: connections });
    mockUseExecuteQuery.mockReturnValue({ mutate: vi.fn(), isPending: false, data: undefined });

    const firstRender = renderWithProviders(<DatabaseBrowserScreen />);
    schemaBrowserProps.onTableSelect("orders");
    await waitFor(() =>
      expect(latestQueryEditorProps.defaultQuery).toBe("db.orders.find().limit(10)"),
    );
    expect(screen.getByText("connected")).toBeInTheDocument();

    firstRender.unmount();

    mockSearchParams = new URLSearchParams([["connection", "redis-1"]]);
    mockUseDatabaseConnections.mockReturnValue({
      data: [
        {
          id: "redis-1",
          name: "Redis",
          type: "redis",
          host: "localhost",
          port: 6379,
          status: undefined,
        },
      ],
    });

    const secondRender = renderWithProviders(<DatabaseBrowserScreen />);
    schemaBrowserProps.onTableSelect("session-key");
    await waitFor(() => expect(latestQueryEditorProps.defaultQuery).toBe("GET session-key"));
    expect(screen.getByText("untested")).toBeInTheDocument();
    secondRender.unmount();
  });
});
