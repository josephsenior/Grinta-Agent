import React from "react";
import { useTranslation } from "react-i18next";
import { GitBranch } from "lucide-react";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { I18nKey } from "#/i18n/declaration";
import { Accordion } from "#/components/features/settings/accordion";

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
    <Accordion
      title={t(I18nKey.SETTINGS$GIT_SETTINGS)}
      icon={GitBranch}
      defaultOpen
    >
      <p className="text-sm text-[var(--text-tertiary)] mb-4">
        {t(I18nKey.SETTINGS$GIT_SETTINGS_DESCRIPTION)}
      </p>
      <div className="grid grid-cols-1 gap-4">
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
    </Accordion>
  );
}
