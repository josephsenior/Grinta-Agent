import type {
  UserRepositoriesResponse,
  InstallationRepositoriesResponse,
  InstallationPageParam,
} from "./query-functions";

export function getNextPageParamForInstallation(
  lastPage: InstallationRepositoriesResponse,
): InstallationPageParam | null {
  if (lastPage.nextPage) {
    return {
      installationIndex: lastPage.installationIndex,
      repoPage: lastPage.nextPage,
    };
  }

  if (lastPage.installationIndex !== null) {
    return {
      installationIndex: lastPage.installationIndex,
      repoPage: 1,
    };
  }

  return null;
}

export function getNextPageParamForUser(
  lastPage: UserRepositoriesResponse,
): number | null {
  return lastPage.nextPage;
}
