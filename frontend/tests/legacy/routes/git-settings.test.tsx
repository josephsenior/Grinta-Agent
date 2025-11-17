import { render, screen, waitFor } from "@testing-library/react";
import { createRoutesStub } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import i18next from "i18next";
import { I18nextProvider } from "react-i18next";
import GitSettingsScreen from "#/routes/git-settings";
import Forge from "#/api/forge";
import { MOCK_DEFAULT_USER_SETTINGS } from "#/mocks/handlers";
import { GetConfigResponse } from "#/api/forge.types";
import * as ToastHandlers from "#/utils/custom-toast-handlers";
import { SecretsService } from "#/api/secrets-service";
import { I18nKey } from "#/i18n/declaration";

const VALID_OSS_CONFIG: GetConfigResponse = {
  APP_MODE: "oss",
  GITHUB_CLIENT_ID: "123",
  POSTHOG_CLIENT_KEY: "456",
  FEATURE_FLAGS: {
    ENABLE_BILLING: false,
    HIDE_LLM_SETTINGS: false,
    ENABLE_JIRA: false,
    ENABLE_JIRA_DC: false,
    ENABLE_LINEAR: false,
  },
};

const VALID_SAAS_CONFIG: GetConfigResponse = {
  APP_MODE: "saas",
  GITHUB_CLIENT_ID: "123",
  POSTHOG_CLIENT_KEY: "456",
  FEATURE_FLAGS: {
    ENABLE_BILLING: false,
    HIDE_LLM_SETTINGS: false,
    ENABLE_JIRA: false,
    ENABLE_JIRA_DC: false,
    ENABLE_LINEAR: false,
  },
};

const queryClient = new QueryClient();

const GitSettingsRouterStub = createRoutesStub([
  {
    Component: GitSettingsScreen,
    path: "/settings/integrations",
  },
]);

const renderGitSettingsScreen = () => {
  // Initialize i18next instance
  i18next.init({
    lng: "en",
    resources: {
      en: {
        translation: {
          GITHUB$TOKEN_HELP_TEXT: "Help text",
          GITHUB$TOKEN_LABEL: "GitHub Token",
          GITHUB$HOST_LABEL: "GitHub Host",
          GITLAB$TOKEN_LABEL: "GitLab Token",
          GITLAB$HOST_LABEL: "GitLab Host",
          BITBUCKET$TOKEN_LABEL: "Bitbucket Token",
          BITBUCKET$HOST_LABEL: "Bitbucket Host",
          SETTINGS$SAVE_CHANGES: "Save Changes",
          SETTINGS$SAVING: "Saving…",
        },
      },
    },
  });

  const { rerender, ...rest } = render(
    <GitSettingsRouterStub initialEntries={["/settings/integrations"]} />,
    {
      wrapper: ({ children }) => (
        <I18nextProvider i18n={i18next}>
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        </I18nextProvider>
      ),
    },
  );

  const rerenderGitSettingsScreen = () =>
    rerender(
      <I18nextProvider i18n={i18next}>
        <QueryClientProvider client={queryClient}>
          <GitSettingsRouterStub initialEntries={["/settings/integrations"]} />
        </QueryClientProvider>
      </I18nextProvider>,
    );

  return {
    ...rest,
    rerender: rerenderGitSettingsScreen,
  };
};

const disconnectMutation = vi.fn();
vi.mock("#/hooks/mutation/use-logout", () => ({
  useLogout: () => ({ mutate: disconnectMutation }),
}));

const addGitProvidersMutate = vi.fn(
  (
    variables: { providers: Record<string, { token: string; host: string }> },
    options?: {
      onSuccess?: (value: unknown) => void;
      onError?: (error: unknown) => void;
      onSettled?: () => void;
    },
  ) => {
    const result = SecretsService.addGitProvider(variables.providers);
    return Promise.resolve(result)
      .then((value) => {
        options?.onSuccess?.(value);
        return value;
      })
      .catch((error) => {
        options?.onError?.(error);
        throw error;
      })
      .finally(() => {
        options?.onSettled?.();
      });
  },
);

