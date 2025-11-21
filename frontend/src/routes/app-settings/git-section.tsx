import React from "react";
import { useTranslation } from "react-i18next";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { I18nKey } from "#/i18n/declaration";
import { SettingsPanel } from "./settings-panel";

interface GitSectionProps {
  gitUserName: string;
  gitUserEmail: string;
  onGitUserNameChange: (value: string) => void;
  onGitUserEmailChange: (value: string) => void;
}

export function GitSection({
  gitUserName,
  gitUserEmail,
  onGitUserNameChange,
  onGitUserEmailChange,
}: GitSectionProps) {
  const { t } = useTranslation();

  return (
    <SettingsPanel title={t(I18nKey.SETTINGS$GIT_SETTINGS)}>
      <p className="text-sm text-foreground-secondary mb-4 w-full">
        {t(I18nKey.SETTINGS$GIT_SETTINGS_DESCRIPTION)}
      </p>
      <div className="grid gap-6 md:grid-cols-2">
        <SettingsInput
          testId="git-user-name-input"
          name="git-user-name-input"
          type="text"
          label={t(I18nKey.SETTINGS$GIT_USERNAME)}
          defaultValue={gitUserName}
          onChange={onGitUserNameChange}
          placeholder="Username for git commits"
          className="w-full"
        />
        <SettingsInput
          testId="git-user-email-input"
          name="git-user-email-input"
          type="email"
          label={t(I18nKey.SETTINGS$GIT_EMAIL)}
          defaultValue={gitUserEmail}
          onChange={onGitUserEmailChange}
          placeholder="Email for git commits"
          className="w-full"
        />
      </div>
    </SettingsPanel>
  );
}
