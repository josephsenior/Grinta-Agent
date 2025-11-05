/**
 * React Query hooks for database connections
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as dbAPI from "#/api/database-connections";
import type {
  DatabaseConnection,
  TestConnectionRequest,
  QueryRequest,
} from "#/types/database";

/**
 * Fetch all database connections
 */
export function useDatabaseConnections() {
  return useQuery({
    queryKey: ["database-connections"],
    queryFn: dbAPI.listDatabaseConnections,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Create a new database connection
 */
export function useCreateDatabaseConnection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: dbAPI.createDatabaseConnection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["database-connections"] });
    },
  });
}

/**
 * Update an existing database connection
 */
export function useUpdateDatabaseConnection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      connectionId,
      updates,
    }: {
      connectionId: string;
      updates: Partial<DatabaseConnection>;
    }) => dbAPI.updateDatabaseConnection(connectionId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["database-connections"] });
    },
  });
}

/**
 * Delete a database connection
 */
export function useDeleteDatabaseConnection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: dbAPI.deleteDatabaseConnection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["database-connections"] });
    },
  });
}

/**
 * Get database schema (tables, collections, or keys)
 */
export function useDatabaseSchema(connectionId: string | null) {
  return useQuery({
    queryKey: ["database-schema", connectionId],
    queryFn: () => dbAPI.getDatabaseSchema(connectionId!),
    enabled: !!connectionId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Execute a query against a database
 */
export function useExecuteQuery() {
  return useMutation({
    mutationFn: ({
      connectionId,
      query,
      limit,
      timeout,
    }: {
      connectionId: string;
      query: string;
      limit?: number;
      timeout?: number;
    }) => dbAPI.executeQuery(connectionId, query, limit, timeout),
  });
}

/**
 * Test a database connection (no caching, always fresh)
 */
export function useTestDatabaseConnection() {
  return useMutation({
    mutationFn: (request: TestConnectionRequest) =>
      dbAPI.testDatabaseConnection(request),
  });
}
