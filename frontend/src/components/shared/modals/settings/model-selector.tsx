import React from "react";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { mapProvider } from "#/utils/map-provider";
import { CustomDropdown } from "#/components/shared/inputs/custom-dropdown";
import {
  VERIFIED_MODELS,
  VERIFIED_PROVIDERS,
  VERIFIED_OPENHANDS_MODELS,
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
  const [, setLitellmId] = React.useState<string | undefined>(undefined);
  const [selectedProvider, setSelectedProvider] = React.useState<
    string | undefined
  >(undefined);
  const [selectedModel, setSelectedModel] = React.useState<string | undefined>(
    undefined,
  );


  // Get the appropriate verified models array based on the selected provider
  const getVerifiedModels = () => {
    if (selectedProvider === "openhands") {
      return VERIFIED_OPENHANDS_MODELS;
    }
    return VERIFIED_MODELS;
  };

  React.useEffect(() => {
    if (currentModel) {
      // runs when resetting to defaults
      const { provider, model } = extractModelAndProvider(currentModel);

      setLitellmId(currentModel);
      setSelectedProvider(provider || undefined);
      setSelectedModel(model || undefined);
    }
  }, [currentModel]);

  const handleChangeProvider = (provider: string) => {
    setSelectedProvider(provider || undefined);
    setSelectedModel(undefined);

    const separator = models[provider]?.separator || "";
    setLitellmId(provider + separator);
  };

  const handleChangeModel = (model: string) => {
    const separator = models[selectedProvider || ""]?.separator || "";
    let fullModel = (selectedProvider || "") + separator + model;
    if (selectedProvider === "openai") {
      // LiteLLM lists OpenAI models without the openai/ prefix
      fullModel = model;
    }
    setLitellmId(fullModel);
    setSelectedModel(model);
    onChange?.(fullModel);
  };

  const clear = () => {
    setSelectedProvider(undefined);
    setLitellmId(undefined);
  };

  const { t } = useTranslation();

  return (
    <div className="flex flex-col sm:flex-row w-full max-w-[680px] justify-between gap-3 sm:gap-4 md:gap-[46px]">
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
              items: VERIFIED_PROVIDERS.filter(
                (provider) => models[provider],
              ).map((provider) => ({
                key: provider,
                label: mapProvider(provider),
              })),
            },
            ...(Object.keys(models).some(
              (provider) => !VERIFIED_PROVIDERS.includes(provider),
            )
              ? [
                  {
                    title: t(I18nKey.MODEL_SELECTOR$OTHERS),
                    items: Object.keys(models)
                      .filter(
                        (provider) => !VERIFIED_PROVIDERS.includes(provider),
                      )
                      .map((provider) => ({
                        key: provider,
                        label: mapProvider(provider),
                      })),
                  },
                ]
              : []),
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
              items: getVerifiedModels()
                .filter((model) =>
                  models[selectedProvider || ""]?.models?.includes(model),
                )
                .map((model) => ({
                  key: model,
                  label: model,
                })),
            },
            ...(models[selectedProvider || ""]?.models?.some(
              (model) => !getVerifiedModels().includes(model),
            )
              ? [
                  {
                    title: t(I18nKey.MODEL_SELECTOR$OTHERS),
                    items:
                      models[selectedProvider || ""]?.models
                        .filter((model) => !getVerifiedModels().includes(model))
                        .map((model) => ({
                          key: model,
                          label: model,
                        })) || [],
                  },
                ]
              : []),
          ]}
        />
      </fieldset>
    </div>
  );
}
