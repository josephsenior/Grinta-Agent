import { Input } from "#/components/ui/input";
import { Tooltip } from "#/components/ui/tooltip";
import { useTranslation } from "react-i18next";
import { CheckCircle, AlertCircle } from "lucide-react";
import { I18nKey } from "#/i18n/declaration";

interface APIKeyInputProps {
  isDisabled: boolean;
  isSet: boolean;
}

export function APIKeyInput({ isDisabled, isSet }: APIKeyInputProps) {
  const { t } = useTranslation();

  return (
    <fieldset data-testid="api-key-input" className="flex flex-col gap-2">
      <Tooltip content={isSet ? "API Key is set" : "API Key is not set"}>
        <label
          htmlFor="api-key"
          className="font-[500] text-basic text-xs flex items-center gap-1 self-start"
        >
          {isSet && <CheckCircle className="text-aqua-500 inline-block" />}
          {!isSet && (
            <AlertCircle className="text-danger-500 inline-block" />
          )}
          {t(I18nKey.API$KEY)}
        </label>
      </Tooltip>
      <Input
        disabled={isDisabled}
        id="api-key"
        name="api-key"
        aria-label={t(I18nKey.API$KEY)}
        type="password"
        defaultValue=""
        className="bg-[#27272A] rounded-md text-sm px-3 py-2.5"
      />
      <p className="text-sm text-basic">
        {t(I18nKey.API$DONT_KNOW_KEY)}{" "}
        <a
          href="https://docs.forge.dev/usage/llms"
          rel="noreferrer noopener"
          target="_blank"
          className="underline underline-offset-2"
        >
          {t(I18nKey.COMMON$CLICK_FOR_INSTRUCTIONS)}
        </a>
      </p>
    </fieldset>
  );
}
