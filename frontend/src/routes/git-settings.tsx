import React from "react";
import { useTranslation } from "react-i18next";
import { useConfig } from "#/hooks/query/use-config";
import { useSettings } from "#/hooks/query/use-settings";
import { BrandButton } from "#/components/features/settings/brand-button";
import { useLogout } from "#/hooks/mutation/use-logout";
import { GitHubTokenInput } from "#/components/features/settings/git-settings/github-token-input";
import { GitLabTokenInput } from "#/components/features/settings/git-settings/gitlab-token-input";
import { BitbucketTokenInput } from "#/components/features/settings/git-settings/bitbucket-token-input";
import { ConfigureGitHubRepositoriesAnchor } from "#/components/features/settings/git-settings/configure-github-repositories-anchor";
import { InstallSlackAppAnchor } from "#/components/features/settings/git-settings/install-slack-app-anchor";
import { I18nKey } from "#/i18n/declaration";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";
import { GitSettingInputsSkeleton } from "#/components/features/settings/git-settings/github-settings-inputs-skeleton";
import { useAddGitProviders } from "#/hooks/mutation/use-add-git-providers";
import { useUserProviders } from "#/hooks/use-user-providers";
import { ProjectManagementIntegration } from "#/components/features/settings/project-management/project-management-integration";
import { cn } from "#/utils/utils";

type DirtyFlagKey =
  | "githubToken"
  | "gitlabToken"
  | "bitbucketToken"
  | "githubHost"
  | "gitlabHost"
  | "bitbucketHost";

type DirtyFlags = Record<DirtyFlagKey, boolean>;

const INITIAL_DIRTY_FLAGS: DirtyFlags = {
  githubToken: false,
  gitlabToken: false,
  bitbucketToken: false,
  githubHost: false,
  gitlabHost: false,
  bitbucketHost: false,
};

const DISCONNECT_BUTTON_FIELD = "disconnect-tokens-button";

interface ProviderFormValues {
  githubToken: string;
  gitlabToken: string;
  bitbucketToken: string;
  githubHost: string;
  gitlabHost: string;
  bitbucketHost: string;
}

function isDisconnectRequest(formData: FormData): boolean {
  return formData.get(DISCONNECT_BUTTON_FIELD) !== null;
}

function extractProviderFormValues(formData: FormData): ProviderFormValues {
  return {
    githubToken: formData.get("github-token-input")?.toString() ?? "",
    gitlabToken: formData.get("gitlab-token-input")?.toString() ?? "",
    bitbucketToken: formData.get("bitbucket-token-input")?.toString() ?? "",
    githubHost: formData.get("github-host-input")?.toString() ?? "",
    gitlabHost: formData.get("gitlab-host-input")?.toString() ?? "",
    bitbucketHost: formData.get("bitbucket-host-input")?.toString() ?? "",
  };
}

function buildProviderTokens(values: ProviderFormValues) {
  return {
    github: { token: values.githubToken, host: values.githubHost },
    gitlab: { token: values.gitlabToken, host: values.gitlabHost },
    bitbucket: { token: values.bitbucketToken, host: values.bitbucketHost },
    enterprise_sso: { token: "", host: "" },
  };
}

function GitSettingsScreen() {
  const {
    t,
    isLoading,
    formAction,
    providerInputs,
    showGithubIntegration,
    showSlackIntegration,
    showProjectManagement,
    config,
    formIsClean,
    isPending,
  } = useGitSettingsController();

  return (
    <form
      data-testid="git-settings-screen"
      action={formAction}
      className="flex flex-col h-full justify-between"
    >
      {!isLoading && (
        <div className="p-9 flex flex-col">
          <GitIntegrationsHeader
            showGithub={showGithubIntegration}
            showSlack={showSlackIntegration}
            config={config}
            t={t}
          />

          {showProjectManagement && (
            <div className="mt-6">
              <ProjectManagementIntegration />
            </div>
          )}

          <GitProviderInputs providerInputs={providerInputs} t={t} />
        </div>
      )}

      {isLoading && <GitSettingInputsSkeleton />}

      <GitSettingsFooter formIsClean={formIsClean} isPending={isPending} t={t} />
    </form>
  );
}

function GitIntegrationsHeader({
  showGithub,
  showSlack,
  config,
  t,
}: {
  showGithub: boolean;
  showSlack: boolean;
  config: ReturnType<typeof useConfig>["data"];
  t: ReturnType<typeof useTranslation>["t"];
}) {
  if (!showGithub && !showSlack) {
    return null;
  }

  return (
    <>
      {showGithub && config?.APP_SLUG && (
        <IntegrationSection
          title={t(I18nKey.SETTINGS$GITHUB)}
          content={<ConfigureGitHubRepositoriesAnchor slug={config.APP_SLUG} />}
        />
      )}

      {showSlack && (
        <IntegrationSection
          title={t(I18nKey.SETTINGS$SLACK)}
          content={<InstallSlackAppAnchor />}
          className="mt-6"
        />
      )}
    </>
  );
}

function IntegrationSection({
  title,
  content,
  className,
}: {
  title: string;
  content: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("pb-1 flex flex-col", className)}>
      <h3 className="text-xl font-medium text-white">{title}</h3>
      {content}
      <div className="w-1/2 border-b border-violet-500/20 mt-2" />
    </div>
  );
}

