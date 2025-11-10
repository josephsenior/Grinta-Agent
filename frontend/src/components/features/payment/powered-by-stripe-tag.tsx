import { useTranslation } from "react-i18next";
import type { ComponentType, SVGProps } from "react";
import { I18nKey } from "#/i18n/declaration";
import stripeLogo from "#/assets/stripe.svg";

export function PoweredByStripeTag() {
  const { t } = useTranslation();

  const renderStripeLogo = () => {
    if (typeof stripeLogo === "string") {
      return <img src={stripeLogo} alt="Stripe" className="h-8" />;
    }

    const StripeLogoComponent = stripeLogo as unknown as ComponentType<
      SVGProps<SVGSVGElement>
    >;
    return (
      <StripeLogoComponent role="img" aria-label="Stripe" className="h-8" />
    );
  };

  return (
    <div className="flex flex-row items-center">
      <span className="text-medium font-semi-bold">
        {t(I18nKey.BILLING$POWERED_BY)}
      </span>
      {renderStripeLogo()}
    </div>
  );
}
