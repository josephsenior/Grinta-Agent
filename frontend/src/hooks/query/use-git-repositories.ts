import { useInfiniteQuery } from "@tanstack/react-query";
import { useConfig } from "./use-config";
import { useUserProviders } from "../use-user-providers";
import { useAppInstallations } from "./use-app-installations";
import { Provider } from "../../types/settings";
import { shouldUseInstallationRepos } from "#/utils/utils";

import { createQueryConfig } from "./use-git-repositories/query-config";

interface UseGitRepositoriesOptions {
  provider: Provider | null;
  pageSize?: number;
  enabled?: boolean;
}

export function useGitRepositories(options: UseGitRepositoriesOptions) {
  const { provider, pageSize = 30, enabled = true } = options;
  const { providers } = useUserProviders();
  const { data: config } = useConfig();
  const { data: installations } = useAppInstallations(provider);

  const useInstallationRepos = provider
    ? shouldUseInstallationRepos(provider, config?.APP_MODE)
    : false;

  const queryConfig = createQueryConfig(
    provider!,
    useInstallationRepos,
    installations,
    pageSize,
    enabled,
    providers || [],
  );

  const repos = useInfiniteQuery(queryConfig);

  const onLoadMore = () => {
    if (repos.hasNextPage && !repos.isFetchingNextPage) {
      repos.fetchNextPage();
    }
  };

  return {
    data: repos.data,
    isLoading: repos.isLoading,
    isError: repos.isError,
    hasNextPage: repos.hasNextPage,
    isFetchingNextPage: repos.isFetchingNextPage,
    fetchNextPage: repos.fetchNextPage,
    onLoadMore,
  };
}