function GitProviderInputs({
  providerInputs,
  t,
}: {
  providerInputs: Array<{ key: string; element: React.ReactNode }>;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  if (providerInputs.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <h3 className="text-xl font-medium text-white">
          {t(I18nKey.SETTINGS$GIT_SETTINGS)}
        </h3>
        <span className="text-sm text-muted-foreground">
          {t(I18nKey.SETTINGS$GIT_SETTINGS_DESCRIPTION)}
        </span>
      </div>

      {providerInputs.map((input) => (
        <div key={input.key} className="w-full">
          {input.element}
        </div>
      ))}
    </div>
  );
}

function GitSettingsFooter({
  formIsClean,
  isPending,
  t,
}: {
  formIsClean: boolean;
  isPending: boolean;
  t: ReturnType<typeof useTranslation>["t"];
}) {
  return (
    <div className="border-t border-border bg-background-tertiary/40 px-9 py-6 flex justify-end">
      <BrandButton
        type="submit"
        variant="primary"
        isDisabled={formIsClean || isPending}
      >
        {isPending ? t(I18nKey.SETTINGS$SAVING) : t(I18nKey.SETTINGS$SAVE_CHANGES)}
      </BrandButton>
    </div>
  );
}

function useGitSettingsController() {
  const { t } = useTranslation();

  const { mutate: saveGitProviders, isPending } = useAddGitProviders();
  const { mutate: disconnectGitTokens } = useLogout();

  const { data: settings, isLoading } = useSettings();
  const { providers } = useUserProviders();

  const { data: config } = useConfig();

  const [dirtyFlags, setDirtyFlags] = React.useState<DirtyFlags>(
    INITIAL_DIRTY_FLAGS,
  );
  const markDirty = React.useCallback((key: DirtyFlagKey, value: boolean) => {
    setDirtyFlags((previous) =>
      previous[key] === value ? previous : { ...previous, [key]: value },
    );
  }, []);
  const resetDirtyFlags = React.useCallback(() => {
    setDirtyFlags(INITIAL_DIRTY_FLAGS);
  }, []);

  const existingGithubHost = settings?.PROVIDER_TOKENS_SET.github;
  const existingGitlabHost = settings?.PROVIDER_TOKENS_SET.gitlab;
  const existingBitbucketHost = settings?.PROVIDER_TOKENS_SET.bitbucket;

  const isSaas = config?.APP_MODE === "saas";
  const isGitHubTokenSet = providers.includes("github");
  const isGitLabTokenSet = providers.includes("gitlab");
  const isBitbucketTokenSet = providers.includes("bitbucket");

  const formAction = React.useCallback(
    async (formData: FormData) => {
      if (isDisconnectRequest(formData)) {
        disconnectGitTokens();
        return;
      }

      const values = extractProviderFormValues(formData);
      const providerTokens = buildProviderTokens(values);

      saveGitProviders(
        { providers: providerTokens },
        {
          onSuccess: () => {
            displaySuccessToast(t(I18nKey.SETTINGS$SAVED));
          },
          onError: (error) => {
            const errorMessage = retrieveAxiosErrorMessage(error);
            displayErrorToast(
              t(I18nKey.ERROR$GENERIC, { defaultValue: errorMessage }),
            );
          },
          onSettled: resetDirtyFlags,
        },
      );
    },
    [disconnectGitTokens, resetDirtyFlags, saveGitProviders, t],
  );

  const formIsClean = React.useMemo(
    () => !Object.values(dirtyFlags).some(Boolean),
    [dirtyFlags],
  );

  const providerInputs = React.useMemo(() => {
    if (isSaas) {
      return [] as Array<{ key: string; element: React.ReactNode }>;
    }

    return [
      {
        key: "github-token-input",
        element: (
          <GitHubTokenInput
            name="github-token-input"
            isGitHubTokenSet={isGitHubTokenSet}
            onChange={(value) => markDirty("githubToken", Boolean(value))}
            onGitHubHostChange={(value) =>
              markDirty("githubHost", Boolean(value))
            }
            githubHostSet={existingGithubHost}
          />
        ),
      },
      {
        key: "gitlab-token-input",
        element: (
          <GitLabTokenInput
            name="gitlab-token-input"
            isGitLabTokenSet={isGitLabTokenSet}
            onChange={(value) => markDirty("gitlabToken", Boolean(value))}
            onGitLabHostChange={(value) =>
              markDirty("gitlabHost", Boolean(value))
            }
            gitlabHostSet={existingGitlabHost}
          />
        ),
      },
      {
        key: "bitbucket-token-input",
        element: (
          <BitbucketTokenInput
            name="bitbucket-token-input"
            isBitbucketTokenSet={isBitbucketTokenSet}
            onChange={(value) => markDirty("bitbucketToken", Boolean(value))}
            onBitbucketHostChange={(value) =>
              markDirty("bitbucketHost", Boolean(value))
            }
            bitbucketHostSet={existingBitbucketHost}
          />
        ),
      },
    ];
  }, [
    isSaas,
    isGitHubTokenSet,
    isGitLabTokenSet,
    isBitbucketTokenSet,
    markDirty,
    existingGithubHost,
    existingGitlabHost,
    existingBitbucketHost,
  ]);

  const showGithubIntegration = Boolean(isSaas && config?.APP_SLUG);
  const showSlackIntegration = showGithubIntegration;
  const showProjectManagement = Boolean(
    config?.FEATURE_FLAGS?.ENABLE_JIRA ||
      config?.FEATURE_FLAGS?.ENABLE_JIRA_DC ||
      config?.FEATURE_FLAGS?.ENABLE_LINEAR,
  );

  return {
    t,
    isLoading,
    formAction,
    providerInputs,
    showGithubIntegration,
    showSlackIntegration,
    showProjectManagement,
    config,
    formIsClean,
    isPending,
  } as const;
}

export default GitSettingsScreen;
