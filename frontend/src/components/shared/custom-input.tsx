import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";

interface CustomInputProps {
  name: string;
  label: string;
  required?: boolean;
  defaultValue?: string;
  type?: "text" | "password";
}

export function CustomInput({
  name,
  label,
  required,
  defaultValue,
  type = "text",
}: CustomInputProps) {
  const { t } = useTranslation();

  return (
    <label htmlFor={name} className="flex flex-col gap-3 group">
      <span className="text-sm font-medium text-foreground leading-tight">
        {label}
        {required && <span className="text-danger-400 ml-1">*</span>}
        {!required && (
          <span className="text-foreground-secondary ml-2 font-normal">
            {t(I18nKey.CUSTOM_INPUT$OPTIONAL_LABEL)}
          </span>
        )}
      </span>
      <input
        id={name}
        name={name}
        required={required}
        defaultValue={defaultValue}
        type={type}
        className={`
          w-full px-4 py-3 text-sm font-medium rounded-xl
          bg-gradient-to-br from-grey-800/60 to-grey-900/80
          border border-grey-600/40
          text-foreground placeholder:text-foreground-secondary
          backdrop-blur-sm transition-all duration-300 ease-in-out
          focus:outline-none focus:ring-2 focus:ring-primary-500/30
          focus:border-primary-500/50 focus:bg-grey-800/80
          hover:border-grey-500/60 hover:bg-grey-800/70
          disabled:opacity-50 disabled:cursor-not-allowed
        `}
      />
    </label>
  );
}
