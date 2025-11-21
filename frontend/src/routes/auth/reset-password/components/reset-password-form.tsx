import { Link } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { FormField } from "./form-field";
import { SuccessView } from "./success-view";

interface ResetPasswordFormProps {
  email: string;
  resetToken: string;
  password: string;
  confirmPassword: string;
  error: string | null;
  errors: {
    email: string | null;
    resetToken: string | null;
    password: string | null;
    confirmPassword: string | null;
  };
  isSubmitting: boolean;
  hasTokenFromUrl: boolean;
  hasEmailFromUrl: boolean;
  onEmailChange: (value: string) => void;
  onResetTokenChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onConfirmPasswordChange: (value: string) => void;
  onBlur: (
    field: "email" | "resetToken" | "password" | "confirmPassword",
  ) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export function ResetPasswordForm({
  email,
  resetToken,
  password,
  confirmPassword,
  error,
  errors,
  isSubmitting,
  hasTokenFromUrl,
  hasEmailFromUrl,
  onEmailChange,
  onResetTokenChange,
  onPasswordChange,
  onConfirmPasswordChange,
  onBlur,
  onSubmit,
}: ResetPasswordFormProps) {
  return (
    <form onSubmit={onSubmit} noValidate className="w-full space-y-6">
      {error && (
        <div className="p-3 rounded-lg bg-danger-500/10 border border-danger-500/30 text-danger-500 text-sm flex items-start gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      <FormField
        id="email"
        label="Email"
        type="text"
        placeholder="you@example.com"
        value={email}
        onChange={(e) => onEmailChange(e.target.value)}
        onBlur={() => onBlur("email")}
        error={errors.email}
        disabled={isSubmitting || hasEmailFromUrl}
        autoComplete="email"
      />

      <FormField
        id="resetToken"
        label="Reset Token"
        type="text"
        placeholder="Enter reset token from email"
        value={resetToken}
        onChange={(e) => onResetTokenChange(e.target.value)}
        onBlur={() => onBlur("resetToken")}
        error={errors.resetToken}
        disabled={isSubmitting || hasTokenFromUrl}
        helperText={
          !errors.resetToken && !hasTokenFromUrl
            ? "Check your email for the reset token"
            : undefined
        }
      />

      <FormField
        id="password"
        label="New Password"
        type="password"
        placeholder="••••••••"
        value={password}
        onChange={(e) => onPasswordChange(e.target.value)}
        onBlur={() => onBlur("password")}
        error={errors.password}
        disabled={isSubmitting}
        autoComplete="new-password"
        helperText={
          !errors.password
            ? "At least 8 characters with uppercase, lowercase, and numbers"
            : undefined
        }
      />

      <FormField
        id="confirmPassword"
        label="Confirm New Password"
        type="password"
        placeholder="••••••••"
        value={confirmPassword}
        onChange={(e) => onConfirmPasswordChange(e.target.value)}
        onBlur={() => onBlur("confirmPassword")}
        error={errors.confirmPassword}
        disabled={isSubmitting}
        autoComplete="new-password"
      />

      <button
        type="submit"
        className="w-full h-12 rounded-lg bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed] text-white font-medium text-sm transition-all duration-150 hover:brightness-110 active:brightness-95 disabled:opacity-50 disabled:cursor-not-allowed"
        disabled={isSubmitting}
      >
        {isSubmitting ? "Resetting password..." : "Reset password"}
      </button>

      <div className="pt-2 text-sm text-[var(--text-tertiary)] text-center">
        <span className="block sm:inline">Remember your password? </span>
        <Link
          to="/auth/login"
          className="text-[var(--text-accent)] hover:text-[#a78bfa] hover:underline font-medium"
        >
          Sign in
        </Link>
      </div>
    </form>
  );
}

export { SuccessView };
