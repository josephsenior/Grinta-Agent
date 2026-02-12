/**
 * Git-related API operations for the Forge workspace.
 *
 * Extracted from ForgeClient — handles user info, repository search / listing,
 * branch operations, and diff retrieval.
 */

import {
  GitChangeDiff,
  GitChange,
} from "#/api/forge.types";
import { Forge } from "./forge-axios";
import {
  getBase,
  getConversationUrl,
} from "./forge-helpers";
import {
  GitUser,
  GitRepository,
  PaginatedBranchesResponse,
  Branch,
} from "#/types/git";
import { Provider } from "#/types/settings";
import { extractNextPageFromLink } from "#/utils/extract-next-page-from-link";

export async function getGitUser(): Promise<GitUser> {
  const response = await Forge.get<GitUser>(`${getBase()}/user/info`);
  const { data } = response;
  return {
    id: data.id,
    login: data.login,
    avatar_url: data.avatar_url,
    company: data.company,
    name: data.name,
    email: data.email,
  };
}

export async function searchGitRepositories(
  query: string,
  per_page = 5,
  selected_provider: Provider = "github",
): Promise<GitRepository[]> {
  const response = await Forge.get<GitRepository[]>(
    `${getBase()}/user/search/repositories`,
    {
      params: { query, per_page, selected_provider },
    },
  );
  return response.data;
}

export async function getGitChanges(
  conversationId: string,
): Promise<GitChange[]> {
  const url = `${getConversationUrl(conversationId)}/git/changes`;
  const { data } = await Forge.get<GitChange[]>(url);
  return data;
}

export async function getGitChangeDiff(
  conversationId: string,
  path: string,
): Promise<GitChangeDiff> {
  const url = `${getConversationUrl(conversationId)}/git/diff`;
  const { data } = await Forge.get<GitChangeDiff>(url, {
    params: { path },
  });
  return data;
}

export async function retrieveUserGitRepositories(
  provider: Provider,
  page = 1,
  per_page = 30,
) {
  const { data } = await Forge.get<GitRepository[]>(
    `${getBase()}/user/repositories`,
    {
      params: {
        selected_provider: provider,
        sort: "pushed",
        page,
        per_page,
      },
    },
  );

  const link =
    data.length > 0 && data[0].link_header ? data[0].link_header : "";
  const nextPage = extractNextPageFromLink(link);

  return { data, nextPage };
}

export async function retrieveInstallationRepositories(
  provider: Provider,
  installationIndex: number,
  installations: string[],
  page = 1,
  per_page = 30,
) {
  const installationId = installations[installationIndex];
  const response = await Forge.get<GitRepository[]>(
    `${getBase()}/user/repositories`,
    {
      params: {
        selected_provider: provider,
        sort: "pushed",
        page,
        per_page,
        installation_id: installationId,
      },
    },
  );
  const link =
    response.data.length > 0 && response.data[0].link_header
      ? response.data[0].link_header
      : "";
  const nextPage = extractNextPageFromLink(link);
  let nextInstallation: number | null;
  if (nextPage) {
    nextInstallation = installationIndex;
  } else if (installationIndex + 1 < installations.length) {
    nextInstallation = installationIndex + 1;
  } else {
    nextInstallation = null;
  }
  return {
    data: response.data,
    nextPage,
    installationIndex: nextInstallation,
  };
}

export async function getRepositoryBranches(
  repository: string,
  page: number = 1,
  perPage: number = 30,
): Promise<PaginatedBranchesResponse> {
  const { data } = await Forge.get<PaginatedBranchesResponse>(
    `/api/user/repository/branches?repository=${encodeURIComponent(repository)}&page=${page}&per_page=${perPage}`,
  );
  return data;
}

export async function searchRepositoryBranches(
  repository: string,
  query: string,
  perPage: number = 30,
  selected_provider: Provider = "github",
): Promise<Branch[]> {
  const { data } = await Forge.get<Branch[]>(`/api/user/search/branches`, {
    params: {
      repository,
      query,
      per_page: perPage,
      selected_provider,
    },
  });
  return data;
}
