/**
 * ForgeClient — thin facade over domain-specific service modules.
 *
 * All consumers import `ForgeClient` (default export) and call static methods.
 * The heavy implementations now live in:
 *   ./forge-helpers   – shared state, URL builders, normalisation
 *   ./file-service    – getFiles, getFile, uploadFiles (with retry logic)
 *   ./git-service     – git user, repos, branches, diffs
 */

import {
  GetConfigResponse,
  Conversation,
  ResultSet,
  GetTrajectoryResponse,
  SuggestedTask,
  CreatePlaybook,
  GetPlaybooksResponse,
  RepositoryPlaybook,
  PlaybookContentResponse,
} from "#/api/forge.types";
import { Forge } from "./forge-axios";
import { ApiSettings, PostApiSettings, Provider } from "#/types/settings";

// Shared helpers
import {
  getCurrentConversation as _getCurrentConversation,
  setCurrentConversation as _setCurrentConversation,
  getBase,
  getConversationUrl,
  normalizeConversation,
} from "./forge-helpers";

// Domain services
import {
  getFiles as _getFiles,
  getFile as _getFile,
  uploadFiles as _uploadFiles,
} from "./file-service";
import {
  getGitUser as _getGitUser,
  searchGitRepositories as _searchGitRepositories,
  getGitChanges as _getGitChanges,
  getGitChangeDiff as _getGitChangeDiff,
  retrieveUserGitRepositories as _retrieveUserGitRepositories,
  retrieveInstallationRepositories as _retrieveInstallationRepositories,
  getRepositoryBranches as _getRepositoryBranches,
  searchRepositoryBranches as _searchRepositoryBranches,
} from "./git-service";

class ForgeClient {
  // -----------------------------------------------------------------------
  // Conversation state
  // -----------------------------------------------------------------------

  static getCurrentConversation(): Conversation | null {
    return _getCurrentConversation();
  }

  static setCurrentConversation(c: Conversation | null): void {
    _setCurrentConversation(c);
  }

  static getConversationUrl(conversationId: string): string {
    return getConversationUrl(conversationId);
  }

  // -----------------------------------------------------------------------
  // Options / config
  // -----------------------------------------------------------------------

  static async getModels(): Promise<string[]> {
    const { data } = await Forge.get<string[]>(
      `${getBase()}/options/models`,
    );
    return data;
  }

  static async getAgents(): Promise<string[]> {
    const { data } = await Forge.get<string[]>(
      `${getBase()}/options/agents`,
    );
    return data;
  }

  static async getSecurityAnalyzers(): Promise<string[]> {
    const { data } = await Forge.get<string[]>(
      `${getBase()}/options/security-analyzers`,
    );
    return data;
  }

  static async getConfig(): Promise<GetConfigResponse> {
    const { data } = await Forge.get<GetConfigResponse>(
      `${getBase()}/options/config`,
    );
    return data;
  }

  // -----------------------------------------------------------------------
  // Auth
  // -----------------------------------------------------------------------

  static async authenticate(appMode: "oss" | "saas"): Promise<boolean> {
    if (appMode === "oss") return true;
    await Forge.post("/api/authenticate");
    return true;
  }

  static async logout(appMode: "saas" | "oss" = "oss"): Promise<void> {
    if (appMode === "saas") {
      await Forge.post(`${getBase()}/logout`);
    } else {
      await Forge.post(`${getBase()}/unset-provider-tokens`);
    }
  }

  // -----------------------------------------------------------------------
  // Settings
  // -----------------------------------------------------------------------

  static async getSettings(): Promise<ApiSettings> {
    const response = await Forge.get<ApiSettings>(`${getBase()}/settings`);
    return response.data;
  }

  static async saveSettings(
    settings: Partial<PostApiSettings>,
  ): Promise<boolean> {
    const data = await Forge.post(`${getBase()}/settings`, settings);
    return data.status === 200;
  }

  // -----------------------------------------------------------------------
  // Conversations
  // -----------------------------------------------------------------------

