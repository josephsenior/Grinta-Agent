import { ConversationStatus } from "#/types/conversation-status";
import { RuntimeStatus } from "#/types/runtime-status";
import { Provider } from "#/types/settings";

export interface ErrorResponse {
  error: string;
}

export interface SaveFileSuccessResponse {
  message: string;
}

export interface FileUploadSuccessResponse {
  uploaded_files: string[];
  skipped_files: { name: string; reason: string }[];
}

export interface FeedbackBodyResponse {
  message: string;
  feedback_id: string;
  password: string;
}

export interface FeedbackResponse {
  statusCode: number;
  body: FeedbackBodyResponse;
}

export type GitChangeStatus = "M" | "A" | "D" | "R" | "U";

export interface GitHubAccessTokenResponse {
  access_token: string;
}

export interface AuthenticationResponse {
  message: string;
  login?: string; // Only present when allow list is enabled
}

export interface Feedback {
  version: string;
  email: string;
  token: string;
  polarity: "positive" | "negative";
  permissions: "public" | "private";
  trajectory: unknown[];
}

export interface GetConfigResponse {
  APP_MODE: "saas" | "oss";
  APP_SLUG?: string;
  GITHUB_CLIENT_ID: string;
  POSTHOG_CLIENT_KEY?: string;
  PROVIDERS_CONFIGURED?: Provider[];
  FEATURE_FLAGS: {
    ENABLE_BILLING?: boolean;
    HIDE_LLM_SETTINGS: boolean;
    ENABLE_JIRA?: boolean;
    ENABLE_JIRA_DC?: boolean;
    ENABLE_LINEAR?: boolean;
  };
  MAINTENANCE?: {
    startTime: string;
  };
}

export interface GetTrajectoryResponse {
  trajectory: unknown[] | null;
  error?: string;
}

export interface AuthenticateResponse {
  message?: string;
  error?: string;
}

export interface RepositorySelection {
  selected_repository: string | null;
  selected_branch: string | null;
  git_provider: Provider | null;
}

export type ConversationTrigger =
  | "resolver"
  | "gui"
  | "suggested_task"
  | "playbook_management";

export interface Conversation {
  conversation_id: string;
  title: string;
  selected_repository: string | null;
  selected_branch: string | null;
  git_provider: Provider | null;
  last_updated_at: string;
  created_at: string;
  status: ConversationStatus;
  runtime_status: RuntimeStatus | null;
  trigger?: ConversationTrigger;
  url: string | null;
  session_api_key: string | null;
  pr_number?: number[] | null;
}

export interface ResultSet<T> {
  results: T[];
  next_page_id: string | null;
}

export interface InputMetadata {
  name: string;
  description: string;
}

export interface Playbook {
  name: string;
  type: "repo" | "knowledge";
  content: string;
  triggers: string[];
}

export interface GetPlaybooksResponse {
  playbooks: Playbook[];
}

export interface CreatePlaybook {
  repo: string;
  git_provider?: Provider;
  title?: string;
}

export interface RepositoryPlaybook {
  name: string;
  path: string;
  created_at: string;
  git_provider: Provider;
}

export interface PlaybookContentResponse {
  content: string;
  path: string;
  git_provider: Provider;
  triggers: string[];
}

export type GetFilesResponse = string[];

export interface GetFileResponse {
  code: string;
}

export interface GitChange {
  path: string;
  status: GitChangeStatus;
}

export interface GitChangeDiff {
  original: string;
  modified: string;
}

export interface SuggestedTask {
  issue_number?: number;
  title: string;
  repo: string;
  task_type: string;
  git_provider: Provider;
}

export interface SuggestedTaskGroup {
  title: string;
  tasks: SuggestedTask[];
}
