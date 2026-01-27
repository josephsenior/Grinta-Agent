import { useConfig } from "#/hooks/query/use-config";
import { useSettings } from "#/hooks/query/use-settings";

export function useUserData() {
  const { data: config } = useConfig();
  const { data: settings } = useSettings();

  const isSaas = false;
  const hasProAccess = true; // Always true for core open source
  const userEmail = settings?.EMAIL ?? settings?.GIT_USER_EMAIL ?? "user@forge.core";
  const username = "Forge User";
  const isUserAdmin = true; // Always admin in local mode

  return {
    isSaas,
    hasProAccess,
    userEmail,
    username,
    isUserAdmin,
    balance: 0,
  };
}
