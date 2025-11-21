import { AlertCircle } from "lucide-react";
import { PasswordInput } from "../../components/password-input";
import { PasswordStrengthIndicator } from "../../components/password-strength-indicator";
import { PasswordRequirements } from "../../components/password-requirements";
import { usePasswordStrength } from "../../hooks/use-password-strength";

interface PasswordFormFieldsProps {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
  showCurrentPassword: boolean;
  showNewPassword: boolean;
  showConfirmPassword: boolean;
  onCurrentPasswordChange: (value: string) => void;
  onNewPasswordChange: (value: string) => void;
  onConfirmPasswordChange: (value: string) => void;
  onToggleShowCurrentPassword: () => void;
  onToggleShowNewPassword: () => void;
  onToggleShowConfirmPassword: () => void;
  disabled: boolean;
  error: string | null;
}

export function PasswordFormFields({
  currentPassword,
  newPassword,
  confirmPassword,
  showCurrentPassword,
  showNewPassword,
  showConfirmPassword,
  onCurrentPasswordChange,
  onNewPasswordChange,
  onConfirmPasswordChange,
  onToggleShowCurrentPassword,
  onToggleShowNewPassword,
  onToggleShowConfirmPassword,
  disabled,
  error,
}: PasswordFormFieldsProps) {
  const { getPasswordStrength } = usePasswordStrength();
  const passwordStrength = getPasswordStrength(newPassword);
  const passwordsMatch =
    confirmPassword && newPassword && confirmPassword === newPassword;

  return (
    <>
      {error && (
        <div className="p-3 rounded-lg bg-danger-500/10 border border-danger-500/30 text-danger-500 text-sm flex items-start gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <PasswordInput
        id="currentPassword"
        value={currentPassword}
        onChange={onCurrentPasswordChange}
        showPassword={showCurrentPassword}
        onToggleShowPassword={onToggleShowCurrentPassword}
        disabled={disabled}
        autoComplete="current-password"
        label="Current Password"
      />

      <div className="space-y-2">
        <PasswordInput
          id="newPassword"
          value={newPassword}
          onChange={onNewPasswordChange}
          showPassword={showNewPassword}
          onToggleShowPassword={onToggleShowNewPassword}
          disabled={disabled}
          autoComplete="new-password"
          minLength={8}
          label="New Password"
        />
        {newPassword && (
          <div className="space-y-2">
            <PasswordStrengthIndicator strength={passwordStrength.strength} />
            <PasswordRequirements password={newPassword} />
          </div>
        )}
      </div>

      <div className="space-y-2">
        <PasswordInput
          id="confirmPassword"
          value={confirmPassword}
          onChange={onConfirmPasswordChange}
          showPassword={showConfirmPassword}
          onToggleShowPassword={onToggleShowConfirmPassword}
          disabled={disabled}
          autoComplete="new-password"
          minLength={8}
          label="Confirm New Password"
        />
        {confirmPassword && newPassword && (
          <p
            className={`text-xs ${
              passwordsMatch ? "text-success-500" : "text-danger-500"
            }`}
          >
            {passwordsMatch ? "✓ Passwords match" : "✗ Passwords do not match"}
          </p>
        )}
      </div>
    </>
  );
}
