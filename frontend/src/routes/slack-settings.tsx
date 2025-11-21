/**
 * Slack Integration Settings Page
 */
/* eslint-disable i18next/no-literal-string, react/no-unescaped-entities */

import React from "react";
import { ExternalLink, Trash2, CheckCircle, XCircle, Plus } from "lucide-react";
import { BrandButton } from "#/components/features/settings/brand-button";
import { Card } from "#/components/ui/card";
import {
  useSlackWorkspaces,
  useInstallSlackWorkspace,
  useUninstallSlackWorkspace,
} from "#/hooks/query/use-slack";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { logger } from "#/utils/logger";

function SlackSettingsScreen() {
  const { data: workspaces, isLoading } = useSlackWorkspaces();
  const installMutation = useInstallSlackWorkspace();
  const uninstallMutation = useUninstallSlackWorkspace();

  const handleInstall = async () => {
    try {
      const response = await installMutation.mutateAsync({
        redirect_url: window.location.href,
      });

      // Redirect to Slack OAuth
      if (response.url) {
        window.location.href = response.url;
      }
    } catch (error) {
      logger.error("Failed to start Slack installation:", error);
    }
  };

  const handleUninstall = async (teamId: string) => {
    // eslint-disable-next-line no-alert
    const shouldUninstall = window.confirm(
      "Are you sure you want to uninstall this Slack workspace?",
    );
    if (!shouldUninstall) {
      return;
    }
    await uninstallMutation.mutateAsync(teamId);
  };

  const renderWorkspaceSection = () => {
    if (isLoading) {
      return (
        <div className="flex justify-center py-8">
          <LoadingSpinner />
        </div>
      );
    }

    if (workspaces && workspaces.length > 0) {
      return (
        <div className="grid gap-4">
          {workspaces.map((workspace) => (
            <Card
              key={workspace.team_id}
              className="p-4 bg-black/60 border-white/10 hover:border-white/20 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="flex-shrink-0 w-10 h-10 rounded bg-white/5 flex items-center justify-center">
                    <span className="text-2xl">💬</span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">
                      {workspace.team_name}
                    </h3>
                    <p className="text-sm text-foreground-secondary">
                      Team ID: {workspace.team_id}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 text-sm text-foreground-secondary">
                    <CheckCircle className="w-4 h-4" />
                    <span>Active</span>
                  </div>

                  <BrandButton
                    variant="danger"
                    type="button"
                    onClick={() => handleUninstall(workspace.team_id)}
                    isDisabled={uninstallMutation.isPending}
                    testId={`uninstall-slack-${workspace.team_id}`}
                  >
                    <Trash2 className="w-4 h-4 mr-1" />
                    Uninstall
                  </BrandButton>
                </div>
              </div>
            </Card>
          ))}
        </div>
      );
    }

    return (
      <Card className="p-6 bg-black/60 border-white/10 rounded-2xl text-center">
        <div className="flex flex-col items-center gap-3">
          <XCircle className="w-12 h-12 text-foreground-secondary" />
          <p className="text-foreground-secondary">
            No Slack workspaces installed yet
          </p>
          <p className="text-sm text-foreground-secondary">
            Click "Add to Slack" above to get started
          </p>
        </div>
      </Card>
    );
  };

  return (
    <div className="p-6 sm:p-8 lg:p-10 flex flex-col gap-6 lg:gap-8">
      <div className="mx-auto max-w-6xl w-full space-y-6 lg:space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between w-full">
          <div className="w-full">
            <h1 className="text-2xl font-semibold text-foreground w-full">
              Slack Integration
            </h1>
            <p className="text-foreground-secondary mt-1 w-full">
              Connect your Slack workspace to use Forge from Slack threads
            </p>
          </div>

          <BrandButton
            variant="primary"
            type="button"
            onClick={handleInstall}
            isDisabled={installMutation.isPending}
            testId="install-slack-button"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add to Slack
          </BrandButton>
        </div>

        {/* How it works */}
        <Card className="p-6 bg-black/60 border-white/10 rounded-2xl">
          <h2 className="text-lg font-semibold text-foreground mb-4">
            How Slack Integration Works
          </h2>
          <div className="space-y-3 text-sm text-foreground-secondary">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-white text-black flex items-center justify-center text-xs font-bold">
                1
              </div>
              <div>
                <p className="font-medium text-foreground">
                  Install the Forge app to your Slack workspace
                </p>
                <p>Click "Add to Slack" above to start the OAuth flow</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-white text-black flex items-center justify-center text-xs font-bold">
                2
              </div>
              <div>
                <p className="font-medium text-foreground">
                  Mention @Forge in any channel or thread
                </p>
                <p>The bot will start a new Forge conversation</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-white text-black flex items-center justify-center text-xs font-bold">
                3
              </div>
              <div>
                <p className="font-medium text-foreground">
                  Get real-time updates in the Slack thread
                </p>
                <p>
                  The agent will post its thoughts, commands, and results
                  directly to Slack
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-white text-black flex items-center justify-center text-xs font-bold">
                4
              </div>
              <div>
                <p className="font-medium text-foreground">
                  Reply in the thread to continue the conversation
                </p>
                <p>No need to @mention again - just type your message!</p>
              </div>
            </div>
          </div>
        </Card>

        {/* Installed Workspaces */}
        <div>
          <h2 className="text-lg font-semibold text-foreground mb-4">
            Installed Workspaces
          </h2>
          {renderWorkspaceSection()}
        </div>

        {/* Help & Documentation */}
        <Card className="p-6 bg-black/60 border-white/10 rounded-2xl">
          <h3 className="text-sm font-semibold text-foreground mb-3">
            Setup Instructions
          </h3>
          <div className="space-y-3 text-sm text-foreground-secondary">
            <p>
              To enable Slack integration, administrators need to configure the
              following environment variables on the server:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>
                <code className="text-xs bg-background px-1 py-0.5 rounded">
                  SLACK_CLIENT_ID
                </code>
              </li>
              <li>
                <code className="text-xs bg-background px-1 py-0.5 rounded">
                  SLACK_CLIENT_SECRET
                </code>
              </li>
              <li>
                <code className="text-xs bg-background px-1 py-0.5 rounded">
                  SLACK_SIGNING_SECRET
                </code>
              </li>
            </ul>
            <p className="mt-3">
              Get these credentials by creating a Slack app:
            </p>
            <a
              href="https://api.slack.com/apps"
              target="_blank"
              rel="noopener noreferrer"
              className="text-foreground hover:text-foreground-secondary underline flex items-center gap-1"
            >
              Create a Slack app <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </Card>

        {/* Features */}
        <Card className="p-6 bg-black/60 border-white/10 rounded-2xl">
          <h3 className="text-sm font-semibold text-foreground mb-3">
            Features
          </h3>
          <ul className="space-y-2 text-sm text-foreground-secondary">
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-foreground-tertiary flex-shrink-0 mt-0.5" />
              <span>Start conversations with @Forge mentions</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-foreground-tertiary flex-shrink-0 mt-0.5" />
              <span>
                Continue conversations by replying in threads (no @mention
                needed)
              </span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-foreground-tertiary flex-shrink-0 mt-0.5" />
              <span>Real-time agent updates posted to Slack</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-foreground-tertiary flex-shrink-0 mt-0.5" />
              <span>View agent thoughts, commands, and results in Slack</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-foreground-tertiary flex-shrink-0 mt-0.5" />
              <span>Seamlessly switch between Slack and web UI</span>
            </li>
          </ul>
        </Card>
      </div>
    </div>
  );
}

export default SlackSettingsScreen;
