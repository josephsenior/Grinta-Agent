import React from "react";
import { TFunction } from "i18next";
import { SettingsSwitch } from "#/components/features/settings/settings-switch";
import { TooltipButton } from "#/components/shared/buttons/tooltip-button";
import QuestionCircleIcon from "#/icons/question-circle.svg?react";
import { SettingsDropdownInput } from "#/components/features/settings/settings-dropdown-input";
import { I18nKey } from "#/i18n/declaration";

export interface ConfirmationSettingsSectionProps {
  confirmationModeEnabled: boolean;
  selectedSecurityAnalyzer: string;
  securityAnalyzerOptions: { key: string; label: string }[];
  onToggleConfirmationMode: (value: boolean) => void;
  onSecurityAnalyzerChange: (value: string) => void;
  onSecurityAnalyzerInputClear: () => void;
  t: TFunction;
}

export function ConfirmationSettingsSection({
  confirmationModeEnabled,
  selectedSecurityAnalyzer,
  securityAnalyzerOptions,
  onToggleConfirmationMode,
  onSecurityAnalyzerChange,
  onSecurityAnalyzerInputClear,
  t,
}: ConfirmationSettingsSectionProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <SettingsSwitch
          testId="enable-confirmation-mode-switch"
          name="enable-confirmation-mode-switch"
          isToggled={confirmationModeEnabled}
          onToggle={onToggleConfirmationMode}
          defaultIsToggled={confirmationModeEnabled}
          isBeta
        >
          {t(I18nKey.SETTINGS$CONFIRMATION_MODE)}
        </SettingsSwitch>
        <TooltipButton
          tooltip={t(I18nKey.SETTINGS$CONFIRMATION_MODE_TOOLTIP)}
          ariaLabel={t(I18nKey.SETTINGS$CONFIRMATION_MODE)}
          className="text-foreground-tertiary hover:text-foreground-secondary cursor-help transition-colors duration-200"
        >
          <QuestionCircleIcon width={16} height={16} />
        </TooltipButton>
      </div>

      {confirmationModeEnabled && (
        <div className="flex flex-col gap-2">
          <div className="w-full max-w-[680px]">
            <SettingsDropdownInput
              testId="security-analyzer-input"
              name="security-analyzer-display"
              label={t(I18nKey.SETTINGS$SECURITY_ANALYZER)}
              items={securityAnalyzerOptions}
              placeholder={t(I18nKey.SETTINGS$SECURITY_ANALYZER_PLACEHOLDER)}
              selectedKey={selectedSecurityAnalyzer || "none"}
              isClearable={false}
              onSelectionChange={(key) => {
                const value = key?.toString() || "";
                onSecurityAnalyzerChange(value);
              }}
              onInputChange={(value) => {
                if (!value) {
                  onSecurityAnalyzerInputClear();
                }
              }}
              wrapperClassName="w-full"
            />
            <input
              type="hidden"
              name="security-analyzer-input"
              value={selectedSecurityAnalyzer || ""}
            />
          </div>
          <p className="text-xs text-foreground-secondary max-w-[680px]">
            {t(I18nKey.SETTINGS$SECURITY_ANALYZER_DESCRIPTION)}
          </p>
        </div>
      )}
    </div>
  );
}
