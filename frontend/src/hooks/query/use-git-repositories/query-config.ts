import type { UseInfiniteQueryOptions } from "@tanstack/react-query";
import type { Provider } from "#/types/settings";
import type {
  UserRepositoriesResponse,
  InstallationRepositoriesResponse,
  InstallationPageParam,
} from "./query-functions";
import {
  createQueryFn,
  createGetNextPageParam,
  createQueryKey,
  shouldEnableQuery,
} from "./query-config-helpers";

export function createQueryConfig(
  provider: Provider,
  useInstallationRepos: boolean,
  installations: string[] | undefined,
  pageSize: number,
  enabled: boolean,
  providers: unknown[],
): UseInfiniteQueryOptions<
  UserRepositoriesResponse | InstallationRepositoriesResponse,
  Error,
  UserRepositoriesResponse | InstallationRepositoriesResponse,
  readonly unknown[],
  number | InstallationPageParam
> {
  return {
    queryKey: createQueryKey(
      providers,
      provider,
      useInstallationRepos,
      pageSize,
      installations,
    ),
    queryFn: createQueryFn(
      provider,
      useInstallationRepos,
      installations,
      pageSize,
    ),
    getNextPageParam: createGetNextPageParam(useInstallationRepos),
    initialPageParam: useInstallationRepos
      ? { installationIndex: 0, repoPage: 1 }
      : 1,
    enabled: shouldEnableQuery(
      enabled,
      providers,
      provider,
      useInstallationRepos,
      installations,
    ),
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 15, // 15 minutes
    refetchOnWindowFocus: false,
  };
}
