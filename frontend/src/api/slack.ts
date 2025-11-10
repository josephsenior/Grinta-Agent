/**
 * API client for Slack integration
 */

export interface SlackWorkspace {
  team_id: string;
  team_name: string;
}

export interface SlackInstallResponse {
  url: string;
}

/**
 * List all installed Slack workspaces for the current user
 */
export async function listSlackWorkspaces(): Promise<SlackWorkspace[]> {
  const response = await fetch("/api/slack/workspaces");

  if (!response.ok) {
    throw new Error(`Failed to list Slack workspaces: ${response.statusText}`);
  }

  const data = await response.json();
  return data.workspaces || [];
}

/**
 * Get Slack installation URL
 */
export async function getSlackInstallUrl(params?: {
  redirect_url?: string;
}): Promise<SlackInstallResponse> {
  const searchParams = new URLSearchParams();

  if (params?.redirect_url) {
    searchParams.append("redirect_url", params.redirect_url);
  }

  const url = `/api/slack/install?${searchParams.toString()}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to get Slack install URL: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Uninstall a Slack workspace
 */
export async function uninstallSlackWorkspace(teamId: string): Promise<void> {
  const response = await fetch(`/api/slack/workspaces/${teamId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new Error(
      `Failed to uninstall Slack workspace: ${response.statusText}`,
    );
  }
}
