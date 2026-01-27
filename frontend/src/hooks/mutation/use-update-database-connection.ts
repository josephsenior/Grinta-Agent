import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateDatabaseConnection } from "#/api/database-connections";
import { DatabaseConnection } from "#/types/database";

export function useUpdateDatabaseConnection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      updates,
    }: {
      id: string;
      updates: Partial<DatabaseConnection>;
    }) => updateDatabaseConnection(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["database-connections"] });
    },
  });
}
