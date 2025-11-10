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
    <label className={cn("flex flex-col gap-2.5 w-fit", className)}>
      <div className="flex items-center gap-2">
        {startContent}
        <span className="text-sm">{label}</span>
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
          "bg-background-secondary backdrop-blur-xl border border-border h-10 w-full rounded-xl p-3 placeholder:italic placeholder:text-foreground-secondary text-foreground transition-all duration-200 focus:border-brand-500/50 focus:bg-brand-500/5 focus:shadow-lg focus:shadow-brand-500/10 hover:border-brand-500/30 hover:bg-brand-500/3",
          error ? "border-danger-500/80 bg-danger-500/5" : "",
          "disabled:bg-background-tertiary disabled:border-border disabled:cursor-not-allowed disabled:opacity-50",
        )}
      />

      {error && (
        <p id={errorId} role="alert" className="text-danger-500 text-sm mt-1">
          {error}
        </p>
      )}
      {helpText && <p className="text-xs text-neutral-500 mt-1">{helpText}</p>}
    </label>
  );
}
