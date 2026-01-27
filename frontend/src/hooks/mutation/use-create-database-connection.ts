import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createDatabaseConnection } from "#/api/database-connections";
import { DatabaseConnection } from "#/types/database";

export function useCreateDatabaseConnection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (connection: Omit<DatabaseConnection, "id" | "createdAt" | "updatedAt">) =>
      createDatabaseConnection(connection),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["database-connections"] });
    },
  });
}
