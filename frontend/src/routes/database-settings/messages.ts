import { useMemo } from "react";
import type { TFunction } from "i18next";

export interface DatabaseSettingsMessages {
  saveSuccess: string;
  deleteSuccess: string;
  saveError: (message: string) => string;
  deleteError: (message: string) => string;
}

export function useDatabaseSettingsMessages(
  t: TFunction,
): DatabaseSettingsMessages {
  return useMemo(
    () => ({
      saveSuccess: t(
        "databaseSettings.toast.saveSuccess",
        "Database connection saved successfully",
      ),
      deleteSuccess: t(
        "databaseSettings.toast.deleteSuccess",
        "Database connection deleted successfully",
      ),
      saveError: (message: string) =>
        t("databaseSettings.toast.saveError", {
          message,
          defaultValue: "Failed to save connection: {{message}}",
        }),
      deleteError: (message: string) =>
        t("databaseSettings.toast.deleteError", {
          message,
          defaultValue: "Failed to delete connection: {{message}}",
        }),
    }),
    [t],
  );
}
