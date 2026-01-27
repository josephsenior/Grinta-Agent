import { AxiosHeaders, AxiosError } from "axios";
import {
  GetConfigResponse,
  Conversation,
  ResultSet,
  GetTrajectoryResponse,
  GitChangeDiff,
  GitChange,
  FileUploadSuccessResponse,
  GetFilesResponse,
  GetFileResponse,
  SuggestedTask,
  CreateMicroagent,
  GetMicroagentsResponse,
  RepositoryMicroagent,
  MicroagentContentResponse,
} from "#/api/forge.types";
import { ConversationStatus } from "#/types/conversation-status";
import { RuntimeStatus } from "#/types/runtime-status";
import { Forge } from "./forge-axios";
import { ApiSettings, PostApiSettings, Provider } from "#/types/settings";
import {
  GitUser,
  GitRepository,
  PaginatedBranchesResponse,
  Branch,
} from "#/types/git";
import { extractNextPageFromLink } from "#/utils/extract-next-page-from-link";
import { getAPIBase, CURRENT_API_VERSION } from "#/config/api-config";
import { logger } from "#/utils/logger";

/**
 * Safely extract a user-friendly error message from unknown error values.
 */
function safeErrorMessage(err: unknown): string {
  if (typeof err === "string") return err;
  if (err instanceof Error) return err.message;
  if (typeof err === "object" && err !== null) {
    const e = err as Record<string, unknown>;
    const resp = e.response as Record<string, unknown> | undefined;
    const data = resp?.data as Record<string, unknown> | undefined;
    const errorStr = data?.error;
    if (typeof errorStr === "string") return errorStr;
    const msg = e.message;
    if (typeof msg === "string") return msg;
  }
  return "";
}

function normalizeConversation(conversation: Conversation): Conversation {
  const statusRaw = conversation.status;
  const status = (
    typeof statusRaw === "string" ? statusRaw.toUpperCase() : statusRaw
  ) as ConversationStatus;

  const runtimeStatusRaw = conversation.runtime_status;
  const runtimeStatus = (
    typeof runtimeStatusRaw === "string"
      ? runtimeStatusRaw.toUpperCase()
      : runtimeStatusRaw
  ) as RuntimeStatus | null;

  return {
    ...conversation,
    status,
    runtime_status: runtimeStatus,
  };
}

class ForgeClient {
  private static currentConversation: Conversation | null = null;

  /**
   * Get API base URL (with or without versioning)
   * @returns API base URL
   */
  private static getBase(): string {
    return getAPIBase(CURRENT_API_VERSION);
  }

  /**
   * Get a current conversation
   * @return the current conversation
   */
  static getCurrentConversation(): Conversation | null {
    return this.currentConversation;
  }

  /**
   * Set a current conversation
   * @param url Custom URL to use for conversation endpoints
   */
  static setCurrentConversation(
    currentConversation: Conversation | null,
  ): void {
    this.currentConversation = currentConversation;
  }

  /**
   * Get the url for the conversation. If
   */
  static getConversationUrl(conversationId: string): string {
    if (
      this.currentConversation?.conversation_id === conversationId &&
      this.currentConversation.url
    ) {
      return this.currentConversation.url;
    }
    return `${this.getBase()}/conversations/${conversationId}`;
  }

  /**
   * Retrieve the list of models available
   * @returns List of models available
   */
  static async getModels(): Promise<string[]> {
    const { data } = await Forge.get<string[]>(
      `${this.getBase()}/options/models`,
    );
    return data;
  }

  /**
   * Retrieve the list of agents available
   * @returns List of agents available
   */
  static async getAgents(): Promise<string[]> {
    const { data } = await Forge.get<string[]>(
      `${this.getBase()}/options/agents`,
    );
    return data;
  }

  /**
   * Retrieve the list of security analyzers available
   * @returns List of security analyzers available
   */
  static async getSecurityAnalyzers(): Promise<string[]> {
    const { data } = await Forge.get<string[]>(
      `${this.getBase()}/options/security-analyzers`,
    );
    return data;
  }

