import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteDatabaseConnection } from "#/api/database-connections";

export function useDeleteDatabaseConnection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteDatabaseConnection(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["database-connections"] });
    },
  });
}
