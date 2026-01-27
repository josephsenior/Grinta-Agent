import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { mapProvider } from "#/utils/map-provider";
import { CustomDropdown } from "#/components/shared/inputs/custom-dropdown";
import {
  VERIFIED_MODELS,
  VERIFIED_PROVIDERS,
} from "#/utils/verified-models";
import { extractModelAndProvider } from "#/utils/extract-model-and-provider";

interface ModelSelectorProps {
  isDisabled?: boolean;
  models: Record<string, { separator: string; models: string[] }>;
  currentModel?: string;
  onChange?: (model: string | null) => void;
}

export function ModelSelector({
  isDisabled,
  models,
  currentModel,
  onChange,
}: ModelSelectorProps) {
  const [, setLlmId] = React.useState<string | undefined>(undefined);
  const [selectedProvider, setSelectedProvider] = React.useState<
    string | undefined
  >(undefined);
  const [selectedModel, setSelectedModel] = React.useState<string | undefined>(
    undefined,
  );

  const normalizeProvider = (provider?: string | null) => {
    if (!provider) return undefined;
    return provider.toLowerCase();
  };

  // Get the appropriate verified models array based on the selected provider
  const getVerifiedModels = () => {
    return VERIFIED_MODELS;
  };

  React.useEffect(() => {
    if (currentModel) {
      // runs when resetting to defaults
      const { provider, model } = extractModelAndProvider(currentModel);

      setLlmId(currentModel);
      setSelectedProvider(normalizeProvider(provider));
      setSelectedModel(model || undefined);
    }
  }, [currentModel]);

  const handleChangeProvider = (provider: string) => {
    setSelectedProvider(normalizeProvider(provider));
    setSelectedModel(undefined);

    const normalized = normalizeProvider(provider);
    const separator = models[normalized || provider]?.separator || "";
    setLlmId((normalized || provider) + separator);
  };

  const handleChangeModel = (model: string) => {
    const providerKey = normalizeProvider(selectedProvider) || "";
    const separator = models[providerKey]?.separator || "";
    let fullModel = providerKey + separator + model;
    if (selectedProvider === "openai") {
      // Direct SDK integration lists OpenAI models without the openai/ prefix
      fullModel = model;
    }
    setLlmId(fullModel);
    setSelectedModel(model);
    onChange?.(fullModel);
  };

  const clear = () => {
    setSelectedProvider(undefined);
    setLlmId(undefined);
  };

  const { t } = useTranslation();

  return (
    <div className="flex flex-col sm:flex-row w-full max-w-[680px] justify-between gap-3 sm:gap-4 md:gap-[46px]">
      {/* Hidden inputs for form submission */}
      <input
        type="hidden"
        name="llm-provider-input"
        value={selectedProvider || ""}
      />
      <input type="hidden" name="llm-model-input" value={selectedModel || ""} />

      <fieldset className="flex flex-col gap-2 sm:gap-2.5 w-full">
        <label className="text-xs sm:text-sm">{t(I18nKey.LLM$PROVIDER)}</label>
        <CustomDropdown
          data-testid="llm-provider-input"
          aria-label={t(I18nKey.LLM$PROVIDER)}
          placeholder={t(I18nKey.LLM$SELECT_PROVIDER_PLACEHOLDER)}
          disabled={isDisabled}
          value={selectedProvider}
          onSelectionChange={(key) => {
            if (key) {
              handleChangeProvider(key);
            }
          }}
          onInputChange={(value) => !value && clear()}
          isLoading={false}
          loadingText={t("HOME$LOADING")}
          items={[
            {
              title: t(I18nKey.MODEL_SELECTOR$VERIFIED),
              items: Object.keys(models).map((provider) => {
                const normalized = normalizeProvider(provider);
                return {
                  key: normalized || provider,
                  label: mapProvider(normalized || provider || ""),
                };
              }),
            },
          ]}
        />
      </fieldset>

      <fieldset className="flex flex-col gap-2 sm:gap-2.5 w-full">
        <label className="text-xs sm:text-sm">{t(I18nKey.LLM$MODEL)}</label>
        <CustomDropdown
          data-testid="llm-model-input"
          aria-label={t(I18nKey.LLM$MODEL)}
          placeholder={t(I18nKey.LLM$SELECT_MODEL_PLACEHOLDER)}
          disabled={isDisabled || !selectedProvider}
          value={selectedModel}
          onSelectionChange={(key) => {
            if (key) {
              handleChangeModel(key);
            }
          }}
          isLoading={false}
          loadingText={t("HOME$LOADING")}
          items={[
            {
              title: t(I18nKey.MODEL_SELECTOR$VERIFIED),
              items: (
                models[normalizeProvider(selectedProvider) || ""]?.models || []
              ).map((model) => ({
                key: model,
                label: model,
              })),
            },
          ]}
        />
      </fieldset>
    </div>
  );
}
