import { useMemo } from "react";
import type { TFunction } from "i18next";
import type { DatabaseType } from "#/types/database";

export interface DatabaseOption {
  type: DatabaseType;
  label: string;
}

export function useDatabaseOptions(t: TFunction): DatabaseOption[] {
  return useMemo(
    () =>
      [
        {
          type: "postgresql" as DatabaseType,
          label: t("databaseSettings.types.postgresql", "PostgreSQL"),
        },
        {
          type: "mongodb" as DatabaseType,
          label: t("databaseSettings.types.mongodb", "MongoDB"),
        },
        {
          type: "mysql" as DatabaseType,
          label: t("databaseSettings.types.mysql", "MySQL"),
        },
        {
          type: "redis" as DatabaseType,
          label: t("databaseSettings.types.redis", "Redis"),
        },
      ] satisfies Array<{ type: DatabaseType; label: string }>,
    [t],
  );
}
