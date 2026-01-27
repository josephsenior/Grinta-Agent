import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { Settings } from "#/types/settings";

interface SettingsChecklistProps {
  settings?: Settings | null;
  isSaas: boolean;
}

const getChecklist = (settings?: Settings | null, isSaas?: boolean) => {
  const hasModel = Boolean(settings?.LLM_API_KEY_SET);
  const hasRepo = Boolean(
    settings?.PROVIDER_TOKENS_SET &&
      Object.values(settings.PROVIDER_TOKENS_SET).some(Boolean),
  );
  const hasSecrets = Boolean(settings?.ENABLE_DEFAULT_CONDENSER);

  return [
    {
      id: "llm",
      label: "Configure AI model",
      description: "Add your preferred LLM and API key",
      to: "/settings/llm",
      complete: hasModel,
    },
    {
      id: "repo",
      label: "Connect your repo",
      description: "Authorize Git provider for conversations",
      to: "/settings/integrations",
      complete: hasRepo,
    },
    {
      id: "secrets",
      label: "Secure secrets",
      description: "Store API keys safely for agents",
      to: "/settings/secrets",
      complete: hasSecrets,
      disabled: !isSaas && !hasRepo,
      disabledReason: !isSaas
        ? "Secrets require SaaS mode or BYO vault"
        : undefined,
    },
  ];
};

export function SettingsChecklist({
  settings,
  isSaas,
}: SettingsChecklistProps) {
  const { t } = useTranslation();
  const items = getChecklist(settings, isSaas);
  const allComplete = items.every((item) => item.complete);

  return (
    <section
      aria-label={t("settings.setupChecklistAriaLabel", "Recommended setup")}
      className="rounded-3xl border border-white/10 bg-gradient-to-br from-white/5 via-black/40 to-black/70 px-6 py-5 backdrop-blur-2xl"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-white">
            {t("settings.setupChecklist", "Setup checklist")}
          </p>
          <p className="text-xs text-white/60">
            {allComplete
              ? t(
                  "settings.setupChecklistComplete",
                  "You're ready to go — tweak settings anytime.",
                )
              : t(
                  "settings.setupChecklistIncomplete",
                  "Complete these steps to get the best experience.",
                )}
          </p>
        </div>
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {items.map((item) => {
          const isDisabled = item.disabled && !item.complete;
          let className =
            "rounded-2xl border px-4 py-3 transition focus:outline-none focus:ring-2 focus:ring-brand-violet/50 ";
          if (item.complete) {
            className += "border-emerald-500/40 bg-emerald-500/10 text-white";
          } else if (isDisabled) {
            className +=
              "border-white/5 bg-white/5 text-white/40 cursor-not-allowed";
          } else {
            className +=
              "border-white/10 bg-white/5 text-white hover:border-white/20";
          }
          return (
            <Link
              key={item.id}
              to={item.to}
              aria-disabled={isDisabled}
              tabIndex={isDisabled ? -1 : 0}
              className={className}
              title={isDisabled ? item.disabledReason : undefined}
            >
              <div className="flex items-center gap-2">
                <span
                  aria-hidden="true"
                  className={`h-2 w-2 rounded-full ${
                    item.complete
                      ? "bg-emerald-400"
                      : "bg-white/40 group-hover:bg-white/70"
                  }`}
                />
                <p className="text-sm font-semibold">{item.label}</p>
              </div>
              <p className="text-xs text-white/60 mt-1">{item.description}</p>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
