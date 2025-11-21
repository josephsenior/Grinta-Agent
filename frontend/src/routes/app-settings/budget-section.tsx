import React from "react";
import { useTranslation } from "react-i18next";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { I18nKey } from "#/i18n/declaration";
import { SettingsPanel } from "./settings-panel";

interface BudgetSectionProps {
  maxBudget: string;
  onBudgetChange: (value: string) => void;
}

export function BudgetSection({
  maxBudget,
  onBudgetChange,
}: BudgetSectionProps) {
  const { t } = useTranslation();

  return (
    <SettingsPanel title={t("SETTINGS$BUDGET_AND_USAGE", "Budget & Usage")}>
      <div className="grid gap-4">
        <div className="w-full">
          <SettingsInput
            testId="max-budget-per-task-input"
            name="max-budget-per-task-input"
            type="number"
            label={t(I18nKey.SETTINGS$MAX_BUDGET_PER_CONVERSATION)}
            defaultValue={maxBudget}
            onChange={onBudgetChange}
            placeholder={t(I18nKey.SETTINGS$MAXIMUM_BUDGET_USD)}
            min={1}
            step={1}
            className="w-full"
          />
        </div>
      </div>
    </SettingsPanel>
  );
}
