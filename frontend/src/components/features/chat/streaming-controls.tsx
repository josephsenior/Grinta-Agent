import React from "react";
import { useTranslation } from "react-i18next";
import { Settings, Zap, Clock, Play, Pause, RotateCcw } from "lucide-react";
import { Button } from "#/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "#/components/ui/card";
import { Slider } from "#/components/ui/slider";
import { Switch } from "#/components/ui/switch";
import { cn } from "#/utils/utils";

interface StreamingControlsProps {
  isStreamingEnabled: boolean;
  onToggleStreaming: (enabled: boolean) => void;
  streamingSpeed: number;
  onSpeedChange: (speed: number) => void;
  streamingDelay: number;
  onDelayChange: (delay: number) => void;
  isStreaming?: boolean;
  onStartStreaming?: () => void;
  onPauseStreaming?: () => void;
  onResetStreaming?: () => void;
  className?: string;
}

export function StreamingControls({
  isStreamingEnabled,
  onToggleStreaming,
  streamingSpeed,
  onSpeedChange,
  streamingDelay,
  onDelayChange,
  isStreaming = false,
  onStartStreaming,
  onPauseStreaming,
  onResetStreaming,
  className,
}: StreamingControlsProps) {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = React.useState(false);

  const speedLabels = {
    1: t("chat.slow", "Slow"),
    2: t("chat.normal", "Normal"),
    3: t("chat.fast", "Fast"),
    4: t("chat.veryFast", "Very Fast"),
    5: t("chat.instant", "Instant"),
  };

  // Delay labels for future use
  // const delayLabels = {
  //   0: "No Delay",
  //   100: "Short",
  //   300: "Medium",
  //   500: "Long",
  //   1000: "Very Long",
  // };

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <Zap className="w-4 h-4" />
            {t("chat.streamingControls", "Streaming Controls")}
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-8 w-8 p-0"
          >
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Main toggle */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Play className="w-4 h-4 text-primary-500" />
            <span className="text-sm font-medium">
              {t("chat.enableStreaming", "Enable Streaming")}
            </span>
          </div>
          <Switch
            checked={isStreamingEnabled}
            onCheckedChange={onToggleStreaming}
          />
        </div>

        {/* Playback controls */}
        {isStreamingEnabled && (
          <div className="flex items-center gap-2 p-2 bg-background-tertiary rounded-lg">
            <Button
              variant="ghost"
              size="sm"
              onClick={onStartStreaming}
              disabled={isStreaming}
              className="h-8 px-3"
            >
              <Play className="w-3 h-3 mr-1" />
              {t("chat.start", "Start")}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onPauseStreaming}
              disabled={!isStreaming}
              className="h-8 px-3"
            >
              <Pause className="w-3 h-3 mr-1" />
              {t("chat.pause", "Pause")}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onResetStreaming}
              className="h-8 px-3"
            >
              <RotateCcw className="w-3 h-3 mr-1" />
              {t("chat.reset", "Reset")}
            </Button>
          </div>
        )}

        {/* Advanced settings */}
        {isExpanded && isStreamingEnabled && (
          <div className="space-y-4 pt-2 border-t border-border">
            {/* Speed control */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-warning-500" />
                  <span className="text-sm font-medium text-foreground">
                    {t("chat.speed", "Speed")}
                  </span>
                </div>
                <span className="text-xs text-foreground-secondary">
                  {speedLabels[streamingSpeed as keyof typeof speedLabels] ||
                    t("chat.custom", "Custom")}
                </span>
              </div>
              <Slider
                value={[streamingSpeed]}
                onValueChange={([value]: number[]) => onSpeedChange(value)}
                min={1}
                max={5}
                step={1}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-foreground-secondary">
                <span>{t("chat.slow", "Slow")}</span>
                <span>{t("chat.instant", "Instant")}</span>
              </div>
            </div>

            {/* Delay control */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-violet-500" />
                  <span className="text-sm font-medium text-foreground">
                    {t("chat.startDelay", "Start Delay")}
                  </span>
                </div>
                <span className="text-xs text-foreground-secondary">
                  {t("chat.delayMs", "{{delay}}ms", { delay: streamingDelay })}
                </span>
              </div>
              <Slider
                value={[streamingDelay]}
                onValueChange={([value]: number[]) => onDelayChange(value)}
                min={0}
                max={1000}
                step={50}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-foreground-secondary">
                <span>{t("chat.noDelay", "No Delay")}</span>
                <span>{t("chat.oneSecondDelay", "1s Delay")}</span>
              </div>
            </div>

            {/* Preview */}
            <div className="p-3 bg-background-tertiary rounded-lg border border-border">
              <div className="text-xs text-foreground-secondary mb-2">
                {t("chat.preview", "Preview")}:
              </div>
              <div className="text-sm text-foreground font-mono">
                <span className="text-success-500">
                  {t("chat.helloWorld", "Hello world!")}
                </span>
                <span className="inline-block w-0.5 h-4 bg-brand-500 ml-0.5 animate-pulse" />
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface StreamingStatusProps {
  isStreaming: boolean;
  progress: number;
  message?: string;
  className?: string;
}

export function StreamingStatus({
  isStreaming,
  progress,
  message = "Streaming response...",
  className,
}: StreamingStatusProps) {
  if (!isStreaming && progress === 0) return null;

  return (
    <div
      className={cn(
        "flex items-center gap-3 p-3 bg-background-secondary rounded-lg border border-border",
        className,
      )}
    >
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 bg-brand-500 rounded-full animate-pulse" />
        <span className="text-sm text-foreground">{message}</span>
      </div>

      {progress > 0 && (
        <div className="flex-1 max-w-32">
          <div className="w-full bg-background-tertiary rounded-full h-1.5 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-brand-500 to-accent-500 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
          </div>
        </div>
      )}

      <span className="text-xs text-foreground-secondary">
        {Math.round(progress)}%
      </span>
    </div>
  );
}