  static async getUserConversations(
    limit: number = 20,
    pageId?: string,
  ): Promise<ResultSet<Conversation>> {
    const params = new URLSearchParams();
    params.append("limit", limit.toString());
    if (pageId) params.append("page_id", pageId);

    const { data } = await Forge.get<ResultSet<Conversation>>(
      `/api/conversations?${params.toString()}`,
    );
    return {
      ...data,
      results: Array.isArray(data.results)
        ? data.results.map(normalizeConversation)
        : data.results,
    };
  }

  static async searchConversations(
    selectedRepository?: string,
    conversationTrigger?: string,
    limit: number = 100,
  ): Promise<Conversation[]> {
    const params = new URLSearchParams();
    params.append("limit", limit.toString());
    if (selectedRepository)
      params.append("selected_repository", selectedRepository);
    if (conversationTrigger)
      params.append("conversation_trigger", conversationTrigger);

    const { data } = await Forge.get<ResultSet<Conversation>>(
      `/api/conversations?${params.toString()}`,
    );
    return Array.isArray(data.results)
      ? data.results.map(normalizeConversation)
      : data.results;
  }

  static async getWebHosts(conversationId: string): Promise<string[]> {
    const { data } = await Forge.get<{ hosts: string[] }>(
      `/api/conversations/${conversationId}/web-hosts`,
    );
    return data.hosts;
  }

  static async deleteUserConversation(conversationId: string): Promise<void> {
    await Forge.delete(`/api/conversations/${conversationId}`);
  }

  static async createConversation(
    selectedRepository?: string,
    git_provider?: Provider,
    initialUserMsg?: string,
    suggested_task?: SuggestedTask,
    selected_branch?: string,
    conversationInstructions?: string,
    create_playbook?: CreatePlaybook,
  ): Promise<Conversation> {
    const body: Record<string, unknown> = {};
    if (selectedRepository !== undefined) body.repository = selectedRepository;
    if (git_provider !== undefined) body.git_provider = git_provider;
    if (selected_branch !== undefined) body.selected_branch = selected_branch;
    if (initialUserMsg !== undefined) body.initial_user_msg = initialUserMsg;
    if (suggested_task !== undefined) body.suggested_task = suggested_task;
    if (conversationInstructions !== undefined)
      body.conversation_instructions = conversationInstructions;
    if (create_playbook !== undefined) body.create_playbook = create_playbook;

    const { data } = await Forge.post<Conversation>(
      `${getBase()}/conversations`,
      body,
    );
    return normalizeConversation(data);
  }

  static async getConversation(
    conversationId: string,
  ): Promise<Conversation | null> {
    const { data } = await Forge.get<Conversation | null>(
      `/api/conversations/${conversationId}`,
    );
    return data ? normalizeConversation(data) : data;
  }

  static async startConversation(
    conversationId: string,
  ): Promise<Conversation | null> {
    const { data } = await Forge.post<Conversation | null>(
      `/api/conversations/${conversationId}/start`,
      {},
    );
    return data ? normalizeConversation(data) : data;
  }

  static async stopConversation(
    conversationId: string,
  ): Promise<Conversation | null> {
    const { data } = await Forge.post<Conversation | null>(
      `/api/conversations/${conversationId}/stop`,
    );
    return data ? normalizeConversation(data) : data;
  }

  static async updateConversation(
    conversationId: string,
    updates: { title: string },
  ): Promise<boolean> {
    const { data } = await Forge.patch<boolean>(
      `/api/conversations/${conversationId}`,
      updates,
    );
    return data;
  }

  static async getWorkspaceZip(conversationId: string): Promise<Blob> {
    const url = `${getConversationUrl(conversationId)}/zip-directory`;
    const response = await Forge.get(url, {
      responseType: "blob",
    });
    return response.data;
  }

  static async getRuntimeId(
    conversationId: string,
  ): Promise<{ runtime_id: string }> {
    const url = `${getConversationUrl(conversationId)}/config`;
    const { data } = await Forge.get<{ runtime_id: string }>(url);
    return data;
  }

  static async getTrajectory(
    conversationId: string,
    opts?: { sinceId?: number; limit?: number },
  ): Promise<GetTrajectoryResponse> {
    const url = `${getConversationUrl(conversationId)}/trajectory`;
    const params: Record<string, number> = {};
    if (opts?.sinceId != null && opts.sinceId >= 0) params.since_id = opts.sinceId;
    if (opts?.limit != null) params.limit = opts.limit;
    const { data } = await Forge.get<GetTrajectoryResponse>(url, { params });
    return data;
  }

