import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { useAIConfigOptions } from "#/hooks/query/use-ai-config-options";
import { I18nKey } from "#/i18n/declaration";
import { LoadingSpinner } from "../../loading-spinner";
import { ModalBackdrop } from "../modal-backdrop";
import { SettingsForm } from "./settings-form";
import { Settings } from "#/types/settings";
import { Card, CardContent, CardHeader } from "#/components/ui/card";
import { Separator } from "#/components/ui/separator";
import { DEFAULT_SETTINGS } from "#/services/settings";

interface SettingsModalProps {
  settings?: Settings;
  onClose: () => void;
}

export function SettingsModal({ onClose, settings }: SettingsModalProps) {
  const aiConfigOptions = useAIConfigOptions();
  const { t } = useTranslation();

  return (
    <ModalBackdrop>
      <Card
        data-testid="ai-config-modal"
        className="bg-base-secondary min-w-[320px] sm:min-w-[384px] m-2 sm:m-4 rounded-xl border border-border shadow-none backdrop-blur-0 lavender-gradient-border lavender-gradient-border-hover max-w-[95vw] sm:max-w-none"
      >
        <CardHeader className="px-4 sm:px-6 pt-4 sm:pt-6 pb-3">
          <span className="section-heading text-sm sm:text-base">
            {t(I18nKey.AI_SETTINGS$TITLE)}
          </span>
          <p className="text-xs text-basic leading-relaxed">
            {t(I18nKey.SETTINGS$DESCRIPTION)}{" "}
            {t(I18nKey.SETTINGS$FOR_OTHER_OPTIONS)}
            <Link
              data-testid="advanced-settings-link"
              to="/settings"
              className="underline underline-offset-2 text-white"
            >
              {t(I18nKey.SETTINGS$SEE_ADVANCED_SETTINGS)}
            </Link>
          </p>
          <Separator className="mt-3 opacity-50" />
        </CardHeader>
        <CardContent className="px-4 sm:px-6 pb-4 sm:pb-6">
          {aiConfigOptions.error && (
            <p className="text-danger text-xs">
              {aiConfigOptions.error.message}
            </p>
          )}

          {aiConfigOptions.isLoading && (
            <div className="flex justify-center">
              <LoadingSpinner size="small" />
            </div>
          )}
          {aiConfigOptions.data && (
            <SettingsForm
              settings={settings || DEFAULT_SETTINGS}
              models={aiConfigOptions.data?.models}
              onClose={onClose}
            />
          )}
        </CardContent>
      </Card>
    </ModalBackdrop>
  );
}
