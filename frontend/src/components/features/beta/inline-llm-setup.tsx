import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Bot, Key, Sparkles } from "lucide-react";
import { Button } from "#/components/ui/button";
import { Input } from "#/components/ui/input";
import { useSettings } from "#/hooks/query/use-settings";
import { useSaveSettings } from "#/hooks/mutation/use-save-settings";
import { Card, CardContent } from "#/components/ui/card";

interface InlineLLMSetupProps {
  onComplete?: () => void;
}

const POPULAR_MODELS = [
  {
    id: "anthropic/claude-3-7-sonnet-20250219",
    name: "Claude 3.7 Sonnet",
    provider: "Anthropic",
  },
  {
    id: "anthropic/claude-3-5-sonnet-20241022",
    name: "Claude 3.5 Sonnet",
    provider: "Anthropic",
  },
  { id: "openai/gpt-4o", name: "GPT-4o", provider: "OpenAI" },
  { id: "openai/gpt-4o-mini", name: "GPT-4o Mini", provider: "OpenAI" },
  { id: "gemini/gemini-1.5-pro", name: "Gemini 1.5 Pro", provider: "Gemini" },
  { id: "xai/grok-beta", name: "Grok Beta", provider: "Grok" },
];

export function InlineLLMSetup({ onComplete }: InlineLLMSetupProps) {
  const { t } = useTranslation();
  const { data: settings } = useSettings();
  const { mutate: saveSettings, isPending } = useSaveSettings();
  const [selectedModel, setSelectedModel] = useState(
    settings?.LLM_MODEL || POPULAR_MODELS[1].id,
  );
  const [apiKey, setApiKey] = useState("");

  const handleSave = () => {
    saveSettings(
      {
        LLM_MODEL: selectedModel,
        llm_api_key: apiKey,
      },
      {
        onSuccess: () => {
          onComplete?.();
        },
      },
    );
  };

  const getProviderFromModel = (modelId: string) => {
    if (modelId.includes("anthropic")) return "Anthropic";
    if (modelId.includes("openai")) return "OpenAI";
    if (modelId.includes("google") || modelId.includes("gemini")) return "Gemini";
    if (modelId.includes("xai") || modelId.includes("grok")) return "Grok";
    return "Custom";
  };

  const provider = getProviderFromModel(selectedModel);

  return (
    <Card className="mx-auto max-w-2xl my-8 border-brand-500/30">
      <CardContent className="p-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-brand-500 to-brand-600 flex items-center justify-center">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-foreground mb-2">
            {t("beta.configureAI", "Configure Your AI")}
          </h2>
          <p className="text-foreground-secondary">
            {t(
              "beta.configureAIDescription",
              "Choose your model and enter your API key to get started",
            )}
          </p>
        </div>

        {/* Model Selection */}
        <div className="mb-6">
          <div className="block text-sm font-medium text-foreground mb-3">
            <Bot className="w-4 h-4 inline mr-2" />
            {t("beta.chooseModel", "Choose Model")}
          </div>
          <div
            className="grid grid-cols-2 gap-3"
            role="radiogroup"
            aria-label="Choose Model"
          >
            {POPULAR_MODELS.map((model) => (
              <button
                key={model.id}
                type="button"
                onClick={() => {
                  setSelectedModel(model.id);
                }}
                className={`p-4 rounded-lg border-2 transition-all text-left ${
                  selectedModel === model.id
                    ? "border-brand-500 bg-brand-500/10"
                    : "border-border hover:border-brand-500/50 hover:bg-background-tertiary/50"
                }`}
              >
                <div className="font-semibold text-foreground mb-1">
                  {model.name}
                </div>
                <div className="text-xs text-foreground-secondary">
                  {model.provider}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* API Key Input */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-foreground mb-2">
            <Key className="w-4 h-4 inline mr-2" />
            {t("beta.apiKeyLabel", "{{provider}} API Key", { provider })}
          </label>
          <Input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={`Enter your ${provider} API key...`}
            className="w-full"
          />
          <p className="text-xs text-foreground-secondary mt-2">
            {t("beta.getApiKeyFrom", "Get your key from:")}{" "}
            {provider === "Anthropic" && (
              <a
                href="https://console.anthropic.com/settings/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-violet-500 hover:underline"
              >
                {t("beta.anthropicConsole", "console.anthropic.com")}
              </a>
            )}
            {provider === "OpenAI" && (
              <a
                href="https://platform.openai.com/api-keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-violet-500 hover:underline"
              >
                {t("beta.openaiPlatform", "platform.openai.com")}
              </a>
            )}
          </p>
        </div>

        {/* Info Box */}
        <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <p className="text-sm text-blue-400">
            💡{" "}
            <strong>
              {t("beta.apiKeyPrivacy", "Your API key stays on your device.")}
            </strong>{" "}
            {t(
              "beta.apiKeyPrivacyDescription",
              "We never store or transmit it to our servers.",
            )}
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <Button
            onClick={handleSave}
            className="flex-1"
            disabled={!apiKey.trim() || isPending}
          >
            {isPending ? "Saving..." : "Start Building"}
          </Button>
        </div>

        {/* Link to Settings */}
        <div className="text-center mt-6">
          <a
            href="/settings"
            className="text-sm text-foreground-secondary hover:text-violet-500 transition-colors"
          >
            {t("beta.advancedSettings", "Advanced settings")} →
          </a>
        </div>
      </CardContent>
    </Card>
  );
}
