import { AxiosHeaders } from "axios";
import {
  Feedback,
  FeedbackResponse,
  GitHubAccessTokenResponse,
  GetConfigResponse,
  GetVSCodeUrlResponse,
  AuthenticateResponse,
  Conversation,
  ResultSet,
  GetTrajectoryResponse,
  GitChangeDiff,
  GitChange,
  GetMicroagentsResponse,
  GetMicroagentPromptResponse,
  CreateMicroagent,
  MicroagentContentResponse,
  FileUploadSuccessResponse,
  GetFilesResponse,
  GetFileResponse,
} from "#/api/forge.types";
import { Forge } from "./forge-axios";
import { ApiSettings, PostApiSettings, Provider } from "#/types/settings";
import {
  GitUser,
  GitRepository,
  PaginatedBranchesResponse,
  Branch,
} from "#/types/git";
import { SuggestedTask } from "#/components/features/home/tasks/task.types";
import { extractNextPageFromLink } from "#/utils/extract-next-page-from-link";
import { RepositoryMicroagent } from "#/types/microagent-management";
import { BatchFeedbackData } from "#/hooks/query/use-batch-feedback";
import { SubscriptionAccess } from "#/types/billing";
import { getAPIBase, CURRENT_API_VERSION } from "#/config/api-config";

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
   * Send feedback to the server
   * @param data Feedback data
   * @returns The stored feedback data
   */
  static async submitFeedback(
    conversationId: string,
    feedback: Feedback,
  ): Promise<FeedbackResponse> {
    const url = `/api/conversations/${conversationId}/submit-feedback`;
    const { data } = await Forge.post<FeedbackResponse>(url, feedback);
    return data;
  }

  /**
   * Submit conversation feedback with rating
   * @param conversationId The conversation ID
   * @param rating The rating (1-5)
   * @param eventId Optional event ID this feedback corresponds to
   * @param reason Optional reason for the rating
   * @returns Response from the feedback endpoint
   */
  static async submitConversationFeedback(
    conversationId: string,
    rating: number,
    eventId?: number,
    reason?: string,
  ): Promise<{ status: string; message: string }> {
    const url = `/feedback/conversation`;
    const payload = {
      conversation_id: conversationId,
      event_id: eventId,
      rating,
      reason,
      metadata: { source: "likert-scale" },
    };
    const { data } = await Forge.post<{ status: string; message: string }>(
      url,
      payload,
    );
    return data;
  }

  /**
   * Check if feedback exists for a specific conversation and event
   * @param conversationId The conversation ID
   * @param eventId The event ID to check
   * @returns Feedback data including existence, rating, and reason
   */
  static async checkFeedbackExists(
    conversationId: string,
    eventId: number,
  ): Promise<{ exists: boolean; rating?: number; reason?: string }> {
    try {
      const url = `/feedback/conversation/${conversationId}/${eventId}`;
      const { data } = await Forge.get<{
        exists: boolean;
        rating?: number;
        reason?: string;
      }>(url);
      return data;
    } catch (error) {
      // Error checking if feedback exists
      return { exists: false };
    }
  }

  /**
   * Get feedback for multiple events in a conversation
   * @param conversationId The conversation ID
   * @returns Map of event IDs to feedback data including existence, rating, reason and metadata
   */
  static async getBatchFeedback(conversationId: string): Promise<
    Record<
      string,
      {
        exists: boolean;
        rating?: number;
        reason?: string;
        metadata?: Record<string, BatchFeedbackData>;
      }
    >
  > {
    const url = `/feedback/conversation/${conversationId}/batch`;
    const { data } = await Forge.get<
      Record<
        string,
        {
          exists: boolean;
          rating?: number;
          reason?: string;
          metadata?: Record<string, BatchFeedbackData>;
        }
      >
    >(url);

    return data;
  }

  /**
   * Authenticate with GitHub token
   * @returns Response with authentication status and user info if successful
   */
  static async authenticate(
    appMode: GetConfigResponse["APP_MODE"],
  ): Promise<boolean> {
    if (appMode === "oss") {
      return true;
    }

    // Just make the request, if it succeeds (no exception thrown), return true
    await Forge.post<AuthenticateResponse>(`${this.getBase()}/authenticate`);
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

  /**
   * Get the web hosts
   * @returns Array of web hosts
   */
  static async getWebHosts(conversationId: string): Promise<string[]> {
    const url = `${this.getConversationUrl(conversationId)}/web-hosts`;
    const response = await Forge.get(url, {
      headers: this.getConversationHeaders(),
    });
    return Object.keys(response.data.hosts);
  }

  /**
   * @param code Code provided by GitHub
   * @returns GitHub access token
   */
  static async getGitHubAccessToken(
    code: string,
  ): Promise<GitHubAccessTokenResponse> {
    const { data } = await Forge.post<GitHubAccessTokenResponse>(
      `${this.getBase()}/keycloak/callback`,
      {
        code,
      },
    );
    return data;
  }

  /**
   * Get the VSCode URL
   * @returns VSCode URL
   */
  static async getVSCodeUrl(
    conversationId: string,
  ): Promise<GetVSCodeUrlResponse> {
    const baseUrl = this.getConversationUrl(conversationId);
    const url = `${baseUrl}/vscode-url`;
    const { data } = await Forge.get<GetVSCodeUrlResponse>(url, {
      headers: this.getConversationHeaders(),
    });
    return data;
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
    return data;
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
    return data.results;
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
    createMicroagent?: CreateMicroagent,
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
    if (createMicroagent !== undefined) {
      body.create_microagent = createMicroagent;
    }

    const { data } = await Forge.post<Conversation>(
      `${this.getBase()}/conversations`,
      body,
    );

    return data;
  }

  static async getConversation(
    conversationId: string,
  ): Promise<Conversation | null> {
    const { data } = await Forge.get<Conversation | null>(
      `/api/conversations/${conversationId}`,
    );

    return data;
  }

  static async startConversation(
    conversationId: string,
    providers?: Provider[],
  ): Promise<Conversation | null> {
    const { data } = await Forge.post<Conversation | null>(
      `/api/conversations/${conversationId}/start`,
      providers ? { providers_set: providers } : {},
    );

    return data;
  }

  static async stopConversation(
    conversationId: string,
  ): Promise<Conversation | null> {
    const { data } = await Forge.post<Conversation | null>(
      `/api/conversations/${conversationId}/stop`,
    );

    return data;
  }

  /**
   * Trigger a MetaSOP debug run for a conversation.
   * Useful for validating that MetaSOP orchestration can be scheduled.
   */
  static async triggerMetaSopDebug(
    conversationId: string,
    message: string = "sop: validation run",
  ): Promise<{ started: boolean; message?: string }> {
    const url = `${this.getConversationUrl(conversationId)}/metasop-debug`;
    const { data } = await Forge.post<{
      started: boolean;
      message?: string;
    }>(url, { message }, { headers: this.getConversationHeaders() });
    return data;
  }

  /**
   * Send a raw text event to the conversation (POST /events/raw).
   * Useful as a fallback when the dedicated metasop-debug helper fails.
   */
  static async sendRawEvent(
    conversationId: string,
    text: string,
    create: boolean = false,
  ): Promise<{ success: boolean; note?: string }> {
    const url = `${this.getConversationUrl(conversationId)}/events/raw${create ? "?create=true" : ""}`;
    // axios will set content-type for plain text when provided in headers
    const { data } = await Forge.post<{ success: boolean; note?: string }>(
      url,
      text,
      {
        headers: {
          "Content-Type": "text/plain",
          ...this.getConversationHeaders(),
        },
      },
    );
    return data;
  }

  /**
   * Get the settings from the server or use the default settings if not found
   */
  static async getSettings(): Promise<ApiSettings> {
    const { data } = await Forge.get<ApiSettings>(`${this.getBase()}/settings`);
    return data;
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

  static async createCheckoutSession(amount: number): Promise<string> {
    const { data } = await Forge.post(
      `${this.getBase()}/billing/create-checkout-session`,
      {
        amount,
      },
    );
    return data.redirect_url;
  }

  static async createBillingSessionResponse(): Promise<string> {
    const { data } = await Forge.post(
      `${this.getBase()}/billing/create-customer-setup-session`,
    );
    return data.redirect_url;
  }

  static async getBalance(): Promise<string> {
    const { data } = await Forge.get<{ credits: string }>(
      `${this.getBase()}/billing/credits`,
    );
    return data.credits;
  }

  static async getSubscriptionAccess(): Promise<SubscriptionAccess | null> {
    const { data } = await Forge.get<SubscriptionAccess | null>(
      `${this.getBase()}/billing/subscription-access`,
    );
    return data;
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
    selected_provider?: Provider,
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

  static async logout(appMode: GetConfigResponse["APP_MODE"]): Promise<void> {
    const endpoint =
      appMode === "saas"
        ? `${this.getBase()}/logout`
        : `${this.getBase()}/unset-provider-tokens`;
    await Forge.post(endpoint);
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
    selected_provider: Provider,
    page = 1,
    per_page = 30,
  ) {
    const { data } = await Forge.get<GitRepository[]>(
      `${this.getBase()}/user/repositories`,
      {
        params: {
          selected_provider,
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
    selected_provider: Provider,
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
          selected_provider,
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
    selectedProvider?: Provider,
  ): Promise<Branch[]> {
    const { data } = await Forge.get<Branch[]>(`/api/user/search/branches`, {
      params: {
        repository,
        query,
        per_page: perPage,
        selected_provider: selectedProvider,
      },
    });
    return data;
  }

  /**
   * Get the available microagents associated with a conversation
   * @param conversationId The ID of the conversation
   * @returns The available microagents associated with the conversation
   */
  static async getMicroagents(
    conversationId: string,
  ): Promise<GetMicroagentsResponse> {
    const url = `${this.getConversationUrl(conversationId)}/microagents`;
    const { data } = await Forge.get<GetMicroagentsResponse>(url, {
      headers: this.getConversationHeaders(),
    });
    return data;
  }

  /**
   * Get the available microagents for a repository
   * @param owner The repository owner
   * @param repo The repository name
   * @returns The available microagents for the repository
   */
  static async getRepositoryMicroagents(
    owner: string,
    repo: string,
  ): Promise<RepositoryMicroagent[]> {
    const { data } = await Forge.get<RepositoryMicroagent[]>(
      `/api/user/repository/${owner}/${repo}/microagents`,
    );
    return data;
  }

  /**
   * Get the content of a specific microagent from a repository
   * @param owner The repository owner
   * @param repo The repository name
   * @param filePath The path to the microagent file within the repository
   * @returns The microagent content and metadata
   */
  static async getRepositoryMicroagentContent(
    owner: string,
    repo: string,
    filePath: string,
  ): Promise<MicroagentContentResponse> {
    const { data } = await Forge.get<MicroagentContentResponse>(
      `/api/user/repository/${owner}/${repo}/microagents/content`,
      {
        params: { file_path: filePath },
      },
    );
    return data;
  }

  static async getMicroagentPrompt(
    conversationId: string,
    eventId: number,
  ): Promise<string> {
    const url = `${this.getConversationUrl(conversationId)}/remember-prompt`;
    const { data } = await Forge.get<GetMicroagentPromptResponse>(url, {
      params: { event_id: eventId },
      headers: this.getConversationHeaders(),
    });

    return data.prompt;
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

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const { data } = await Forge.get<GetFilesResponse>(url, {
          params: { path },
          headers: this.getConversationHeaders(),
        });
        return data;
      } catch (err: unknown) {
        const errorMsg = safeErrorMessage(err);

        // 503 = Runtime container is permanently dead/crashed - don't retry
        if ((err as any)?.response?.status === 503) {
          console.error(
            "❌ Runtime container permanently unavailable:",
            errorMsg,
          );
          // Mark agent as errored so UI can recover
          const { setCurrentAgentState } = await import("#/state/agent-slice");
          const { default: store } = await import("#/store");
          const { AgentState } = await import("#/types/agent-state");
          store.dispatch(setCurrentAgentState(AgentState.ERROR));
          throw new Error(
            "Runtime container unavailable. Please start a new conversation.",
          );
        }

        // Retryable errors (500) - retry with exponential backoff
        const isRuntimeUnavailable =
          errorMsg.includes("Runtime unavailable") ||
          errorMsg.includes("Connection refused") ||
          (err as any)?.response?.status === 500;

        if (isRuntimeUnavailable && attempt < maxRetries) {
          console.warn(
            `Runtime temporarily unavailable, retrying file list (${attempt}/${maxRetries})...`,
          );
          await new Promise((resolve) =>
            setTimeout(resolve, retryDelayMs * attempt),
          ); // Exponential backoff
          continue;
        }

        // Final attempt failed
        throw err;
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
      console.error("❌ Runtime container permanently unavailable:", errorMsg);
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

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const { data } = await Forge.get<GetFileResponse>(url, {
          params: { file: path },
          headers: this.getConversationHeaders(),
        });
        return data.code;
      } catch (err: unknown) {
        const responseStatus = (err as any)?.response?.status;
        const errorMsg = safeErrorMessage(err);

        nonRetryableError(errorMsg, responseStatus);

        if (responseStatus === 503) {
          await handlePermanentFailure(errorMsg);
        }

        if (shouldRetry(errorMsg, responseStatus) && attempt < maxRetries) {
          console.warn(
            `Runtime temporarily unavailable, retrying (${attempt}/${maxRetries})...`,
          );
          await new Promise((resolve) =>
            setTimeout(resolve, retryDelayMs * attempt),
          );
          continue;
        }

        throw err;
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
    return data.results;
  }
}

export default ForgeClient;
