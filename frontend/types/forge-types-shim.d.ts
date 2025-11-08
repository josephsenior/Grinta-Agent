import type { ConversationStatus as ProjectConversationStatus } from "#/types/conversation-status";
import type { RuntimeStatus as ProjectRuntimeStatus } from "#/types/runtime-status";

// Focused, minimal type declarations for `#/api/forge.types`.
// These are intentionally conservative: properties are optional and narrow
// where we know usage, but avoid `any`. Expand shapes only as needed.
declare module "#/api/forge.types" {
  // Basic conversation shape used across UI and tests
  export interface Conversation {
    conversation_id: string;
    id?: string;
    title: string;
    created_at?: string;
    updated_at?: string;
    // Some APIs/tests use `last_updated_at` instead of `updated_at`.
    last_updated_at: string;
    // payloads/messages and other fields exist but are typed as unknown to start
    participants?: unknown[] | null;
    metadata?: Record<string, unknown> | null;
    // Common runtime / git fields used across the UI (allow nulls because tests/mocks use null)
    selected_repository?: string | null;
    selected_branch?: string | null;
    // Restrict to the known provider literals (allow null in mocks)
    git_provider?: "github" | "gitlab" | "bitbucket" | "enterprise_sso" | null;
    // Use the project-defined ConversationStatus type to stay compatible
    status?: ProjectConversationStatus;
    runtime_status?: ProjectRuntimeStatus | null;
    session_api_key?: string | null;
    url?: string | null;
    pr_number?: number[] | string[] | string | null | undefined;
    // Some mocks include a 'trigger' key
    trigger?: string;
  }

  // Config response often contains small set of flags and strings
  export interface GetConfigResponse {
    // Narrow to the two expected values so callers that expect "saas"|"oss" accept it.
    APP_MODE?: "saas" | "oss" | undefined;
    FEATURE_FLAGS?: Record<string, boolean>;
    // Common config keys accessed in the frontend
    APP_SLUG?: string;
    GITHUB_CLIENT_ID?: string | null;
    AUTH_URL?: string | undefined;
    MAINTENANCE?: { startTime: string } | null;
    PROVIDERS_CONFIGURED?: ("github" | "gitlab" | "bitbucket" | "enterprise_sso")[] | undefined;
    // Required (may be null) so callers that pass this into setState accept it
    POSTHOG_CLIENT_KEY: string | null;
    // Allow additional keys; be conservative but permissive for config values
    [key: string]: any;
  }

  // Small ResultSet wrapper used by some endpoints
  export interface ResultSet<T = unknown> {
    // `results` is commonly present; keep as required to reduce consumer undefined checks.
    results: T[];
    items?: T[];
    total?: number;
    next_page_id?: string | null;
    [key: string]: unknown;
  }

  export interface CreateMicroagent {
    id?: string;
    name?: string;
    description?: string;
    // UI sometimes passes creation options
    repo?: string;
    git_provider?: "github" | "gitlab" | "bitbucket" | "enterprise_sso" | string;
    title?: string;
  }

  // Git change and status
  export type GitChangeStatus = "modified" | "added" | "deleted" | "renamed" | string;

  export interface GitChange {
    path?: string;
    status?: GitChangeStatus;
    diff?: string;
    lines_changed?: number;
  }

  export interface MicroagentContentResponse {
    id?: string;
    name?: string;
    content: string;
    triggers?: string[];
    path?: string;
    // tests sometimes include repository/git fields here
    git_provider?: "github" | "gitlab" | "bitbucket" | "enterprise_sso" | null;
    repo?: string | null;
  }

  export interface GetTrajectoryResponse {
    trajectory: unknown[] | null;
  }

  export interface GitChangeDiff {
    path?: string;
    diff?: string;
    // Consumers expect original/modified content in diffs
    original?: string;
    modified?: string;
  }

  // Accept either an array of path strings or objects with a `path` property.
  // This narrows the previous `any[]` while remaining compatible with most callers.
  export type FileEntry = string | { path: string; name?: string; type?: string };
  export type GetFilesResponse = FileEntry[];

  export interface GetFileResponse {
    path?: string;
    content?: string;
    // Some endpoints return a `code` property used as a string
    code: string;
  }

