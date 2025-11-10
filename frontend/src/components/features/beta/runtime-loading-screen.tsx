import React, { useEffect, useState } from "react";
import { Loader2, CheckCircle, Circle, Container } from "lucide-react";
import { Card, CardContent } from "#/components/ui/card";

interface RuntimeLoadingScreenProps {
  onComplete?: () => void;
}

interface LoadingStep {
  id: string;
  label: string;
  status: "pending" | "loading" | "complete";
  duration?: number;
}

const LOADING_STEPS: LoadingStep[] = [
  {
    id: "docker",
    label: "Starting Docker runtime...",
    status: "pending",
    duration: 3000,
  },
  {
    id: "container",
    label: "Initializing container...",
    status: "pending",
    duration: 2000,
  },
  {
    id: "agent",
    label: "Loading AI agent...",
    status: "pending",
    duration: 2000,
  },
  { id: "ready", label: "System ready!", status: "pending", duration: 1000 },
];

export function RuntimeLoadingScreen({
  onComplete,
}: RuntimeLoadingScreenProps) {
  const [steps, setSteps] = useState<LoadingStep[]>(LOADING_STEPS);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  useEffect(() => {
    const processSteps = async () => {
      for (let i = 0; i < LOADING_STEPS.length; i++) {
        // Set current step to loading
        setCurrentStepIndex(i);
        setSteps((prev) =>
          prev.map((step, idx) => ({
            ...step,
            status: idx === i ? "loading" : idx < i ? "complete" : "pending",
          })),
        );

        // Wait for step duration
        await new Promise((resolve) =>
          setTimeout(resolve, LOADING_STEPS[i].duration),
        );

        // Mark step as complete
        setSteps((prev) =>
          prev.map((step, idx) => ({
            ...step,
            status: idx <= i ? "complete" : "pending",
          })),
        );
      }

      // All steps complete
      setTimeout(() => {
        onComplete?.();
      }, 500);
    };

    processSteps();
  }, [onComplete]);

  const progress = ((currentStepIndex + 1) / LOADING_STEPS.length) * 100;

  return (
    <div className="fixed inset-0 bg-background-primary flex items-center justify-center z-50">
      <Card className="max-w-md w-full mx-4">
        <CardContent className="p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-brand-500 to-brand-600 flex items-center justify-center">
              <Container className="w-8 h-8 text-white animate-pulse" />
            </div>
            <h2 className="text-2xl font-bold text-foreground mb-2">
              Starting Forge
            </h2>
            <p className="text-sm text-foreground-secondary">
              Preparing your development environment...
            </p>
          </div>

          {/* Progress Bar */}
          <div className="mb-6">
            <div className="h-2 bg-background-tertiary rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-brand-500 to-brand-600 transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="text-xs text-foreground-secondary text-right mt-2">
              {Math.round(progress)}%
            </div>
          </div>

          {/* Loading Steps */}
          <div className="space-y-3">
            {steps.map((step, index) => (
              <div
                key={step.id}
                className="flex items-center gap-3 text-sm transition-all duration-300"
              >
                {step.status === "complete" ? (
                  <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
                ) : step.status === "loading" ? (
                  <Loader2 className="w-5 h-5 text-violet-500 flex-shrink-0 animate-spin" />
                ) : (
                  <Circle className="w-5 h-5 text-foreground-secondary/30 flex-shrink-0" />
                )}
                <span
                  className={
                    step.status === "complete"
                      ? "text-foreground"
                      : step.status === "loading"
                        ? "text-foreground font-medium"
                        : "text-foreground-secondary"
                  }
                >
                  {step.label}
                </span>
              </div>
            ))}
          </div>

          {/* Tip */}
          <div className="mt-6 pt-6 border-t border-border">
            <p className="text-xs text-foreground-secondary text-center">
              💡 First startup may take a moment. Subsequent loads will be
              faster.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
