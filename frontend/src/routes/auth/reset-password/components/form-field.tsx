interface FormFieldProps {
  id: string;
  label: string;
  type: string;
  placeholder: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onBlur: () => void;
  error: string | null;
  disabled: boolean;
  autoComplete?: string;
  helperText?: string;
}

export function FormField({
  id,
  label,
  type,
  placeholder,
  value,
  onChange,
  onBlur,
  error,
  disabled,
  autoComplete,
  helperText,
}: FormFieldProps) {
  return (
    <div className="space-y-2.5">
      <label
        htmlFor={id}
        className="text-sm font-medium text-[var(--text-primary)] block"
      >
        {label}
      </label>
      <input
        id={id}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        disabled={disabled}
        autoComplete={autoComplete}
        className={`w-full h-12 rounded-lg border bg-[var(--bg-input)] px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] transition-all duration-200 focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed ${
          error
            ? "border-danger-500/50 focus:border-danger-500 focus:ring-danger-500/20"
            : "border-[var(--border-primary)] focus:border-[var(--border-accent)] focus:ring-[rgba(139,92,246,0.2)]"
        }`}
      />
      {error && <p className="text-sm text-danger-500 mt-1">{error}</p>}
      {!error && helperText && (
        <p className="text-xs text-[var(--text-tertiary)] mt-1.5">
          {helperText}
        </p>
      )}
    </div>
  );
}
