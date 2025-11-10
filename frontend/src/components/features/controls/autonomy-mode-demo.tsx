import React from "react";
import { AutonomyModeSelector, AutonomyMode } from "./autonomy-mode-selector";

/**
 * Demo component to showcase the autonomy mode selector
 * Shows how the component looks and behaves
 */
export function AutonomyModeDemo() {
  const [currentMode, setCurrentMode] =
    React.useState<AutonomyMode>("balanced");

  const handleModeChange = (mode: AutonomyMode) => {
    setCurrentMode(mode);
    console.log(`Autonomy mode changed to: ${mode}`);
  };

  return (
    <div className="p-6 bg-background-primary rounded-lg border border-border">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-text-primary mb-2">
          Autonomy Mode Selector
        </h3>
        <p className="text-sm text-text-secondary">
          Click the button below to switch between autonomy modes:
        </p>
      </div>

      <div className="flex items-center gap-4">
        <AutonomyModeSelector
          currentMode={currentMode}
          onModeChange={handleModeChange}
        />

        <div className="text-sm text-text-secondary">
          Current mode:{" "}
          <span className="font-medium text-text-primary">{currentMode}</span>
        </div>
      </div>

      <div className="mt-4 p-3 bg-background-secondary rounded-md">
        <p className="text-xs text-text-tertiary">
          This selector allows users to choose between three autonomy levels:
        </p>
        <ul className="text-xs text-text-tertiary mt-2 space-y-1">
          <li>
            • <strong>Supervised:</strong> Always ask for confirmation
          </li>
          <li>
            • <strong>Balanced:</strong> Ask for confirmation on high-risk
            actions
          </li>
          <li>
            • <strong>Full Autonomous:</strong> Execute without confirmation
          </li>
        </ul>
      </div>
    </div>
  );
}
