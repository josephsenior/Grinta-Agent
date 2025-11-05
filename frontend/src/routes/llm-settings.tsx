import React from "react";
import { useTranslation } from "react-i18next";
import { AxiosError } from "axios";
import { ModelSelector } from "#/components/shared/modals/settings/model-selector";
import { organizeModelsAndProviders } from "#/utils/organize-models-and-providers";
import { useAIConfigOptions } from "#/hooks/query/use-ai-config-options";
import { useSettings } from "#/hooks/query/use-settings";
import { hasAdvancedSettingsSet } from "#/utils/has-advanced-settings-set";
import { useSaveSettings } from "#/hooks/mutation/use-save-settings";
import { SettingsSwitch } from "#/components/features/settings/settings-switch";
import { TooltipButton } from "#/components/shared/buttons/tooltip-button";
import QuestionCircleIcon from "#/icons/question-circle.svg?react";
import { I18nKey } from "#/i18n/declaration";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { HelpLink } from "#/components/features/settings/help-link";
import { BrandButton } from "#/components/features/settings/brand-button";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { useToast } from "#/components/shared/notifications/toast";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";
import { SettingsDropdownInput } from "#/components/features/settings/settings-dropdown-input";
import { useConfig } from "#/hooks/query/use-config";
import { isCustomModel } from "#/utils/is-custom-model";
import { LlmSettingsInputsSkeleton } from "#/components/features/settings/llm-settings/llm-settings-inputs-skeleton";
import { KeyStatusIcon } from "#/components/features/settings/key-status-icon";
import { DEFAULT_SETTINGS } from "#/services/settings";
import { getProviderId } from "#/utils/map-provider";
import { DEFAULT_OPENHANDS_MODEL } from "#/utils/verified-models";
import { AdvancedLLMConfig } from "#/components/features/settings/advanced-llm-config";
import { SettingsErrorBoundary } from "#/components/features/settings/settings-error-boundary";

