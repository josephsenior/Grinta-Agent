import { cn } from "#/utils/utils";
import { OptionalTag } from "./optional-tag";

interface SettingsInputProps {
  testId?: string;
  name?: string;
  label: string;
  type: React.HTMLInputTypeAttribute;
  defaultValue?: string;
  value?: string;
  placeholder?: string;
  showOptionalTag?: boolean;
  isDisabled?: boolean;
  startContent?: React.ReactNode;
  className?: string;
  onChange?: (value: string) => void;
  helpText?: string;
  required?: boolean;
  min?: number;
  max?: number;
  step?: number;
  pattern?: string;
  error?: string | null;
}

export function SettingsInput({
  testId,
  name,
  label,
  type,
  defaultValue,
  value,
  placeholder,
  showOptionalTag,
  isDisabled,
  startContent,
  className,
  onChange,
  helpText,
  required,
  min,
  max,
  step,
  pattern,
  error,
}: SettingsInputProps) {
  const errorId = `${name ?? testId}-error`;

  return (
    <label className={cn("flex flex-col gap-2.5", className)}>
      <div className="flex items-center gap-2">
        {startContent}
        <span className="text-sm font-medium text-foreground">{label}</span>
        {showOptionalTag && <OptionalTag />}
      </div>
      <input
        aria-invalid={!!error}
        aria-describedby={error ? errorId : undefined}
        data-testid={testId}
        onChange={(e) => onChange && onChange(e.target.value)}
        name={name}
        disabled={isDisabled}
        type={type}
        defaultValue={defaultValue}
        value={value}
        placeholder={placeholder}
        min={min}
        max={max}
        step={step}
        required={required}
        pattern={pattern}
        className={cn(
          "bg-black/60 backdrop-blur-sm border h-10 w-full rounded-xl px-4 py-2.5 placeholder:text-foreground-tertiary text-foreground transition-all duration-200 focus:outline-none",
          error
            ? "border-danger-500/50 focus:border-danger-500"
            : "border-white/10 focus:border-white/20 hover:border-white/15",
          "disabled:bg-black/30 disabled:border-white/5 disabled:cursor-not-allowed disabled:opacity-50",
        )}
      />

      {error && (
        <p id={errorId} role="alert" className="text-danger-400 text-sm mt-1">
          {error}
        </p>
      )}
      {helpText && (
        <p className="text-xs text-foreground-tertiary mt-1">{helpText}</p>
      )}
    </label>
  );
}
