import { GitRepository } from "#/types/git";
import { Provider } from "#/types/settings";
import Forge from "#/api/forge";

export interface UserRepositoriesResponse {
  data: GitRepository[];
  nextPage: number | null;
}

export interface InstallationRepositoriesResponse {
  data: GitRepository[];
  nextPage: number | null;
  installationIndex: number | null;
}

export interface InstallationPageParam {
  installationIndex: number | null;
  repoPage: number | null;
}

export async function fetchUserRepositories(
  provider: Provider,
  pageParam: number,
  pageSize: number,
): Promise<UserRepositoriesResponse> {
  return Forge.retrieveUserGitRepositories(provider, pageParam, pageSize);
}

export async function fetchInstallationRepositories(
  provider: Provider,
  pageParam: InstallationPageParam,
  installations: string[],
  pageSize: number,
): Promise<InstallationRepositoriesResponse> {
  const { repoPage, installationIndex } = pageParam;

  if (!installations) {
    throw new Error("Missing installation list");
  }

  return Forge.retrieveInstallationRepositories(
    provider,
    installationIndex || 0,
    installations,
    repoPage || 1,
    pageSize,
  );
}
