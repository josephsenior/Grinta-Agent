import { useTranslation } from "react-i18next";
import { TooltipButton } from "./tooltip-button";

export function ForgeLogoButton() {
  const { t } = useTranslation();

  return (
    <TooltipButton
      tooltip={t("tooltip.forge_pro_ai_engineer", {
        defaultValue: "Forge Pro AI Engineer",
      })}
      ariaLabel={t("app.name", { defaultValue: `Forge Pro AI Logo` })}
      navLinkTo="/"
    >
      {/* Inline SVG placeholder to avoid resolving static assets in tests */}
      <svg width={24} height={24} viewBox="0 0 24 24" aria-hidden="true">
        <circle cx="12" cy="12" r="10" fill="#111827" />
        <circle cx="12" cy="12" r="6" fill="#FBBF24" />
      </svg>
    </TooltipButton>
  );
}