  export interface FileUploadSuccessResponse {
    uploaded_files: string[];
    skipped_files: Array<{ file?: string; reason?: string }>;
  }

  export interface GetMicroagentPromptResponse {
    // Callers return this directly as string; make required for now.
    prompt: string;
    metadata?: Record<string, unknown>;
  }

  export interface Feedback {
    subject?: string;
    body?: string;
    rating?: number;
    version?: string;
    email?: string;
    polarity?: string;
    permissions?: "private" | "public";
    trajectory?: unknown[];
    token?: string;
  }

  export interface FeedbackResponse {
    success?: boolean;
    id?: string;
    body: { message: string; feedback_id: string; password: string };
  }

  export interface RepositorySelection {
    id?: string;
    name?: string;
    // UI/tests use these fields directly in object literals
    selected_repository?: string | null;
    selected_branch?: string | null;
    git_provider?: "github" | "gitlab" | "bitbucket" | "enterprise_sso" | null;
  }

  export interface AuthenticateResponse {
    token?: string;
    expires_at?: string;
  }

  export interface PaginatedBranchesResponse {
    branches?: Branch[];
    total?: number;
  }

  export interface Branch {
    name?: string;
    last_commit?: string;
  }

  export interface GetMicroagentsResponse {
    microagents?: MicroagentContentResponse[];
  }

  export interface ResultSetItem {
    id?: string;
    [key: string]: unknown;
  }

  // Export a small stable stub value if consumers import it
  export const ForgeTypesStub: Readonly<{ version: string }>;
}
// Focused, minimal type declarations for `#/api/forge.types`.
// These are intentionally conservative: properties are optional and narrow
// where we know usage, but avoid `any`. Expand shapes only as needed.
import type { ConversationStatus as ProjectConversationStatus } from "#/types/conversation-status";
import type { RuntimeStatus as ProjectRuntimeStatus } from "#/types/runtime-status";

declare module "#/api/forge.types" {
  // Basic conversation shape used across UI and tests
  export interface Conversation {
    conversation_id: string;
    id?: string;
    title: string;
    created_at?: string;
    updated_at?: string;
    // Some APIs/tests use `last_updated_at` instead of `updated_at`.
    last_updated_at: string;
    // payloads/messages and other fields exist but are typed as unknown to start
    participants?: unknown[] | null;
    metadata?: Record<string, unknown> | null;
    // Common runtime / git fields used across the UI (allow nulls because tests/mocks use null)
    selected_repository?: string | null;
    selected_branch?: string | null;
    // Restrict to the known provider literals (allow null in mocks)
    git_provider?: "github" | "gitlab" | "bitbucket" | "enterprise_sso" | null;
    // Use the project-defined ConversationStatus type to stay compatible
    status?: ProjectConversationStatus | null;
    runtime_status?: ProjectRuntimeStatus | null;
    session_api_key?: string | null;
    url?: string | null;
    pr_number?: number[] | string[] | string | null | undefined;
    // Some mocks include a 'trigger' key
    trigger?: string;
  }

  // Config response often contains small set of flags and strings
  export interface GetConfigResponse {
    // Narrow to the two expected values so callers that expect "saas"|"oss" accept it.
    APP_MODE?: "saas" | "oss" | undefined;
    FEATURE_FLAGS?: Record<string, boolean>;
    // Common config keys accessed in the frontend
    APP_SLUG?: string;
    GITHUB_CLIENT_ID?: string | null;
    AUTH_URL?: string | undefined;
    MAINTENANCE?: { startTime: string } | null;
    PROVIDERS_CONFIGURED?: boolean | ("github" | "gitlab" | "bitbucket" | "enterprise_sso")[] | undefined;
    // Required (may be null) so callers that pass this into setState accept it
    POSTHOG_CLIENT_KEY: string | null;
    // Allow additional keys; be conservative but permissive for config values
    [key: string]: any;
  }

  // Small ResultSet wrapper used by some endpoints
  export interface ResultSet<T = unknown> {
    // `results` is commonly present; keep as required to reduce consumer undefined checks.
    results: T[];
    items?: T[];
    total?: number;
    next_page_id?: string | null;
    [key: string]: unknown;
  }

  export interface CreateMicroagent {
    id?: string;
    name?: string;
    description?: string;
    // UI sometimes passes creation options
    repo?: string;
    git_provider?: "github" | "gitlab" | "bitbucket" | "enterprise_sso" | string;
    title?: string;
  }

