import type { Provider } from "#/types/settings";
import type {
  UserRepositoriesResponse,
  InstallationRepositoriesResponse,
  InstallationPageParam,
} from "./query-functions";
import {
  fetchUserRepositories,
  fetchInstallationRepositories,
} from "./query-functions";
import {
  getNextPageParamForInstallation,
  getNextPageParamForUser,
} from "./pagination-helpers";

export function createQueryFn(
  provider: Provider,
  useInstallationRepos: boolean,
  installations: string[] | undefined,
  pageSize: number,
) {
  return async ({
    pageParam,
  }: {
    pageParam: number | InstallationPageParam;
  }) => {
    if (!provider) {
      throw new Error("Provider is required");
    }

    if (useInstallationRepos) {
      return fetchInstallationRepositories(
        provider,
        pageParam as InstallationPageParam,
        installations || [],
        pageSize,
      );
    }

    return fetchUserRepositories(provider, pageParam as number, pageSize);
  };
}

export function createGetNextPageParam(useInstallationRepos: boolean) {
  return (
    lastPage: UserRepositoriesResponse | InstallationRepositoriesResponse,
  ) => {
    if (useInstallationRepos) {
      return getNextPageParamForInstallation(
        lastPage as InstallationRepositoriesResponse,
      );
    }

    return getNextPageParamForUser(lastPage as UserRepositoriesResponse);
  };
}

export function createQueryKey(
  providers: unknown[],
  provider: Provider,
  useInstallationRepos: boolean,
  pageSize: number,
  installations: string[] | undefined,
): readonly unknown[] {
  return [
    "repositories",
    providers || [],
    provider,
    useInstallationRepos,
    pageSize,
    ...(useInstallationRepos ? [installations || []] : []),
  ] as readonly unknown[];
}

export function shouldEnableQuery(
  enabled: boolean,
  providers: unknown[],
  provider: Provider | null,
  useInstallationRepos: boolean,
  installations: string[] | undefined,
): boolean {
  return (
    enabled &&
    (providers || []).length > 0 &&
    !!provider &&
    (!useInstallationRepos ||
      (Array.isArray(installations) && installations.length > 0))
  );
}
