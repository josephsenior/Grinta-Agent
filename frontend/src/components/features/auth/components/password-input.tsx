import { Eye, EyeOff } from "lucide-react";
import { Input } from "../../../ui/input";

interface PasswordInputProps {
  id: string;
  value: string;
  onChange: (value: string) => void;
  showPassword: boolean;
  onToggleShowPassword: () => void;
  disabled?: boolean;
  autoComplete?: string;
  minLength?: number;
  label: string;
}

export function PasswordInput({
  id,
  value,
  onChange,
  showPassword,
  onToggleShowPassword,
  disabled,
  autoComplete,
  minLength,
  label,
}: PasswordInputProps) {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="text-sm font-medium text-foreground">
        {label}
      </label>
      <div className="relative">
        <Input
          id={id}
          type={showPassword ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required
          disabled={disabled}
          autoComplete={autoComplete}
          minLength={minLength}
          className="pr-10"
        />
        <button
          type="button"
          onClick={onToggleShowPassword}
          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/60 hover:text-white"
        >
          {showPassword ? (
            <EyeOff className="h-4 w-4" />
          ) : (
            <Eye className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}
