import { useTranslation } from "react-i18next";

export default function SettingsHub() {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      <div className="bg-[var(--bg-elevated)] border border-[var(--border-primary)] rounded-xl p-6">
        <p className="text-[var(--text-secondary)] text-sm leading-relaxed">
          {t(
            "settings.description",
            "Use the sidebar to navigate between different settings categories. Configure your AI models, account preferences, integrations, and more.",
          )}
        </p>
      </div>
    </div>
  );
}
