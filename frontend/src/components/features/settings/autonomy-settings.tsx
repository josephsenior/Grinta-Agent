import React from "react";
import { useTranslation } from "react-i18next";
import { Shield, Eye, Zap, Info } from "lucide-react";
import { SettingsSwitch } from "./settings-switch";
import { SettingsDropdownInput } from "./settings-dropdown-input";
import { logger } from "#/utils/logger";

interface AutonomySettingsProps {
  autonomyLevel?: string;
  enablePermissions?: boolean;
  enableCheckpoints?: boolean;
  onAutonomyLevelChange?: (level: string) => void;
  onPermissionsToggle?: (enabled: boolean) => void;
  onCheckpointsToggle?: (enabled: boolean) => void;
}

/**
 * Autonomy settings component for advanced configuration
 * Provides detailed control over agent autonomy and safety features
 */
export function AutonomySettings({
  autonomyLevel = "balanced",
  enablePermissions = true,
  enableCheckpoints = true,
  onAutonomyLevelChange,
  onPermissionsToggle,
  onCheckpointsToggle,
}: AutonomySettingsProps) {
  const { t } = useTranslation();

  const autonomyOptions = [
    {
      key: "supervised",
      label: t("settings.autonomy.supervised", "Supervised Mode"),
    },
    {
      key: "balanced",
      label: t("settings.autonomy.balanced", "Balanced Mode"),
    },
    {
      key: "full",
      label: t("settings.autonomy.full", "Full Autonomous Mode"),
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      {/* Autonomy Level */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-text-primary">
            Agent Autonomy Level
          </h3>
          <Info className="w-4 h-4 text-text-tertiary" />
        </div>

        {/* Wrap in a div to isolate from form events */}
        <div
          onClick={() => {
            logger.debug("[AutonomySettings] Wrapper clicked");
            // Don't prevent propagation, just log to debug
          }}
        >
          <SettingsDropdownInput
            testId="autonomy-level-input"
            name="autonomy-level-input"
            label="Autonomy Mode"
            items={autonomyOptions}
            placeholder="Select autonomy mode"
            selectedKey={autonomyLevel}
            onSelectionChange={(key) => {
              logger.debug(
                "═══════════════════════════════════════════════════",
              );
              logger.debug("[AutonomySettings] 🎯 SELECTION CHANGED:", key);
              logger.debug("[AutonomySettings] Previous value:", autonomyLevel);
              logger.debug("[AutonomySettings] New value:", key);
              logger.debug(
                "═══════════════════════════════════════════════════",
              );
              onAutonomyLevelChange?.(key as string);
            }}
          />
        </div>

        <div className="text-xs text-text-tertiary mt-2">
          Controls how much the agent asks for confirmation before taking
          actions.
        </div>
      </div>

      {/* Fine-grained Permissions */}
      <div className="flex flex-col gap-3">
        <SettingsSwitch
          testId="enable-permissions-switch"
          name="enable-permissions-switch"
          isToggled={enablePermissions}
          onToggle={onPermissionsToggle}
        >
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-text-secondary" />
            <span>Fine-grained Permissions</span>
          </div>
        </SettingsSwitch>

        <div className="text-xs text-text-tertiary">
          Enable detailed permission controls for file operations, git commands,
          shell access, and more.
        </div>
      </div>

      {/* Rollback System */}
      <div className="flex flex-col gap-3">
        <SettingsSwitch
          testId="enable-checkpoints-switch"
          name="enable-checkpoints-switch"
          isToggled={enableCheckpoints}
          onToggle={onCheckpointsToggle}
        >
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-text-secondary" />
            <span>Automatic Checkpoints</span>
          </div>
        </SettingsSwitch>

        <div className="text-xs text-text-tertiary">
          Automatically create checkpoints before risky operations to enable
          rollback.
        </div>
      </div>

      {/* Mode Descriptions */}
      <div className="bg-background-secondary rounded-lg p-4 space-y-3">
        <h4 className="text-xs font-medium text-text-primary">Mode Details</h4>

        <div className="space-y-2">
          <div className="flex items-start gap-2">
            <Shield className="w-3.5 h-3.5 text-orange-500 mt-0.5 flex-shrink-0" />
            <div>
              <div className="text-xs font-medium text-orange-500">
                Supervised
              </div>
              <div className="text-[10px] text-text-tertiary">
                Agent requests confirmation for every action. Maximum safety.
              </div>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <Eye className="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
            <div>
              <div className="text-xs font-medium text-blue-500">Balanced</div>
              <div className="text-[10px] text-text-tertiary">
                Agent confirms only high-risk operations. Good balance of safety
                and efficiency.
              </div>
            </div>
          </div>

          <div className="flex items-start gap-2">
            <Zap className="w-3.5 h-3.5 text-green-500 mt-0.5 flex-shrink-0" />
            <div>
              <div className="text-xs font-medium text-green-500">
                Full Autonomous
              </div>
              <div className="text-[10px] text-text-tertiary">
                Agent executes tasks independently. Maximum efficiency with
                built-in safety.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
