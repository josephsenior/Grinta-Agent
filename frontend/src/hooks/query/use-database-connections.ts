import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listDatabaseConnections,
  createDatabaseConnection,
  updateDatabaseConnection,
  deleteDatabaseConnection,
  testDatabaseConnection,
  getDatabaseSchema,
  executeQuery,
} from "#/api/database-connections";
import type {
  DatabaseConnection,
  TestConnectionRequest,
  TestConnectionResponse,
} from "#/types/database";

export function useDatabaseConnections() {
  return useQuery<DatabaseConnection[]>({
    queryKey: ["database-connections"],
    queryFn: listDatabaseConnections,
  });
}

export function useCreateDatabaseConnection() {
  const queryClient = useQueryClient();
  return useMutation<
    DatabaseConnection,
    Error,
    Omit<DatabaseConnection, "id" | "createdAt" | "updatedAt">
  >({
    mutationFn: createDatabaseConnection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["database-connections"] });
    },
  });
}

export function useUpdateDatabaseConnection() {
  const queryClient = useQueryClient();
  return useMutation<
    DatabaseConnection,
    Error,
    { id: string; updates: Partial<DatabaseConnection> }
  >({
    mutationFn: ({ id, updates }) => updateDatabaseConnection(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["database-connections"] });
    },
  });
}

export function useDeleteDatabaseConnection() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: deleteDatabaseConnection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["database-connections"] });
    },
  });
}

export function useTestDatabaseConnection() {
  return useMutation<TestConnectionResponse, Error, TestConnectionRequest>({
    mutationFn: testDatabaseConnection,
  });
}

export function useDatabaseSchema(connectionId: string | undefined) {
  return useQuery({
    queryKey: ["database-schema", connectionId],
    queryFn: () => getDatabaseSchema(connectionId!),
    enabled: !!connectionId,
  });
}

export function useExecuteDatabaseQuery() {
  return useMutation<
    any,
    Error,
    { connectionId: string; query: string; limit?: number; timeout?: number }
  >({
    mutationFn: ({ connectionId, query, limit, timeout }) =>
      executeQuery(connectionId, query, limit, timeout),
  });
}