const addGitProvidersState = { isPending: false };

vi.mock("#/hooks/mutation/use-add-git-providers", () => ({
  useAddGitProviders: () => ({
    mutate: addGitProvidersMutate,
    isPending: addGitProvidersState.isPending,
  }),
}));

beforeEach(() => {
  // Since we don't recreate the query client on every test, we need to
  // reset the query client before each test to avoid state leaks
  // between tests.
  queryClient.invalidateQueries();
  disconnectMutation.mockReset();
  addGitProvidersMutate.mockReset();
  addGitProvidersState.isPending = false;
});

describe("Content", () => {
  it("should render", async () => {
    renderGitSettingsScreen();
    await screen.findByTestId("git-settings-screen");
  });

  it("should render the inputs if OSS mode", async () => {
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(VALID_OSS_CONFIG);

    const { rerender } = renderGitSettingsScreen();

    await screen.findByTestId("github-token-input");
    await screen.findByTestId("github-token-help-anchor");

    await screen.findByTestId("gitlab-token-input");
    await screen.findByTestId("gitlab-token-help-anchor");

    await screen.findByTestId("bitbucket-token-input");
    await screen.findByTestId("bitbucket-token-help-anchor");

    getConfigSpy.mockResolvedValue(VALID_SAAS_CONFIG);
    queryClient.invalidateQueries();
    rerender();

    await waitFor(() => {
      expect(
        screen.queryByTestId("github-token-input"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("github-token-help-anchor"),
      ).not.toBeInTheDocument();

      expect(
        screen.queryByTestId("gitlab-token-input"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("gitlab-token-help-anchor"),
      ).not.toBeInTheDocument();

      expect(
        screen.queryByTestId("bitbucket-token-input"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("bitbucket-token-help-anchor"),
      ).not.toBeInTheDocument();
    });
  });

  it("should set '<hidden>' placeholder and indicator if the GitHub token is set", async () => {
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");

    getConfigSpy.mockResolvedValue(VALID_OSS_CONFIG);
    getSettingsSpy.mockResolvedValue({
      ...MOCK_DEFAULT_USER_SETTINGS,
    });

    const { rerender } = renderGitSettingsScreen();

    await waitFor(() => {
      const githubInput = screen.getByTestId("github-token-input");
      expect(githubInput).toHaveProperty("placeholder", "");
      expect(
        screen.queryByTestId("gh-set-token-indicator"),
      ).not.toBeInTheDocument();

      const gitlabInput = screen.getByTestId("gitlab-token-input");
      expect(gitlabInput).toHaveProperty("placeholder", "");
      expect(
        screen.queryByTestId("gl-set-token-indicator"),
      ).not.toBeInTheDocument();
    });

    getSettingsSpy.mockResolvedValue({
      ...MOCK_DEFAULT_USER_SETTINGS,
      provider_tokens_set: {
        github: null,
        gitlab: null,
      },
    });
    queryClient.invalidateQueries();

    rerender();

    await waitFor(() => {
      const githubInput = screen.getByTestId("github-token-input");
      expect(githubInput).toHaveProperty("placeholder", "<hidden>");
      expect(
        screen.queryByTestId("gh-set-token-indicator"),
      ).toBeInTheDocument();

      const gitlabInput = screen.getByTestId("gitlab-token-input");
      expect(gitlabInput).toHaveProperty("placeholder", "<hidden>");
      expect(
        screen.queryByTestId("gl-set-token-indicator"),
      ).toBeInTheDocument();
    });

    getSettingsSpy.mockResolvedValue({
      ...MOCK_DEFAULT_USER_SETTINGS,
      provider_tokens_set: {
        gitlab: null,
      },
    });
    queryClient.invalidateQueries();

    rerender();

    await waitFor(() => {
      const githubInput = screen.getByTestId("github-token-input");
      expect(githubInput).toHaveProperty("placeholder", "");
      expect(
        screen.queryByTestId("gh-set-token-indicator"),
      ).not.toBeInTheDocument();

      const gitlabInput = screen.getByTestId("gitlab-token-input");
      expect(gitlabInput).toHaveProperty("placeholder", "<hidden>");
      expect(
        screen.queryByTestId("gl-set-token-indicator"),
      ).toBeInTheDocument();
    });
  });

  it("should render the 'Configure GitHub Repositories' button if SaaS mode and app slug exists", async () => {
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(VALID_OSS_CONFIG);

    const { rerender } = renderGitSettingsScreen();

    let button = screen.queryByTestId("configure-github-repositories-button");
    expect(button).not.toBeInTheDocument();

    expect(screen.getByTestId("submit-button")).toBeInTheDocument();
    expect(
      screen.queryByTestId("disconnect-tokens-button"),
    ).not.toBeInTheDocument();

    getConfigSpy.mockResolvedValue(VALID_SAAS_CONFIG);
    queryClient.invalidateQueries();
    rerender();

    await waitFor(() => {
      // wait until queries are resolved
      expect(queryClient.isFetching()).toBe(0);
      button = screen.queryByTestId("configure-github-repositories-button");
      expect(button).not.toBeInTheDocument();
    });

    getConfigSpy.mockResolvedValue({
      ...VALID_SAAS_CONFIG,
      APP_SLUG: "test-slug",
    });
    queryClient.invalidateQueries();
    rerender();

    await waitFor(() => {
      button = screen.getByTestId("configure-github-repositories-button");
      expect(button).toBeInTheDocument();
      expect(screen.getByTestId("submit-button")).toBeDisabled();
    });
  });

  it("should render project management integrations when feature flags enabled", async () => {
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue({
      ...VALID_OSS_CONFIG,
      FEATURE_FLAGS: {
        ...VALID_OSS_CONFIG.FEATURE_FLAGS,
        ENABLE_JIRA: true,
        ENABLE_JIRA_DC: true,
        ENABLE_LINEAR: true,
      },
    });

    renderGitSettingsScreen();

    expect(await screen.findByTestId("jira-integration-row")).toBeInTheDocument();
    expect(
      screen.getByTestId("jira-dc-integration-row"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("linear-integration-row")).toBeInTheDocument();
  });
});

describe("Form submission", () => {
  it("should save the GitHub token", async () => {
    const saveProvidersSpy = vi.spyOn(SecretsService, "addGitProvider");
    saveProvidersSpy.mockImplementation(() => Promise.resolve(true));
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(VALID_OSS_CONFIG);

    renderGitSettingsScreen();

    const githubInput = await screen.findByTestId("github-token-input");
    const submit = await screen.findByTestId("submit-button");

    await userEvent.type(githubInput, "test-token");
    await userEvent.click(submit);

    expect(saveProvidersSpy).toHaveBeenCalledWith({
      github: { token: "test-token", host: "" },
      gitlab: { token: "", host: "" },
      bitbucket: { token: "", host: "" },
      enterprise_sso: { token: "", host: "" },
    });
  });

  it("should save GitLab tokens", async () => {
    const saveProvidersSpy = vi.spyOn(SecretsService, "addGitProvider");
    saveProvidersSpy.mockImplementation(() => Promise.resolve(true));
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(VALID_OSS_CONFIG);

    renderGitSettingsScreen();

    const gitlabInput = await screen.findByTestId("gitlab-token-input");
    const submit = await screen.findByTestId("submit-button");

    await userEvent.type(gitlabInput, "test-token");
    await userEvent.click(submit);

    expect(saveProvidersSpy).toHaveBeenCalledWith({
      github: { token: "", host: "" },
      gitlab: { token: "test-token", host: "" },
      bitbucket: { token: "", host: "" },
      enterprise_sso: { token: "", host: "" },
    });
  });

  it("should save the Bitbucket token", async () => {
    const saveProvidersSpy = vi.spyOn(SecretsService, "addGitProvider");
    saveProvidersSpy.mockImplementation(() => Promise.resolve(true));
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(VALID_OSS_CONFIG);

    renderGitSettingsScreen();

    const bitbucketInput = await screen.findByTestId("bitbucket-token-input");
    const submit = await screen.findByTestId("submit-button");

    await userEvent.type(bitbucketInput, "test-token");
    await userEvent.click(submit);

    expect(saveProvidersSpy).toHaveBeenCalledWith({
      github: { token: "", host: "" },
      gitlab: { token: "", host: "" },
      bitbucket: { token: "test-token", host: "" },
      enterprise_sso: { token: "", host: "" },
    });
  });

  it("should disable the button if there is no input", async () => {
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(VALID_OSS_CONFIG);

    renderGitSettingsScreen();

    const submit = await screen.findByTestId("submit-button");
    expect(submit).toBeDisabled();

    const githubInput = await screen.findByTestId("github-token-input");
    await userEvent.type(githubInput, "test-token");

    expect(submit).not.toBeDisabled();

    await userEvent.clear(githubInput);
    expect(submit).toBeDisabled();

    const gitlabInput = await screen.findByTestId("gitlab-token-input");
    await userEvent.type(gitlabInput, "test-token");

    expect(submit).not.toBeDisabled();

    await userEvent.clear(gitlabInput);
    expect(submit).toBeDisabled();
  });

  it("should mark host inputs as dirty when edited", async () => {
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getConfigSpy.mockResolvedValue(VALID_OSS_CONFIG);
    getSettingsSpy.mockResolvedValue(MOCK_DEFAULT_USER_SETTINGS);

    renderGitSettingsScreen();

    const submit = await screen.findByTestId("submit-button");
    expect(submit).toBeDisabled();

    const githubHostInput = await screen.findByTestId("github-host-input");
    await userEvent.type(githubHostInput, "enterprise.github.com");
    expect(githubHostInput).toHaveValue("enterprise.github.com");
    expect(submit).not.toBeDisabled();

    await userEvent.clear(githubHostInput);
    expect(githubHostInput).toHaveValue("");
    expect(submit).toBeDisabled();

    const gitlabHostInput = await screen.findByTestId("gitlab-host-input");
    await userEvent.type(gitlabHostInput, "gitlab.enterprise.com");
    expect(gitlabHostInput).toHaveValue("gitlab.enterprise.com");
    expect(submit).not.toBeDisabled();

    await userEvent.clear(gitlabHostInput);
    expect(gitlabHostInput).toHaveValue("");
    expect(submit).toBeDisabled();

    const bitbucketHostInput = await screen.findByTestId(
      "bitbucket-host-input",
    );
    await userEvent.type(bitbucketHostInput, "bitbucket.enterprise.com");
    expect(bitbucketHostInput).toHaveValue("bitbucket.enterprise.com");
    expect(submit).not.toBeDisabled();

    await userEvent.clear(bitbucketHostInput);
    expect(bitbucketHostInput).toHaveValue("");
    expect(submit).toBeDisabled();
  });

  it("shows saving state while a mutation is pending", async () => {
    addGitProvidersState.isPending = true;

    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(VALID_OSS_CONFIG);

    renderGitSettingsScreen();

    const submit = await screen.findByTestId("submit-button");
    expect(submit).toBeDisabled();
    expect(submit).toHaveTextContent(I18nKey.SETTINGS$SAVING);
  });

  it("disconnects git tokens when the disconnect field is present", async () => {
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getConfigSpy.mockResolvedValue(VALID_OSS_CONFIG);
    getSettingsSpy.mockResolvedValue(MOCK_DEFAULT_USER_SETTINGS);
    const saveProvidersSpy = vi.spyOn(SecretsService, "addGitProvider");
    saveProvidersSpy.mockResolvedValue(true);

    renderGitSettingsScreen();

    const form = await screen.findByTestId("git-settings-screen");
    const submit = await screen.findByTestId("submit-button");

    const hiddenInput = document.createElement("input");
    hiddenInput.type = "hidden";
    hiddenInput.name = "disconnect-tokens-button";
    hiddenInput.value = "1";
    form.appendChild(hiddenInput);

    const githubInput = await screen.findByTestId("github-token-input");
    await userEvent.type(githubInput, "x");

    await userEvent.click(submit);

    expect(disconnectMutation).toHaveBeenCalledTimes(1);
    expect(saveProvidersSpy).not.toHaveBeenCalled();
  });

  // flaky test
  it.skip("should disable the button when submitting changes", async () => {
    const saveSettingsSpy = vi.spyOn(SecretsService, "addGitProvider");
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(VALID_OSS_CONFIG);

    renderGitSettingsScreen();

    const submit = await screen.findByTestId("submit-button");
    expect(submit).toBeDisabled();

    const githubInput = await screen.findByTestId("github-token-input");
    await userEvent.type(githubInput, "test-token");
    expect(submit).not.toBeDisabled();

    // submit the form
    await userEvent.click(submit);
    expect(saveSettingsSpy).toHaveBeenCalled();

    expect(submit).toHaveTextContent("Saving...");
    expect(submit).toBeDisabled();

    await waitFor(() => expect(submit).toHaveTextContent("Save"));
  });

  it("should disable the button after submitting changes", async () => {
    const saveProvidersSpy = vi.spyOn(SecretsService, "addGitProvider");
    const getConfigSpy = vi.spyOn(Forge, "getConfig");
    getConfigSpy.mockResolvedValue(VALID_OSS_CONFIG);

    renderGitSettingsScreen();
    await screen.findByTestId("git-settings-screen");

    const submit = await screen.findByTestId("submit-button");
    expect(submit).toBeDisabled();

    const githubInput = await screen.findByTestId("github-token-input");
    await userEvent.type(githubInput, "test-token");
    expect(submit).not.toBeDisabled();

    // submit the form
    await userEvent.click(submit);
    expect(saveProvidersSpy).toHaveBeenCalled();
    expect(submit).toBeDisabled();

    const gitlabInput = await screen.findByTestId("gitlab-token-input");
    await userEvent.type(gitlabInput, "test-token");
    expect(gitlabInput).toHaveValue("test-token");
    expect(submit).not.toBeDisabled();

    // submit the form
    await userEvent.click(submit);
    expect(saveProvidersSpy).toHaveBeenCalled();

    await waitFor(() => expect(submit).toBeDisabled());
  });
});

describe("Status toasts", () => {
  it("should call displaySuccessToast when the settings are saved", async () => {
    const saveProvidersSpy = vi.spyOn(SecretsService, "addGitProvider");
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getSettingsSpy.mockResolvedValue(MOCK_DEFAULT_USER_SETTINGS);

    const displaySuccessToastSpy = vi.spyOn(
      ToastHandlers,
      "displaySuccessToast",
    );

    renderGitSettingsScreen();

    // Toggle setting to change
    const githubInput = await screen.findByTestId("github-token-input");
    await userEvent.type(githubInput, "test-token");

    const submit = await screen.findByTestId("submit-button");
    await userEvent.click(submit);

    expect(saveProvidersSpy).toHaveBeenCalled();
    await waitFor(() => expect(displaySuccessToastSpy).toHaveBeenCalled());
  });

  it("should call displayErrorToast when the settings fail to save", async () => {
    const saveProvidersSpy = vi.spyOn(SecretsService, "addGitProvider");
    const getSettingsSpy = vi.spyOn(Forge, "getSettings");
    getSettingsSpy.mockResolvedValue(MOCK_DEFAULT_USER_SETTINGS);

    const displayErrorToastSpy = vi.spyOn(ToastHandlers, "displayErrorToast");

    saveProvidersSpy.mockRejectedValue(new Error("Failed to save settings"));

    renderGitSettingsScreen();

    // Toggle setting to change
    const gitlabInput = await screen.findByTestId("gitlab-token-input");
    await userEvent.type(gitlabInput, "test-token");

    const submit = await screen.findByTestId("submit-button");
    await userEvent.click(submit);

    expect(saveProvidersSpy).toHaveBeenCalled();
    expect(displayErrorToastSpy).toHaveBeenCalled();
  });
});
