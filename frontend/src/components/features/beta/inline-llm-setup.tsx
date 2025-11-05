import React, { useState } from "react";
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
  { id: "anthropic/claude-sonnet-4", name: "Claude Sonnet 4", provider: "Anthropic" },
  { id: "anthropic/claude-haiku-4-5-20251001", name: "Claude Haiku 4.5", provider: "Anthropic" },
  { id: "openai/gpt-4o", name: "GPT-4o", provider: "OpenAI" },
  { id: "openai/gpt-4o-mini", name: "GPT-4o Mini", provider: "OpenAI" },
];

export function InlineLLMSetup({ onComplete }: InlineLLMSetupProps) {
  const { data: settings } = useSettings();
  const { mutate: saveSettings, isPending } = useSaveSettings();
  const [selectedModel, setSelectedModel] = useState(settings?.LLM_MODEL || POPULAR_MODELS[1].id);
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
    if (modelId.includes("google")) return "Google";
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
            Configure Your AI
          </h2>
          <p className="text-foreground-secondary">
            Choose your model and enter your API key to get started
          </p>
        </div>

        {/* Model Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-foreground mb-3">
            <Bot className="w-4 h-4 inline mr-2" />
            Choose Model
          </label>
          <div className="grid grid-cols-2 gap-3">
            {POPULAR_MODELS.map((model) => (
              <button
                key={model.id}
                onClick={() => setSelectedModel(model.id)}
                className={`p-4 rounded-lg border-2 transition-all text-left ${
                  selectedModel === model.id
                    ? "border-brand-500 bg-brand-500/10"
                    : "border-border hover:border-brand-500/50 hover:bg-background-tertiary/50"
                }`}
              >
                <div className="font-semibold text-foreground mb-1">{model.name}</div>
                <div className="text-xs text-foreground-secondary">{model.provider}</div>
              </button>
            ))}
          </div>
        </div>

        {/* API Key Input */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-foreground mb-2">
            <Key className="w-4 h-4 inline mr-2" />
            {provider} API Key
          </label>
          <Input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={`Enter your ${provider} API key...`}
            className="w-full"
          />
          <p className="text-xs text-foreground-secondary mt-2">
            Get your key from:{" "}
            {provider === "Anthropic" && (
              <a
                href="https://console.anthropic.com/settings/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-violet-500 hover:underline"
              >
                console.anthropic.com
              </a>
            )}
            {provider === "OpenAI" && (
              <a
                href="https://platform.openai.com/api-keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-violet-500 hover:underline"
              >
                platform.openai.com
              </a>
            )}
          </p>
        </div>

        {/* Info Box */}
        <div className="mb-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <p className="text-sm text-blue-400">
            💡 <strong>Your API key stays on your device.</strong> We never store or transmit it to our servers.
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
            Advanced settings →
          </a>
        </div>
      </CardContent>
    </Card>
  );
}

