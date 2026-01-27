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
  autoComplete?: string;
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
  autoComplete,
}: SettingsInputProps) {
  const errorId = `${name ?? testId}-error`;

  return (
    <label className={cn("flex flex-col gap-2.5", className)}>
      <div className="flex items-center gap-2">
        {startContent}
        <span className="text-sm font-medium text-[var(--text-primary)]">
          {label}
        </span>
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
        autoComplete={autoComplete}
        className={cn(
          "w-full h-12 rounded-lg border px-4 py-3 text-sm",
          "bg-[var(--bg-input)] border-[var(--border-primary)]",
          "text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)]",
          "transition-all duration-200",
          "focus:outline-none focus:border-[var(--border-accent)] focus:ring-2 focus:ring-[rgba(139,92,246,0.2)]",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          error ? "border-danger-500/50 focus:border-danger-500" : "",
        )}
      />

      {error && (
        <p
          id={errorId}
          role="alert"
          className="p-3 rounded-lg bg-danger-500/10 border border-danger-500/30 text-danger-500 text-sm mt-1"
        >
          {error}
        </p>
      )}
      {helpText && (
        <p className="text-xs text-[var(--text-tertiary)] mt-1">{helpText}</p>
      )}
    </label>
  );
}