  static async getConfig(): Promise<GetConfigResponse> {
    const { data } = await Forge.get<GetConfigResponse>(
      `${this.getBase()}/options/config`,
    );
    return data;
  }

  static getConversationHeaders(): AxiosHeaders {
    const headers = new AxiosHeaders();
    const sessionApiKey = this.currentConversation?.session_api_key;
    if (sessionApiKey) {
      headers.set("X-Session-API-Key", sessionApiKey);
    }
    return headers;
  }

  /**
   * Authenticate the user based on app mode
   * @param appMode Current application mode
   */
  static async authenticate(appMode: "oss" | "saas"): Promise<boolean> {
    if (appMode === "oss") return true;
    await Forge.post("/api/authenticate");
    return true;
  }

  /**
   * Get the blob of the workspace zip
   * @returns Blob of the workspace zip
   */
  static async getWorkspaceZip(conversationId: string): Promise<Blob> {
    const url = `${this.getConversationUrl(conversationId)}/zip-directory`;
    const response = await Forge.get(url, {
      responseType: "blob",
      headers: this.getConversationHeaders(),
    });
    return response.data;
  }

  static async getRuntimeId(
    conversationId: string,
  ): Promise<{ runtime_id: string }> {
    const url = `${this.getConversationUrl(conversationId)}/config`;
    const { data } = await Forge.get<{ runtime_id: string }>(url, {
      headers: this.getConversationHeaders(),
    });
    return data;
  }