  // Git change and status
  export type GitChangeStatus = "modified" | "added" | "deleted" | "renamed" | string;

  export interface GitChange {
    path?: string;
    status?: GitChangeStatus;
    diff?: string;
    lines_changed?: number;
  }

  export interface MicroagentContentResponse {
    id?: string;
    name?: string;
    content: string;
    triggers?: string[];
    path?: string;
    // tests sometimes include repository/git fields here
    git_provider?: "github" | "gitlab" | "bitbucket" | "enterprise_sso" | null;
    repo?: string | null;
  }

  export interface GetTrajectoryResponse {
    trajectory: unknown[] | null;
  }

  export interface GitChangeDiff {
    path?: string;
    diff?: string;
    // Consumers expect original/modified content in diffs
    original?: string;
    modified?: string;
  }

  // Accept either an array of path strings or objects with a `path` property.
  export type FileEntry = string | { path: string; name?: string; type?: string };
  export type GetFilesResponse = FileEntry[];

  export interface GetFileResponse {
    path?: string;
    content?: string;
    // Some endpoints return a `code` property used as a string
    code: string;
  }

  export interface FileUploadSuccessResponse {
    uploaded_files: string[];
    skipped_files: Array<{ file?: string; reason?: string }>;
  }

  export interface GetMicroagentPromptResponse {
    // Callers return this directly as string; make required for now.
    prompt: string;
    metadata?: Record<string, unknown>;
  }

  export interface Feedback {
    subject?: string;
    body?: string;
    rating?: number;
    version?: string;
    email?: string;
    polarity?: string;
    permissions?: "private" | "public";
    trajectory?: unknown[];
    token?: string;
  }

  export interface FeedbackResponse {
    success?: boolean;
    id?: string;
    body: { message?: string; feedback_id?: string; password?: string };
  }

  export interface RepositorySelection {
    id?: string;
    name?: string;
    // UI/tests use these fields directly in object literals
    selected_repository?: string | null;
    selected_branch?: string | null;
    git_provider?: "github" | "gitlab" | "bitbucket" | "enterprise_sso" | null;
  }

  export interface AuthenticateResponse {
    token?: string;
    expires_at?: string;
  }

  export interface PaginatedBranchesResponse {
    branches?: Branch[];
    total?: number;
  }

  export interface Branch {
    name?: string;
    last_commit?: string;
  }

  export interface GetMicroagentsResponse {
    microagents?: MicroagentContentResponse[];
  }

  export interface ResultSetItem {
    id?: string;
    [key: string]: unknown;
  }

  // Export a small stable stub value if consumers import it
  export const ForgeTypesStub: Readonly<{ version: string }>;
}
// Focused, minimal type declarations for `#/api/forge.types`.
// These are intentionally conservative: properties are optional and narrow
// where we know usage, but avoid `any`. Expand shapes only as needed.
declare module "#/api/forge.types" {
  // Basic conversation shape used across UI and tests
  export interface Conversation {
    // Conversation ID is generally present in real responses and consumers
    // expect it; keep required.
    conversation_id: string;
    id?: string;
    title: string;
    created_at?: string;
    updated_at?: string;
    // Some APIs/tests use `last_updated_at` instead of `updated_at`.
    last_updated_at: string;
    // payloads/messages and other fields exist but are typed as unknown to start
    participants?: unknown[] | null;
    metadata?: Record<string, unknown> | null;
    // Common runtime / git fields used across the UI (allow nulls because tests/mocks use null)
    selected_repository?: string | null;
    selected_branch?: string | null;
    // Restrict to the known provider literals (allow null in mocks)
    git_provider?: "github" | "gitlab" | "bitbucket" | "enterprise_sso" | null;
    // Use a broad ConversationStatus so string values are accepted during this
    // tightening phase; refine later if helpful.
    status?: ConversationStatus;
    runtime_status?: string | null;
    session_api_key?: string | null;
    url?: string | null;
    pr_number?: number[] | string[] | string | null | undefined;
    // Some mocks include a 'trigger' key
    trigger?: string;
  }

