import { Provider } from "#/types/settings";

export const convertRawProvidersToList = (
  raw: Partial<Record<Provider, string | null>> | undefined,
): Provider[] => {
  if (!raw) {
    return [];
  }
  return Object.entries(raw)
    .filter(([_, value]) => !!value)
    .map(([key]) => key as Provider);
};