function LlmSettingsScreen() {
  const { t } = useTranslation();
  const { addToast } = useToast();

  const { mutate: saveSettings, isPending } = useSaveSettings();

  const { data: resources } = useAIConfigOptions();
  const { data: settings, isLoading, isFetching } = useSettings();
  const { data: config } = useConfig();

  const [view, setView] = React.useState<"basic" | "advanced">("basic");
  const [userToggledView, setUserToggledView] = React.useState(false);

  const [dirtyInputs, setDirtyInputs] = React.useState({
    model: false,
    apiKey: false,
    searchApiKey: false,
    baseUrl: false,
    agent: false,
    confirmationMode: false,
    enableDefaultCondenser: false,
    securityAnalyzer: false,
    condenserMaxSize: false,
  });

  // Track the currently selected model to show help text
  const [currentSelectedModel, setCurrentSelectedModel] = React.useState<
    string | null
  >(null);

  // Track confirmation mode state to control security analyzer visibility
  const [confirmationModeEnabled, setConfirmationModeEnabled] = React.useState(
    settings?.CONFIRMATION_MODE ?? DEFAULT_SETTINGS.CONFIRMATION_MODE,
  );

  // Track selected security analyzer for form submission
  const [selectedSecurityAnalyzer, setSelectedSecurityAnalyzer] =
    React.useState(
      settings?.SECURITY_ANALYZER === null
        ? "none"
        : (settings?.SECURITY_ANALYZER ?? DEFAULT_SETTINGS.SECURITY_ANALYZER),
    );

  // Track advanced config values for form submission
  const [advancedConfig, setAdvancedConfig] = React.useState<Record<string, any>>({});

  const modelsAndProviders = organizeModelsAndProviders(
    resources?.models || [],
  );

  // Initialize and sync advanced config from settings
  // Update whenever settings change (e.g., after successful save and refetch)
  // Note: Autonomy settings are managed in the chat UI, not here
  React.useEffect(() => {
    if (settings) {
      setAdvancedConfig((prev) => {
        const newConfig = {
          LLM_TEMPERATURE: settings.LLM_TEMPERATURE,
          LLM_TOP_P: settings.LLM_TOP_P,
          LLM_MAX_OUTPUT_TOKENS: settings.LLM_MAX_OUTPUT_TOKENS,
          LLM_TIMEOUT: settings.LLM_TIMEOUT,
          LLM_NUM_RETRIES: settings.LLM_NUM_RETRIES,
          LLM_CACHING_PROMPT: settings.LLM_CACHING_PROMPT,
          LLM_DISABLE_VISION: settings.LLM_DISABLE_VISION,
          LLM_CUSTOM_LLM_PROVIDER: settings.LLM_CUSTOM_LLM_PROVIDER,
        };
        
        // Merge with previous state to preserve any user changes made but not yet saved
        return { ...prev, ...newConfig };
      });
    }
  }, [
    settings?.LLM_TEMPERATURE,
    settings?.LLM_TOP_P,
    settings?.LLM_MAX_OUTPUT_TOKENS,
    settings?.LLM_TIMEOUT,
    settings?.LLM_NUM_RETRIES,
    settings?.LLM_CACHING_PROMPT,
    settings?.LLM_DISABLE_VISION,
    settings?.LLM_CUSTOM_LLM_PROVIDER,
  ]);

  React.useEffect(() => {
    // Don't auto-switch if user manually toggled the view
    if (userToggledView) {
      console.log('[LLM Settings] Skipping auto-switch - user manually toggled view');
      return;
    }

    const determineWhetherToToggleAdvancedSettings = () => {
      if (resources && settings) {
        return (
          isCustomModel(resources.models, settings.LLM_MODEL) ||
          hasAdvancedSettingsSet({
            ...settings,
          })
        );
      }

      return false;
    };

    const userSettingsIsAdvanced = determineWhetherToToggleAdvancedSettings();

    if (userSettingsIsAdvanced) {
      console.log('[LLM Settings] Auto-switching to advanced view');
      setView("advanced");
    } else {
      console.log('[LLM Settings] Auto-switching to basic view');
      setView("basic");
    }
  }, [settings, resources, userToggledView]);

  // Initialize currentSelectedModel with the current settings
  React.useEffect(() => {
    if (settings?.LLM_MODEL) {
      setCurrentSelectedModel(settings.LLM_MODEL);
    }
  }, [settings?.LLM_MODEL]);

  // Update confirmation mode state when settings change
  React.useEffect(() => {
    if (settings?.CONFIRMATION_MODE !== undefined) {
      setConfirmationModeEnabled(settings.CONFIRMATION_MODE);
    }
  }, [settings?.CONFIRMATION_MODE]);

  // Update selected security analyzer state when settings change
  React.useEffect(() => {
    if (settings?.SECURITY_ANALYZER !== undefined) {
      setSelectedSecurityAnalyzer(settings.SECURITY_ANALYZER || "none");
    }
  }, [settings?.SECURITY_ANALYZER]);

  const handleSuccessfulMutation = () => {
    console.log('[LLM Settings] Settings saved successfully!');
    addToast({
      type: "success",
      title: "Settings saved successfully! ✅",
      description: "Your configuration has been updated and saved.",
      duration: 5000,
    });
    setDirtyInputs({
      model: false,
      apiKey: false,
      searchApiKey: false,
      baseUrl: false,
      agent: false,
      confirmationMode: false,
      enableDefaultCondenser: false,
      securityAnalyzer: false,
      condenserMaxSize: false,
    });
    // Don't reset userToggledView - keep the user's choice persistent
    // setUserToggledView(false);
    // Don't reset advancedConfig - it will be updated from the refetched settings
  };

  const handleErrorMutation = (error: AxiosError) => {
    const errorMessage = retrieveAxiosErrorMessage(error);
    displayErrorToast(t(I18nKey.ERROR$GENERIC, { defaultValue: errorMessage }));
  };

  const basicFormAction = (formData: FormData) => {
    const providerDisplay = formData.get("llm-provider-input")?.toString();
    const provider = providerDisplay
      ? getProviderId(providerDisplay)
      : undefined;
    const model = formData.get("llm-model-input")?.toString();
    const apiKey = formData.get("llm-api-key-input")?.toString();
    const searchApiKey = formData.get("search-api-key-input")?.toString();
    const confirmationMode =
      formData.get("enable-confirmation-mode-switch")?.toString() === "on";
    const securityAnalyzer = formData
      .get("security-analyzer-input")
      ?.toString();

    const fullLlmModel = provider && model && `${provider}/${model}`;

    saveSettings(
      {
        LLM_MODEL: fullLlmModel,
        llm_api_key: apiKey || null,
        SEARCH_API_KEY: searchApiKey || "",
        CONFIRMATION_MODE: confirmationMode,
        SECURITY_ANALYZER:
          securityAnalyzer === "none"
            ? null
            : securityAnalyzer || DEFAULT_SETTINGS.SECURITY_ANALYZER,

        // reset advanced settings
        LLM_BASE_URL: DEFAULT_SETTINGS.LLM_BASE_URL,
        AGENT: DEFAULT_SETTINGS.AGENT,
        ENABLE_DEFAULT_CONDENSER: DEFAULT_SETTINGS.ENABLE_DEFAULT_CONDENSER,
      },
      {
        onSuccess: handleSuccessfulMutation,
        onError: handleErrorMutation,
      },
    );
  };

  const advancedFormAction = (formData: FormData) => {
    const model = formData.get("llm-custom-model-input")?.toString();
    const baseUrl = formData.get("base-url-input")?.toString();
    const apiKey = formData.get("llm-api-key-input")?.toString();
    const searchApiKey = formData.get("search-api-key-input")?.toString();
    const agent = formData.get("agent-input")?.toString();
    const confirmationMode =
      formData.get("enable-confirmation-mode-switch")?.toString() === "on";
    const enableDefaultCondenser =
      formData.get("enable-memory-condenser-switch")?.toString() === "on";
    const condenserMaxSizeStr = formData
      .get("condenser-max-size-input")
      ?.toString();
    const condenserMaxSizeRaw = condenserMaxSizeStr
      ? Number.parseInt(condenserMaxSizeStr, 10)
      : undefined;
    const condenserMaxSize =
      condenserMaxSizeRaw !== undefined
        ? Math.max(20, condenserMaxSizeRaw)
        : undefined;

    const securityAnalyzer = formData
      .get("security-analyzer-input")
      ?.toString();

    // Note: Autonomy settings are now managed in the chat UI, not here
    // We preserve existing values if they exist in settings

    // Get advanced LLM config from hidden inputs
    const llmTemperature = formData.get("LLM_TEMPERATURE")?.toString();
    const llmTopP = formData.get("LLM_TOP_P")?.toString();
    const llmMaxOutputTokens = formData.get("LLM_MAX_OUTPUT_TOKENS")?.toString();
    const llmTimeout = formData.get("LLM_TIMEOUT")?.toString();
    const llmNumRetries = formData.get("LLM_NUM_RETRIES")?.toString();
    const llmCachingPrompt = formData.get("LLM_CACHING_PROMPT")?.toString();
    const llmDisableVision = formData.get("LLM_DISABLE_VISION")?.toString();
    const llmCustomProvider = formData.get("LLM_CUSTOM_LLM_PROVIDER")?.toString();

    const settingsToSave = {
      LLM_MODEL: model,
      LLM_BASE_URL: baseUrl,
      llm_api_key: apiKey || null,
      SEARCH_API_KEY: searchApiKey || "",
      AGENT: agent,
      CONFIRMATION_MODE: confirmationMode,
      ENABLE_DEFAULT_CONDENSER: enableDefaultCondenser,
      CONDENSER_MAX_SIZE:
        condenserMaxSize ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE,
      SECURITY_ANALYZER:
        securityAnalyzer === "none"
          ? null
          : securityAnalyzer || DEFAULT_SETTINGS.SECURITY_ANALYZER,

      // Advanced LLM configuration
      LLM_TEMPERATURE: llmTemperature ? parseFloat(llmTemperature) : null,
      LLM_TOP_P: llmTopP ? parseFloat(llmTopP) : null,
      LLM_MAX_OUTPUT_TOKENS: llmMaxOutputTokens ? parseInt(llmMaxOutputTokens, 10) : null,
      LLM_TIMEOUT: llmTimeout ? parseInt(llmTimeout, 10) : null,
      LLM_NUM_RETRIES: llmNumRetries ? parseInt(llmNumRetries, 10) : null,
      LLM_CACHING_PROMPT: llmCachingPrompt === "true" ? true : llmCachingPrompt === "false" ? false : null,
      LLM_DISABLE_VISION: llmDisableVision === "true" ? true : llmDisableVision === "false" ? false : null,
      LLM_CUSTOM_LLM_PROVIDER: llmCustomProvider || null,
    };

    console.log('═══════════════════════════════════════════════════');
    console.log('[LLM Settings] 📤 SENDING TO SERVER:');
    console.log('═══════════════════════════════════════════════════');
    console.log(JSON.stringify(settingsToSave, null, 2));
    console.log('═══════════════════════════════════════════════════');

    saveSettings(
      settingsToSave,
      {
        onSuccess: handleSuccessfulMutation,
        onError: handleErrorMutation,
      },
    );
  };

  const formAction = (formData: FormData) => {
    if (view === "basic") {
      basicFormAction(formData);
    } else {
      advancedFormAction(formData);
    }
  };

  const handleToggleAdvancedSettings = (isToggled: boolean) => {
    console.log('[LLM Settings] Toggle clicked, isToggled:', isToggled, 'current view:', view);
    setUserToggledView(true); // Mark that user manually toggled
    setView(isToggled ? "advanced" : "basic");
    setDirtyInputs({
      model: false,
      apiKey: false,
      searchApiKey: false,
      baseUrl: false,
      agent: false,
      confirmationMode: false,
      enableDefaultCondenser: false,
      securityAnalyzer: false,
      condenserMaxSize: false,
    });
  };

  const handleModelIsDirty = (model: string | null) => {
    // openai providers are special case; see ModelSelector
    // component for details
    const modelIsDirty = model !== settings?.LLM_MODEL.replace("openai/", "");
    setDirtyInputs((prev) => ({
      ...prev,
      model: modelIsDirty,
    }));

    // Track the currently selected model for help text display
    setCurrentSelectedModel(model);
  };

  const handleApiKeyIsDirty = (apiKey: string) => {
    const apiKeyIsDirty = apiKey !== "";
    setDirtyInputs((prev) => ({
      ...prev,
      apiKey: apiKeyIsDirty,
    }));
  };

  const handleSearchApiKeyIsDirty = (searchApiKey: string) => {
    const searchApiKeyIsDirty = searchApiKey !== settings?.SEARCH_API_KEY;
    setDirtyInputs((prev) => ({
      ...prev,
      searchApiKey: searchApiKeyIsDirty,
    }));
  };

  const handleCustomModelIsDirty = (model: string) => {
    const modelIsDirty = model !== settings?.LLM_MODEL && model !== "";
    setDirtyInputs((prev) => ({
      ...prev,
      model: modelIsDirty,
    }));

    // Track the currently selected model for help text display
    setCurrentSelectedModel(model);
  };

  const handleBaseUrlIsDirty = (baseUrl: string) => {
    const baseUrlIsDirty = baseUrl !== settings?.LLM_BASE_URL;
    setDirtyInputs((prev) => ({
      ...prev,
      baseUrl: baseUrlIsDirty,
    }));
  };

  const handleAgentIsDirty = (agent: string) => {
    const agentIsDirty = agent !== settings?.AGENT && agent !== "";
    setDirtyInputs((prev) => ({
      ...prev,
      agent: agentIsDirty,
    }));
  };

  const handleConfirmationModeIsDirty = (isToggled: boolean) => {
    const confirmationModeIsDirty = isToggled !== settings?.CONFIRMATION_MODE;
    setDirtyInputs((prev) => ({
      ...prev,
      confirmationMode: confirmationModeIsDirty,
    }));
    setConfirmationModeEnabled(isToggled);

    // When confirmation mode is enabled, set default security analyzer to "llm" if not already set
    if (isToggled && !selectedSecurityAnalyzer) {
      setSelectedSecurityAnalyzer(DEFAULT_SETTINGS.SECURITY_ANALYZER);
      setDirtyInputs((prev) => ({
        ...prev,
        securityAnalyzer: true,
      }));
    }
  };

  const handleEnableDefaultCondenserIsDirty = (isToggled: boolean) => {
    const enableDefaultCondenserIsDirty =
      isToggled !== settings?.ENABLE_DEFAULT_CONDENSER;
    setDirtyInputs((prev) => ({
      ...prev,
      enableDefaultCondenser: enableDefaultCondenserIsDirty,
    }));
  };

  const handleCondenserMaxSizeIsDirty = (value: string) => {
    const parsed = value ? Number.parseInt(value, 10) : undefined;
    const bounded = parsed !== undefined ? Math.max(20, parsed) : undefined;
    const condenserMaxSizeIsDirty =
      (bounded ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE) !==
      (settings?.CONDENSER_MAX_SIZE ?? DEFAULT_SETTINGS.CONDENSER_MAX_SIZE);
    setDirtyInputs((prev) => ({
      ...prev,
      condenserMaxSize: condenserMaxSizeIsDirty,
    }));
  };

  const handleSecurityAnalyzerIsDirty = (securityAnalyzer: string) => {
    const securityAnalyzerIsDirty =
      securityAnalyzer !== settings?.SECURITY_ANALYZER;
    setDirtyInputs((prev) => ({
      ...prev,
      securityAnalyzer: securityAnalyzerIsDirty,
    }));
  };

  const formIsDirty = Object.values(dirtyInputs).some((isDirty) => isDirty);

  const getSecurityAnalyzerOptions = () => {
    const analyzers = resources?.securityAnalyzers || [];
    const orderedItems = [];

    // Add LLM analyzer first
    if (analyzers.includes("llm")) {
      orderedItems.push({
        key: "llm",
        label: t(I18nKey.SETTINGS$SECURITY_ANALYZER_LLM_DEFAULT),
      });
    }

    // Add None option second
    orderedItems.push({
      key: "none",
      label: t(I18nKey.SETTINGS$SECURITY_ANALYZER_NONE),
    });

    // Add Invariant analyzer third
    if (analyzers.includes("invariant")) {
      orderedItems.push({
        key: "invariant",
        label: t(I18nKey.SETTINGS$SECURITY_ANALYZER_INVARIANT),
      });
    }

    // Add any other analyzers that might exist
    analyzers.forEach((analyzer) => {
      if (!["llm", "invariant", "none"].includes(analyzer)) {
        // For unknown analyzers, use the analyzer name as fallback
        // In the future, add specific i18n keys for new analyzers
        orderedItems.push({
          key: analyzer,
          label: analyzer, // TODO: Add i18n support for new analyzers
        });
      }
    });

    return orderedItems;
  };

  if (!settings || isFetching) return <LlmSettingsInputsSkeleton />;

  return (
    <SettingsErrorBoundary fallbackMessage="Failed to load LLM settings. Please try refreshing the page.">
      <div data-testid="llm-settings-screen" className="h-full">
      <form
        action={formAction}
        className="flex flex-col h-full justify-between"
      >
        <div className="p-9 flex flex-col gap-6">
          <SettingsSwitch
            testId="advanced-settings-switch"
            defaultIsToggled={view === "advanced"}
            onToggle={handleToggleAdvancedSettings}
            isToggled={view === "advanced"}
          >
            {t(I18nKey.SETTINGS$ADVANCED)}
          </SettingsSwitch>

          {view === "basic" && (
            <div
              data-testid="llm-settings-form-basic"
              className="flex flex-col gap-6"
            >
              {!isLoading && !isFetching && (
                <>
                  <ModelSelector
                    models={modelsAndProviders}
                    currentModel={settings.LLM_MODEL || DEFAULT_OPENHANDS_MODEL}
                    onChange={handleModelIsDirty}
                  />
                  {(settings.LLM_MODEL?.startsWith("openhands/") ||
                    currentSelectedModel?.startsWith("openhands/")) && (
                    <HelpLink
                      testId="openhands-api-key-help"
                      text={t(I18nKey.SETTINGS$OPENHANDS_API_KEY_HELP_TEXT)}
                      linkText={t(I18nKey.SETTINGS$NAV_API_KEYS)}
                      href="https://app.all-hands.dev/settings/api-keys"
                      suffix={t(I18nKey.SETTINGS$OPENHANDS_API_KEY_HELP_SUFFIX)}
                    />
                  )}
                </>
              )}

              <SettingsInput
                testId="llm-api-key-input"
                name="llm-api-key-input"
                label={t(I18nKey.SETTINGS_FORM$API_KEY)}
                type="password"
                className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
                placeholder={settings.LLM_API_KEY_SET ? "<hidden>" : ""}
                onChange={handleApiKeyIsDirty}
                startContent={
                  settings.LLM_API_KEY_SET && (
                    <KeyStatusIcon isSet={settings.LLM_API_KEY_SET} />
                  )
                }
              />

              <HelpLink
                testId="llm-api-key-help-anchor"
                text={t(I18nKey.SETTINGS$DONT_KNOW_API_KEY)}
                linkText={t(I18nKey.SETTINGS$CLICK_FOR_INSTRUCTIONS)}
                href="https://docs.all-hands.dev/usage/local-setup#getting-an-api-key"
              />

              <SettingsInput
                testId="search-api-key-input"
                name="search-api-key-input"
                label={t(I18nKey.SETTINGS$SEARCH_API_KEY)}
                type="password"
                className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
                defaultValue={settings.SEARCH_API_KEY || ""}
                onChange={handleSearchApiKeyIsDirty}
                placeholder={t(I18nKey.API$TAVILY_KEY_EXAMPLE)}
                startContent={
                  settings.SEARCH_API_KEY_SET && (
                    <KeyStatusIcon isSet={settings.SEARCH_API_KEY_SET} />
                  )
                }
              />

              <HelpLink
                testId="search-api-key-help-anchor"
                text={t(I18nKey.SETTINGS$SEARCH_API_KEY_OPTIONAL)}
                linkText={t(I18nKey.SETTINGS$SEARCH_API_KEY_INSTRUCTIONS)}
                href="https://tavily.com/"
              />
            </div>
          )}

          {view === "advanced" && (
            <div
              data-testid="llm-settings-form-advanced"
              className="flex flex-col gap-6"
            >
              {/* Debug: Log view state */}
              <SettingsInput
                testId="llm-custom-model-input"
                name="llm-custom-model-input"
                label={t(I18nKey.SETTINGS$CUSTOM_MODEL)}
                defaultValue={settings.LLM_MODEL || DEFAULT_OPENHANDS_MODEL}
                placeholder={DEFAULT_OPENHANDS_MODEL}
                type="text"
                className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
                onChange={handleCustomModelIsDirty}
              />
              {(settings.LLM_MODEL?.startsWith("openhands/") ||
                currentSelectedModel?.startsWith("openhands/")) && (
                <HelpLink
                  testId="openhands-api-key-help-2"
                  text={t(I18nKey.SETTINGS$OPENHANDS_API_KEY_HELP_TEXT)}
                  linkText={t(I18nKey.SETTINGS$NAV_API_KEYS)}
                  href="https://app.all-hands.dev/settings/api-keys"
                  suffix={t(I18nKey.SETTINGS$OPENHANDS_API_KEY_HELP_SUFFIX)}
                />
              )}

              <SettingsInput
                testId="base-url-input"
                name="base-url-input"
                label={t(I18nKey.SETTINGS$BASE_URL)}
                defaultValue={settings.LLM_BASE_URL}
                placeholder="https://api.openai.com"
                type="text"
                className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
                onChange={handleBaseUrlIsDirty}
              />

              <SettingsInput
                testId="llm-api-key-input"
                name="llm-api-key-input"
                label={t(I18nKey.SETTINGS_FORM$API_KEY)}
                type="password"
                className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
                placeholder={settings.LLM_API_KEY_SET ? "<hidden>" : ""}
                onChange={handleApiKeyIsDirty}
                startContent={
                  settings.LLM_API_KEY_SET && (
                    <KeyStatusIcon isSet={settings.LLM_API_KEY_SET} />
                  )
                }
              />
              <HelpLink
                testId="llm-api-key-help-anchor-advanced"
                text={t(I18nKey.SETTINGS$DONT_KNOW_API_KEY)}
                linkText={t(I18nKey.SETTINGS$CLICK_FOR_INSTRUCTIONS)}
                href="https://docs.all-hands.dev/usage/local-setup#getting-an-api-key"
              />

              <SettingsInput
                testId="search-api-key-input"
                name="search-api-key-input"
                label={t(I18nKey.SETTINGS$SEARCH_API_KEY)}
                type="password"
                className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
                defaultValue={settings.SEARCH_API_KEY || ""}
                onChange={handleSearchApiKeyIsDirty}
                placeholder={t(I18nKey.API$TVLY_KEY_EXAMPLE)}
                startContent={
                  settings.SEARCH_API_KEY_SET && (
                    <KeyStatusIcon isSet={settings.SEARCH_API_KEY_SET} />
                  )
                }
              />

              <HelpLink
                testId="search-api-key-help-anchor"
                text={t(I18nKey.SETTINGS$SEARCH_API_KEY_OPTIONAL)}
                linkText={t(I18nKey.SETTINGS$SEARCH_API_KEY_INSTRUCTIONS)}
                href="https://tavily.com/"
              />

              {/* Agent selector hidden - CodeAct is always used as the primary agent */}
              <input type="hidden" name="agent-input" value={settings.AGENT || "codeact_agent"} />
              
              {/* Visual indicator for agent setting */}
              <div className="flex items-center gap-2 p-3 bg-black rounded-lg border border-violet-500/20">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm text-text-primary font-medium">CodeAct Agent</span>
                <span className="text-xs text-text-tertiary">(Primary agent for all tasks)</span>
              </div>

              {/* Advanced LLM Configuration */}
              <div className="border-t border-violet-500/20 pt-6 mt-2">
                <h3 className="text-lg font-semibold mb-4 text-white">
                  Advanced LLM Configuration
                </h3>
                {/* Debug: Log settings */}
                <AdvancedLLMConfig
                  settings={settings}
                  onConfigChange={(config) => {
                    console.log('[LLM Settings] Config changed:', config);
                    // Update state instead of DOM manipulation
                    setAdvancedConfig(prev => ({ ...prev, ...config }));
                    // Mark form as dirty
                    setDirtyInputs(prev => ({ ...prev, model: true }));
                  }}
                />
              </div>

              {config?.APP_MODE === "saas" && (
                <SettingsDropdownInput
                  testId="runtime-settings-input"
                  name="runtime-settings-input"
                  label={
                    <>
                      {t(I18nKey.SETTINGS$RUNTIME_SETTINGS)}
                      <a href="mailto:contact@all-hands.dev">
                        {t(I18nKey.SETTINGS$GET_IN_TOUCH)}
                      </a>
                    </>
                  }
                  items={[]}
                  isDisabled
                  wrapperClassName="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]"
                />
              )}

              <div className="w-full sm:max-w-xs md:max-w-sm lg:max-w-[680px]">
                <SettingsInput
                  testId="condenser-max-size-input"
                  name="condenser-max-size-input"
                  type="number"
                  min={20}
                  step={1}
                  label={t(I18nKey.SETTINGS$CONDENSER_MAX_SIZE)}
                  defaultValue={(
                    settings.CONDENSER_MAX_SIZE ??
                    DEFAULT_SETTINGS.CONDENSER_MAX_SIZE
                  )?.toString()}
                  onChange={(value) => handleCondenserMaxSizeIsDirty(value)}
                  isDisabled={!settings.ENABLE_DEFAULT_CONDENSER}
                />
                <p className="text-xs text-text-foreground-secondary mt-1">
                  {t(I18nKey.SETTINGS$CONDENSER_MAX_SIZE_TOOLTIP)}
                </p>
              </div>

              <SettingsSwitch
                testId="enable-memory-condenser-switch"
                name="enable-memory-condenser-switch"
                defaultIsToggled={settings.ENABLE_DEFAULT_CONDENSER}
                onToggle={handleEnableDefaultCondenserIsDirty}
              >
                {t(I18nKey.SETTINGS$ENABLE_MEMORY_CONDENSATION)}
              </SettingsSwitch>
            </div>
          )}

          {/* Confirmation mode and security analyzer - always visible */}
          <div className="flex items-center gap-2">
            <SettingsSwitch
              testId="enable-confirmation-mode-switch"
              name="enable-confirmation-mode-switch"
              onToggle={handleConfirmationModeIsDirty}
              defaultIsToggled={settings.CONFIRMATION_MODE}
              isBeta
            >
              {t(I18nKey.SETTINGS$CONFIRMATION_MODE)}
            </SettingsSwitch>
            <TooltipButton
              tooltip={t(I18nKey.SETTINGS$CONFIRMATION_MODE_TOOLTIP)}
              ariaLabel={t(I18nKey.SETTINGS$CONFIRMATION_MODE)}
              className="text-text-foreground-secondary hover:text-text-primary cursor-help transition-colors duration-200"
            >
              <QuestionCircleIcon width={16} height={16} />
            </TooltipButton>
          </div>

          {confirmationModeEnabled && (
            <>
              <div className="w-full max-w-[680px]">
                <SettingsDropdownInput
                  testId="security-analyzer-input"
                  name="security-analyzer-display"
                  label={t(I18nKey.SETTINGS$SECURITY_ANALYZER)}
                  items={getSecurityAnalyzerOptions()}
                  placeholder={t(
                    I18nKey.SETTINGS$SECURITY_ANALYZER_PLACEHOLDER,
                  )}
                  selectedKey={selectedSecurityAnalyzer || "none"}
                  isClearable={false}
                  onSelectionChange={(key) => {
                    const newValue = key?.toString() || "";
                    setSelectedSecurityAnalyzer(newValue);
                    handleSecurityAnalyzerIsDirty(newValue);
                  }}
                  onInputChange={(value) => {
                    // Handle when input is cleared
                    if (!value) {
                      setSelectedSecurityAnalyzer("");
                      handleSecurityAnalyzerIsDirty("");
                    }
                  }}
                  wrapperClassName="w-full"
                />
                {/* Hidden input to store the actual key value for form submission */}
                <input
                  type="hidden"
                  name="security-analyzer-input"
                  value={selectedSecurityAnalyzer || ""}
                />
              </div>
              <p className="text-xs text-text-foreground-secondary max-w-[680px]">
                {t(I18nKey.SETTINGS$SECURITY_ANALYZER_DESCRIPTION)}
              </p>
            </>
          )}
        </div>

        {/* Hidden inputs for advanced LLM configuration */}
        <input 
          key={`llm-temp-${advancedConfig.LLM_TEMPERATURE ?? settings.LLM_TEMPERATURE}`}
          type="hidden" 
          name="LLM_TEMPERATURE" 
          value={advancedConfig.LLM_TEMPERATURE ?? settings.LLM_TEMPERATURE ?? ""} 
        />
        <input 
          key={`llm-top-p-${advancedConfig.LLM_TOP_P ?? settings.LLM_TOP_P}`}
          type="hidden" 
          name="LLM_TOP_P" 
          value={advancedConfig.LLM_TOP_P ?? settings.LLM_TOP_P ?? ""} 
        />
        <input 
          key={`llm-max-tokens-${advancedConfig.LLM_MAX_OUTPUT_TOKENS ?? settings.LLM_MAX_OUTPUT_TOKENS}`}
          type="hidden" 
          name="LLM_MAX_OUTPUT_TOKENS" 
          value={advancedConfig.LLM_MAX_OUTPUT_TOKENS ?? settings.LLM_MAX_OUTPUT_TOKENS ?? ""} 
        />
        <input 
          key={`llm-timeout-${advancedConfig.LLM_TIMEOUT ?? settings.LLM_TIMEOUT}`}
          type="hidden" 
          name="LLM_TIMEOUT" 
          value={advancedConfig.LLM_TIMEOUT ?? settings.LLM_TIMEOUT ?? ""} 
        />
        <input 
          key={`llm-retries-${advancedConfig.LLM_NUM_RETRIES ?? settings.LLM_NUM_RETRIES}`}
          type="hidden" 
          name="LLM_NUM_RETRIES" 
          value={advancedConfig.LLM_NUM_RETRIES ?? settings.LLM_NUM_RETRIES ?? ""} 
        />
        <input 
          key={`llm-caching-${advancedConfig.LLM_CACHING_PROMPT ?? settings.LLM_CACHING_PROMPT}`}
          type="hidden" 
          name="LLM_CACHING_PROMPT" 
          value={advancedConfig.LLM_CACHING_PROMPT !== undefined ? String(advancedConfig.LLM_CACHING_PROMPT) : (settings.LLM_CACHING_PROMPT !== null ? String(settings.LLM_CACHING_PROMPT) : "")} 
        />
        <input 
          key={`llm-vision-${advancedConfig.LLM_DISABLE_VISION ?? settings.LLM_DISABLE_VISION}`}
          type="hidden" 
          name="LLM_DISABLE_VISION" 
          value={advancedConfig.LLM_DISABLE_VISION !== undefined ? String(advancedConfig.LLM_DISABLE_VISION) : (settings.LLM_DISABLE_VISION !== null ? String(settings.LLM_DISABLE_VISION) : "")} 
        />
        <input 
          key={`llm-provider-${advancedConfig.LLM_CUSTOM_LLM_PROVIDER ?? settings.LLM_CUSTOM_LLM_PROVIDER}`}
          type="hidden" 
          name="LLM_CUSTOM_LLM_PROVIDER" 
          value={advancedConfig.LLM_CUSTOM_LLM_PROVIDER ?? settings.LLM_CUSTOM_LLM_PROVIDER ?? ""} 
        />

        <div className="flex gap-6 p-6 justify-end border-t border-border-secondary">
          <BrandButton
            testId="submit-button"
            type="submit"
            variant="primary"
            isDisabled={!formIsDirty || isPending}
          >
            {!isPending && t("SETTINGS$SAVE_CHANGES")}
            {isPending && t("SETTINGS$SAVING")}
          </BrandButton>
        </div>
      </form>
      
    </div>
    </SettingsErrorBoundary>
  );
}

export default LlmSettingsScreen;