  // Config response often contains small set of flags and strings
  export interface GetConfigResponse {
    // Narrow to the two expected values so callers that expect "saas"|"oss" accept it.
    APP_MODE?: "saas" | "oss" | undefined;
    FEATURE_FLAGS?: Record<string, boolean>;
    // Common config keys accessed in the frontend
    APP_SLUG?: string;
    GITHUB_CLIENT_ID?: string | null;
    AUTH_URL?: string | null;
    MAINTENANCE?: { startTime?: string } | null;
    PROVIDERS_CONFIGURED?: boolean;
    POSTHOG_CLIENT_KEY?: string | null;
    // Allow additional keys; be conservative but permissive for config values
    [key: string]: any;
  }

  // Small ResultSet wrapper used by some endpoints
  export interface ResultSet<T = unknown> {
    // `results` is commonly present; keep as required to reduce consumer undefined checks.
    results: T[];
    items?: T[];
    total?: number;
    next_page_id?: string | null;
    [key: string]: unknown;
  }

  export interface CreateMicroagent {
    id?: string;
    name?: string;
    description?: string;
    // UI sometimes passes creation options
    repo?: string;
    git_provider?: "github" | "gitlab" | "bitbucket" | "enterprise_sso" | string;
    title?: string;
  }

  // Git change and status
  export type GitChangeStatus = "modified" | "added" | "deleted" | "renamed" | string;

  export interface GitChange {
    path?: string;
    status?: GitChangeStatus;
    diff?: string;
    lines_changed?: number;
  }

  export interface Feedback {
    subject?: string;
    body?: string;
    rating?: number;
  }

  export interface FeedbackResponse {
    success?: boolean;
    id?: string;
  }

  export interface GitHubAccessTokenResponse {
    access_token?: string;
    scope?: string;
    token_type?: string;
  }

  export interface GetVSCodeUrlResponse {
    url?: string;
    // Some endpoints / mocks use `vscode_url` key
    vscode_url?: string;
  }

  export interface FileUploadSuccessResponse {
    uploaded_files: string[];
    skipped_files: Array<{ file?: string; reason?: string }>;
  }

  export interface GetMicroagentPromptResponse {
    // Callers return this directly as string; make required for now.
    prompt: string;
    metadata?: Record<string, unknown>;
  }

  export interface MicroagentContentResponse {
    id?: string;
    name?: string;
    content?: string;
    triggers?: string[];
    path?: string;
    // tests sometimes include repository/git fields here
    git_provider?: string | null;
    repo?: string | null;
  }

  export interface GetTrajectoryResponse {
    trajectory?: unknown[] | null;
  }

  export interface GitChangeDiff {
    path?: string;
    diff?: string;
    // Consumers expect original/modified content in diffs
    original?: string;
    modified?: string;
  }

  // Some endpoints return an array of file path strings, others return file objects;
  // accept either shape. Narrow to `string | { path: string }` for iterative tightening.
  export type FileEntry = string | { path: string; name?: string; type?: string };
  export type GetFilesResponse = FileEntry[];

  export interface GetFileResponse {
    path?: string;
    content?: string;
    // Some endpoints return a `code` property used as a string
    code: string;
  }

  export interface RepositorySelection {
    id?: string;
    name?: string;
    // UI/tests use these fields directly in object literals
    selected_repository?: string | null;
    selected_branch?: string | null;
    git_provider?: "github" | "gitlab" | "bitbucket" | "enterprise_sso" | null;
  }

  export interface Feedback {
    subject?: string;
    body?: string;
    rating?: number;
    version?: string;
  }

  export interface FeedbackResponse {
    success?: boolean;
    id?: string;
    body?: { message?: string; feedback_id?: string; password?: string };
  }

  // Broad conversation status type used in multiple components.
  export type ConversationStatus = "idle" | "running" | "failed" | "succeeded" | string;

  export interface AuthenticateResponse {
    token?: string;
    expires_at?: string;
  }

  export interface PaginatedBranchesResponse {
    branches?: Branch[];
    total?: number;
  }

  export interface Branch {
    name?: string;
    last_commit?: string;
  }

  export interface GetMicroagentsResponse {
    microagents?: MicroagentContentResponse[];
  }

  export interface ResultSetItem {
    id?: string;
    [key: string]: unknown;
  }

  // Export a small stable stub value if consumers import it
  export const ForgeTypesStub: Readonly<{ version: string }>;
}