  static async getUserConversations(
    limit: number = 20,
    pageId?: string,
  ): Promise<ResultSet<Conversation>> {
    const params = new URLSearchParams();
    params.append("limit", limit.toString());

    if (pageId) {
      params.append("page_id", pageId);
    }

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

    if (selectedRepository) {
      params.append("selected_repository", selectedRepository);
    }

    if (conversationTrigger) {
      params.append("conversation_trigger", conversationTrigger);
    }

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
    create_microagent?: CreateMicroagent,
  ): Promise<Conversation> {
    // Build body, only including defined values to avoid sending undefined/null
    const body: Record<string, unknown> = {};

    if (selectedRepository !== undefined) {
      body.repository = selectedRepository;
    }
    if (git_provider !== undefined) {
      body.git_provider = git_provider;
    }
    if (selected_branch !== undefined) {
      body.selected_branch = selected_branch;
    }
    if (initialUserMsg !== undefined) {
      body.initial_user_msg = initialUserMsg;
    }
    if (suggested_task !== undefined) {
      body.suggested_task = suggested_task;
    }
    if (conversationInstructions !== undefined) {
      body.conversation_instructions = conversationInstructions;
    }
    if (create_microagent !== undefined) {
      body.create_microagent = create_microagent;
    }

    const { data } = await Forge.post<Conversation>(
      `${this.getBase()}/conversations`,
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

  /**
   * Get the settings for the user
   * @returns ApiSettings
   */
  static async getSettings(): Promise<ApiSettings> {
    const response = await Forge.get<ApiSettings>(`${this.getBase()}/settings`);
    return response.data;
  }

  /**
   * Save the settings to the server. Only valid settings are saved.
   * @param settings - the settings to save
   */
  static async saveSettings(
    settings: Partial<PostApiSettings>,
  ): Promise<boolean> {
    const data = await Forge.post(`${this.getBase()}/settings`, settings);
    return data.status === 200;
  }

  static async getGitUser(): Promise<GitUser> {
    const response = await Forge.get<GitUser>(`${this.getBase()}/user/info`);

    const { data } = response;

    const user: GitUser = {
      id: data.id,
      login: data.login,
      avatar_url: data.avatar_url,
      company: data.company,
      name: data.name,
      email: data.email,
    };

    return user;
  }

  static async searchGitRepositories(
    query: string,
    per_page = 5,
    selected_provider: Provider = "github",
  ): Promise<GitRepository[]> {
    const response = await Forge.get<GitRepository[]>(
      `${this.getBase()}/user/search/repositories`,
      {
        params: {
          query,
          per_page,
          selected_provider,
        },
      },
    );

    return response.data;
  }

  static async getTrajectory(
    conversationId: string,
  ): Promise<GetTrajectoryResponse> {
    const url = `${this.getConversationUrl(conversationId)}/trajectory`;
    const { data } = await Forge.get<GetTrajectoryResponse>(url, {
      headers: this.getConversationHeaders(),
    });
    return data;
  }

  static async getMicroagents(
    conversationId: string,
  ): Promise<GetMicroagentsResponse> {
    const url = `${this.getConversationUrl(conversationId)}/microagents`;
    const { data } = await Forge.get<GetMicroagentsResponse>(url, {
      headers: this.getConversationHeaders(),
    });
    return data;
  }

  static async getRepositoryMicroagents(
    owner: string,
    repo: string,
  ): Promise<RepositoryMicroagent[]> {
    const url = `${this.getBase()}/repository/${owner}/${repo}/microagents`;
    const { data } = await Forge.get<RepositoryMicroagent[]>(url);
    return data;
  }

  static async getRepositoryMicroagentContent(
    owner: string,
    repo: string,
    filePath: string,
  ): Promise<MicroagentContentResponse> {
    const url = `${this.getBase()}/repository/${owner}/${repo}/microagents/content`;
    const { data } = await Forge.get<MicroagentContentResponse>(url, {
      params: { file_path: filePath },
    });
    return data;
  }

  static async logout(appMode: "saas" | "oss" = "oss"): Promise<void> {
    if (appMode === "saas") {
      await Forge.post(`${this.getBase()}/logout`);
    } else {
      await Forge.post(`${this.getBase()}/unset-provider-tokens`);
    }
  }

  static async getGitChanges(conversationId: string): Promise<GitChange[]> {
    const url = `${this.getConversationUrl(conversationId)}/git/changes`;
    const { data } = await Forge.get<GitChange[]>(url, {
      headers: this.getConversationHeaders(),
    });
    return data;
  }

  static async getGitChangeDiff(
    conversationId: string,
    path: string,
  ): Promise<GitChangeDiff> {
    const url = `${this.getConversationUrl(conversationId)}/git/diff`;
    const { data } = await Forge.get<GitChangeDiff>(url, {
      params: { path },
      headers: this.getConversationHeaders(),
    });
    return data;
  }

  /**
   * @returns A list of repositories
   */
  static async retrieveUserGitRepositories(
    provider: Provider,
    page = 1,
    per_page = 30,
  ) {
    const { data } = await Forge.get<GitRepository[]>(
      `${this.getBase()}/user/repositories`,
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

  static async retrieveInstallationRepositories(
    provider: Provider,
    installationIndex: number,
    installations: string[],
    page = 1,
    per_page = 30,
  ) {
    const installationId = installations[installationIndex];
    const response = await Forge.get<GitRepository[]>(
      `${this.getBase()}/user/repositories`,
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

  static async getRepositoryBranches(
    repository: string,
    page: number = 1,
    perPage: number = 30,
  ): Promise<PaginatedBranchesResponse> {
    const { data } = await Forge.get<PaginatedBranchesResponse>(
      `/api/user/repository/branches?repository=${encodeURIComponent(repository)}&page=${page}&per_page=${perPage}`,
    );

    return data;
  }

  static async searchRepositoryBranches(
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

  /**
   * Retrieve the list of files available in the workspace
   * @param conversationId ID of the conversation
   * @param path Path to list files from. If provided, it lists all the files in the given path
   * @returns List of files available in the given path. If path is not provided, it lists all the files in the workspace
   */
  static async getFiles(
    conversationId: string,
    path?: string,
  ): Promise<GetFilesResponse> {
    const url = `${this.getConversationUrl(conversationId)}/files/list-files`;

    // Retry logic for transient runtime failures
    const maxRetries = 3;
    const retryDelayMs = 1000;

    let attempt = 1;
    while (attempt <= maxRetries) {
      try {
        // eslint-disable-next-line no-await-in-loop
        const { data } = await Forge.get<GetFilesResponse>(url, {
          params: { path },
          headers: this.getConversationHeaders(),
        });
        return data;
      } catch (err: unknown) {
        const errorMsg = safeErrorMessage(err);
        const axiosError = err as AxiosError;
        const errorData = axiosError?.response?.data as
          | { error_code?: string }
          | undefined;
        const errorCode = errorData?.error_code;

        // 503 with RUNTIME_NOT_READY = Runtime is still starting up - retry
        if (
          axiosError?.response?.status === 503 &&
          errorCode === "RUNTIME_NOT_READY"
        ) {
          if (attempt < maxRetries) {
            logger.debug(
              `Runtime not ready yet, retrying file list (${attempt}/${maxRetries})...`,
            );
            const currentAttempt = attempt;
            // eslint-disable-next-line no-await-in-loop
            await new Promise<void>((resolve) => {
              setTimeout(() => {
                resolve();
              }, retryDelayMs * currentAttempt);
            });
            attempt += 1;
          } else {
            // After all retries, return empty array instead of throwing
            logger.warn(
              "Runtime not ready after retries, returning empty file list",
            );
            return [];
          }
        } else if (axiosError?.response?.status === 503) {
          // 503 = Runtime is permanently unavailable (crashed, not starting)
          logger.error("❌ Runtime unavailable (503):", errorMsg);
          // Mark agent as errored so UI can recover
          // eslint-disable-next-line no-await-in-loop
          const { setCurrentAgentState } = await import("#/state/agent-slice");
          // eslint-disable-next-line no-await-in-loop
          const { default: store } = await import("#/store");
          // eslint-disable-next-line no-await-in-loop
          const { AgentState } = await import("#/types/agent-state");
          store.dispatch(setCurrentAgentState(AgentState.ERROR));
          throw new Error(
            "Runtime unavailable. The runtime may be starting up or has encountered an error. Please try again or start a new conversation.",
          );
        } else {
          // Retryable errors (500) - retry with exponential backoff
          const isRuntimeUnavailable =
            errorMsg.includes("Runtime unavailable") ||
            errorMsg.includes("Connection refused") ||
            axiosError?.response?.status === 500;

          if (isRuntimeUnavailable && attempt < maxRetries) {
            logger.warn(
              `Runtime temporarily unavailable, retrying file list (${attempt}/${maxRetries})...`,
            );
            // Capture attempt value to avoid unsafe loop reference
            const currentAttempt = attempt;
            // eslint-disable-next-line no-await-in-loop
            await new Promise<void>((resolve) => {
              setTimeout(() => {
                resolve();
              }, retryDelayMs * currentAttempt);
            }); // Exponential backoff
            attempt += 1;
          } else {
            // Final attempt failed
            throw err;
          }
        }
      }
    }

    throw new Error("Failed to load files after retries");
  }

  /**
   * Retrieve the content of a file
   * @param conversationId ID of the conversation
   * @param path Full path of the file to retrieve
   * @returns Code content of the file
   */
  static async getFile(conversationId: string, path: string): Promise<string> {
    const url = `${this.getConversationUrl(conversationId)}/files/select-file`;

    const nonRetryableError = (errorMsg: string, status?: number) => {
      if (errorMsg.includes("directory")) {
        throw new Error("Cannot read directory as file");
      }

      if (errorMsg.includes("binary")) {
        throw new Error("Cannot read binary file");
      }

      if (status === 415) {
        throw new Error("Unsupported file type");
      }
    };

    const handlePermanentFailure = async (errorMsg: string) => {
      logger.error("❌ Runtime container permanently unavailable:", errorMsg);
      const { setCurrentAgentState } = await import("#/state/agent-slice");
      const { default: store } = await import("#/store");
      const { AgentState } = await import("#/types/agent-state");
      store.dispatch(setCurrentAgentState(AgentState.ERROR));
      throw new Error(
        "Runtime container unavailable. Please start a new conversation.",
      );
    };

    const shouldRetry = (errorMsg: string, status?: number) =>
      errorMsg.includes("Runtime unavailable") ||
      errorMsg.includes("Connection refused") ||
      status === 500;

    const maxRetries = 3;
    const retryDelayMs = 1000;

    let attempt = 1;
    while (attempt <= maxRetries) {
      try {
        // eslint-disable-next-line no-await-in-loop
        const { data } = await Forge.get<GetFileResponse>(url, {
          params: { file: path },
          headers: this.getConversationHeaders(),
        });
        return data.code;
      } catch (err: unknown) {
        const axiosError = err as AxiosError;
        const responseStatus = axiosError?.response?.status;
        const errorMsg = safeErrorMessage(err);

        nonRetryableError(errorMsg, responseStatus);

        if (responseStatus === 503) {
          // eslint-disable-next-line no-await-in-loop
          await handlePermanentFailure(errorMsg);
        }

        if (shouldRetry(errorMsg, responseStatus) && attempt < maxRetries) {
          logger.warn(
            `Runtime temporarily unavailable, retrying (${attempt}/${maxRetries})...`,
          );
          // Capture attempt value to avoid unsafe loop reference
          const currentAttempt = attempt;
          // eslint-disable-next-line no-await-in-loop
          await new Promise<void>((resolve) => {
            setTimeout(() => {
              resolve();
            }, retryDelayMs * currentAttempt);
          });
          attempt += 1;
        } else {
          throw err;
        }
      }
    }

    throw new Error("Failed to load file after retries");
  }

  /**
   * Upload multiple files to the workspace
   * @param conversationId ID of the conversation
   * @param files List of files.
   * @returns list of uploaded files, list of skipped files
   */
  static async uploadFiles(
    conversationId: string,
    files: File[],
  ): Promise<FileUploadSuccessResponse> {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }
    const url = `${this.getConversationUrl(conversationId)}/files/upload-files`;
    const response = await Forge.post<FileUploadSuccessResponse>(
      url,
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
          ...this.getConversationHeaders(),
        },
      },
    );
    return response.data;
  }

  /**
   * Get the user installation IDs
   * @param provider The provider to get installation IDs for (github, bitbucket, etc.)
   * @returns List of installation IDs
   */
  static async getUserInstallationIds(provider: Provider): Promise<string[]> {
    const { data } = await Forge.get<string[]>(
      `/api/user/installations?provider=${provider}`,
    );
    return data;
  }

  static async getMicroagentManagementConversations(
    selectedRepository: string,
    pageId?: string,
    limit: number = 100,
  ): Promise<Conversation[]> {
    const params: Record<string, string | number> = {
      limit,
      selected_repository: selectedRepository,
    };

    if (pageId) {
      params.page_id = pageId;
    }

    const { data } = await Forge.get<ResultSet<Conversation>>(
      `${this.getBase()}/microagent-management/conversations`,
      { params },
    );
    return Array.isArray(data.results)
      ? data.results.map(normalizeConversation)
      : data.results;
  }

  /**
   * Check if feedback exists for a specific message
   * @param conversationId ID of the conversation
   * @param index Index of the message
   * @returns Whether feedback exists
   */
  static async checkFeedbackExists(
    conversationId: string,
    index: number,
  ): Promise<{ exists: boolean }> {
    try {
      const response = await Forge.get<{ exists: boolean }>(
        `${this.getConversationUrl(conversationId)}/feedback/exists`,
        { params: { index } },
      );
      return response.data;
    } catch (err) {
      return { exists: false };
    }
  }

  /**
   * Submit feedback for a specific message
   * @param conversationId ID of the conversation
   * @param feedback Feedback data
   */
  static async submitFeedback(
    conversationId: string,
    feedback: any,
  ): Promise<any> {
    const response = await Forge.post(
      `${this.getConversationUrl(conversationId)}/submit-feedback`,
      feedback,
    );
    return response.data;
  }

  /**
   * Submit feedback for the entire conversation
   * @param conversationId ID of the conversation
   * @param rating Rating value
   */
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

  /**
   * Get subscription access details
   */
  static async getSubscriptionAccess(): Promise<any> {
    const { data } = await Forge.get("/api/billing/subscription-access");
    return data;
  }
}

export default ForgeClient;
