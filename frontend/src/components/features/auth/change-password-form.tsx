import { useState } from "react";
import { CheckCircle2, AlertCircle, Eye, EyeOff } from "lucide-react";
import { useChangePassword } from "../../../hooks/auth/use-password-reset";
import { Button } from "../../ui/button";
import { Input } from "../../ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../ui/card";
import {
  displaySuccessToast,
  displayErrorToast,
} from "../../../utils/custom-toast-handlers";

interface ChangePasswordFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function ChangePasswordForm({
  onSuccess,
  onCancel,
}: ChangePasswordFormProps) {
  const changePasswordMutation = useChangePassword();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  const validatePassword = (
    password: string,
  ): { valid: boolean; message?: string } => {
    if (password.length < 8) {
      return {
        valid: false,
        message: "Password must be at least 8 characters long",
      };
    }
    if (password.length > 128) {
      return {
        valid: false,
        message: "Password must be less than 128 characters",
      };
    }
    if (!/[a-z]/.test(password)) {
      return {
        valid: false,
        message: "Password must contain at least one lowercase letter",
      };
    }
    if (!/[A-Z]/.test(password)) {
      return {
        valid: false,
        message: "Password must contain at least one uppercase letter",
      };
    }
    if (!/[0-9]/.test(password)) {
      return {
        valid: false,
        message: "Password must contain at least one number",
      };
    }
    return { valid: true };
  };

  const getPasswordStrength = (
    password: string,
  ): { strength: "weak" | "medium" | "strong"; score: number } => {
    let score = 0;
    if (password.length >= 8) score++;
    if (password.length >= 12) score++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^a-zA-Z0-9]/.test(password)) score++;

    if (score <= 2) return { strength: "weak", score };
    if (score <= 4) return { strength: "medium", score };
    return { strength: "strong", score };
  };

  const passwordStrength = getPasswordStrength(newPassword);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate passwords match
    if (newPassword !== confirmPassword) {
      setError("New passwords do not match");
      return;
    }

    // Validate password strength
    const validation = validatePassword(newPassword);
    if (!validation.valid) {
      setError(validation.message || "Password does not meet requirements");
      return;
    }

    try {
      await changePasswordMutation.mutateAsync({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setIsSuccess(true);
      displaySuccessToast("Password changed successfully");
      // Reset form
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => {
        setIsSuccess(false);
        onSuccess?.();
      }, 2000);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message ||
        "Failed to change password. Please check your current password.";
      setError(errorMessage);
      displayErrorToast(errorMessage);
    }
  };

  if (isSuccess) {
    return (
      <Card className="border-success-500/25">
        <CardContent className="pt-6">
          <div className="flex items-center gap-3 text-success-500">
            <CheckCircle2 className="h-5 w-5" />
            <p className="font-medium">Password changed successfully!</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Change Password</CardTitle>
        <CardDescription>Update your account password</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-danger-500/10 border border-danger-500/30 text-danger-500 text-sm flex items-start gap-2">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-2">
            <label
              htmlFor="currentPassword"
              className="text-sm font-medium text-foreground"
            >
              Current Password
            </label>
            <div className="relative">
              <Input
                id="currentPassword"
                type={showCurrentPassword ? "text" : "password"}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                disabled={changePasswordMutation.isPending}
                autoComplete="current-password"
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/60 hover:text-white"
              >
                {showCurrentPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <label
              htmlFor="newPassword"
              className="text-sm font-medium text-foreground"
            >
              New Password
            </label>
            <div className="relative">
              <Input
                id="newPassword"
                type={showNewPassword ? "text" : "password"}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                disabled={changePasswordMutation.isPending}
                autoComplete="new-password"
                minLength={8}
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowNewPassword(!showNewPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/60 hover:text-white"
              >
                {showNewPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {newPassword && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        passwordStrength.strength === "weak"
                          ? "bg-danger-500 w-1/3"
                          : passwordStrength.strength === "medium"
                            ? "bg-warning-500 w-2/3"
                            : "bg-success-500 w-full"
                      }`}
                    />
                  </div>
                  <span
                    className={`text-xs font-medium ${
                      passwordStrength.strength === "weak"
                        ? "text-danger-500"
                        : passwordStrength.strength === "medium"
                          ? "text-warning-500"
                          : "text-success-500"
                    }`}
                  >
                    {passwordStrength.strength.charAt(0).toUpperCase() +
                      passwordStrength.strength.slice(1)}
                  </span>
                </div>
                <div className="text-xs text-white/60 space-y-1">
                  <p
                    className={
                      newPassword.length >= 8 ? "text-success-500" : ""
                    }
                  >
                    {newPassword.length >= 8 ? "✓" : "○"} At least 8 characters
                  </p>
                  <p
                    className={
                      /[a-z]/.test(newPassword) && /[A-Z]/.test(newPassword)
                        ? "text-success-500"
                        : ""
                    }
                  >
                    {/[a-z]/.test(newPassword) && /[A-Z]/.test(newPassword)
                      ? "✓"
                      : "○"}{" "}
                    Uppercase and lowercase letters
                  </p>
                  <p
                    className={
                      /[0-9]/.test(newPassword) ? "text-success-500" : ""
                    }
                  >
                    {/[0-9]/.test(newPassword) ? "✓" : "○"} At least one number
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-2">
            <label
              htmlFor="confirmPassword"
              className="text-sm font-medium text-foreground"
            >
              Confirm New Password
            </label>
            <div className="relative">
              <Input
                id="confirmPassword"
                type={showConfirmPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={changePasswordMutation.isPending}
                autoComplete="new-password"
                minLength={8}
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/60 hover:text-white"
              >
                {showConfirmPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {confirmPassword && newPassword && (
              <p
                className={`text-xs ${
                  confirmPassword === newPassword
                    ? "text-success-500"
                    : "text-danger-500"
                }`}
              >
                {confirmPassword === newPassword
                  ? "✓ Passwords match"
                  : "✗ Passwords do not match"}
              </p>
            )}
          </div>

          <div className="flex items-center justify-end gap-3 pt-4">
            {onCancel && (
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                disabled={changePasswordMutation.isPending}
              >
                Cancel
              </Button>
            )}
            <Button type="submit" disabled={changePasswordMutation.isPending}>
              {changePasswordMutation.isPending
                ? "Changing password..."
                : "Change Password"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
