import { useMemo } from "react";
import type { GetConfigResponse } from "#/api/forge.types";
import type { Settings } from "#/types/settings";

interface SettingsSummaryHeaderProps {
  config?: GetConfigResponse;
  settings?: Settings | null;
  hasPro?: boolean;
}

const summaryItems = (
  config?: GetConfigResponse,
  settings?: Settings | null,
  hasPro?: boolean,
) => {
  const workspaceMode = config?.APP_MODE === "saas" ? "SaaS" : "Self-hosted";
  const plan = hasPro ? "Pro beta" : "Free tier";
  const llmModel = settings?.LLM_MODEL || "Not configured";
  const automation =
    settings?.ENABLE_DEFAULT_CONDENSER && settings?.LLM_API_KEY_SET
      ? "Hybrid memory on"
      : "Manual";

  return [
    { label: "Workspace mode", value: workspaceMode },
    { label: "Plan", value: plan },
    { label: "LLM", value: llmModel },
    { label: "Automation", value: automation },
  ];
};

export function SettingsSummaryHeader({
  config,
  settings,
  hasPro,
}: SettingsSummaryHeaderProps) {
  const items = useMemo(
    () => summaryItems(config, settings, hasPro),
    [config, settings, hasPro],
  );

  return (
    <section
      aria-label="Workspace summary"
      className="rounded-3xl border border-white/10 bg-black/70 px-6 py-5 shadow-[0_30px_80px_rgba(0,0,0,0.45)]"
    >
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item) => (
          <div key={item.label}>
            <p className="text-xs uppercase tracking-[0.3em] text-white/40">
              {item.label}
            </p>
            <p className="mt-1 text-base font-semibold text-white truncate">
              {item.value}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