  // -----------------------------------------------------------------------
  // Playbooks
  // -----------------------------------------------------------------------

  static async getPlaybooks(
    conversationId: string,
  ): Promise<GetPlaybooksResponse> {
    const url = `${getConversationUrl(conversationId)}/playbooks`;
    const { data } = await Forge.get<GetPlaybooksResponse>(url);
    return data;
  }

  static async getRepositoryPlaybooks(
    owner: string,
    repo: string,
  ): Promise<RepositoryPlaybook[]> {
    const url = `${getBase()}/repository/${owner}/${repo}/playbooks`;
    const { data } = await Forge.get<RepositoryPlaybook[]>(url);
    return data;
  }

  static async getRepositoryPlaybookContent(
    owner: string,
    repo: string,
    filePath: string,
  ): Promise<PlaybookContentResponse> {
    const url = `${getBase()}/repository/${owner}/${repo}/playbooks/content`;
    const { data } = await Forge.get<PlaybookContentResponse>(url, {
      params: { file_path: filePath },
    });
    return data;
  }

  static async getPlaybookManagementConversations(
    selectedRepository: string,
    pageId?: string,
    limit: number = 100,
  ): Promise<Conversation[]> {
    const params: Record<string, string | number> = {
      limit,
      selected_repository: selectedRepository,
    };
    if (pageId) params.page_id = pageId;

    const { data } = await Forge.get<ResultSet<Conversation>>(
      `${getBase()}/playbook-management/conversations`,
      { params },
    );
    return Array.isArray(data.results)
      ? data.results.map(normalizeConversation)
      : data.results;
  }

  // -----------------------------------------------------------------------
  // File operations (delegated to file-service)
  // -----------------------------------------------------------------------

  static getFiles = _getFiles;
  static getFile = _getFile;
  static uploadFiles = _uploadFiles;

  // -----------------------------------------------------------------------
  // Git operations (delegated to git-service)
  // -----------------------------------------------------------------------

  static getGitUser = _getGitUser;
  static searchGitRepositories = _searchGitRepositories;
  static getGitChanges = _getGitChanges;
  static getGitChangeDiff = _getGitChangeDiff;
  static retrieveUserGitRepositories = _retrieveUserGitRepositories;
  static retrieveInstallationRepositories = _retrieveInstallationRepositories;
  static getRepositoryBranches = _getRepositoryBranches;
  static searchRepositoryBranches = _searchRepositoryBranches;

  // -----------------------------------------------------------------------
  // User / provider
  // -----------------------------------------------------------------------

  static async getUserInstallationIds(provider: Provider): Promise<string[]> {
    const { data } = await Forge.get<string[]>(
      `/api/user/installations?provider=${provider}`,
    );
    return data;
  }

  // -----------------------------------------------------------------------
  // Feedback
  // -----------------------------------------------------------------------

  static async checkFeedbackExists(
    conversationId: string,
    index: number,
  ): Promise<{ exists: boolean }> {
    try {
      const response = await Forge.get<{ exists: boolean }>(
        `${getConversationUrl(conversationId)}/feedback/exists`,
        { params: { index } },
      );
      return response.data;
    } catch {
      return { exists: false };
    }
  }

  static async submitFeedback(
    conversationId: string,
    feedback: any,
  ): Promise<any> {
    const response = await Forge.post(
      `${getConversationUrl(conversationId)}/submit-feedback`,
      feedback,
    );
    return response.data;
  }

  static async submitConversationFeedback(
    conversationId: string,
    rating: number,
  ): Promise<any> {
    const response = await Forge.post("/feedback/conversation", {
      rating,
      metadata: { source: "likert-scale" },
      conversation_id: conversationId,
    });
    return response.data;
  }

  // -----------------------------------------------------------------------
  // Billing
  // -----------------------------------------------------------------------

  static async getSubscriptionAccess(): Promise<any> {
    const { data } = await Forge.get("/api/billing/subscription-access");
    return data;
  }
}

export default ForgeClient;
