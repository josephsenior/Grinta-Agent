import { useState, useEffect } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { CheckCircle2, AlertCircle } from "lucide-react";
import { useResetPassword } from "../../hooks/auth/use-password-reset";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const resetPasswordMutation = useResetPassword();
  const [email, setEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  useEffect(() => {
    // Get token and email from URL params if available
    const token = searchParams.get("token");
    const emailParam = searchParams.get("email");
    if (token) setResetToken(token);
    if (emailParam) setEmail(emailParam);
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validate passwords match
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    // Validate password strength
    if (password.length < 8) {
      setError("Password must be at least 8 characters long");
      return;
    }

    if (!email || !resetToken) {
      setError("Email and reset token are required");
      return;
    }

    try {
      await resetPasswordMutation.mutateAsync({
        email,
        reset_token: resetToken,
        new_password: password,
      });
      setIsSuccess(true);
      // Redirect to login after 3 seconds
      setTimeout(() => {
        navigate("/auth/login");
      }, 3000);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message ||
        "Failed to reset password. Please try again.";
      setError(errorMessage);
    }
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black px-4 py-12">
        <Card className="w-full max-w-md glass-modern border-success-500/25">
          <CardHeader className="space-y-1">
            <div className="flex justify-center mb-4">
              <CheckCircle2 className="w-16 h-16 text-success-500" />
            </div>
            <CardTitle className="text-2xl font-bold text-center">
              Password reset successful
            </CardTitle>
            <CardDescription className="text-center">
              Your password has been reset. Redirecting to login...
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center">
              <Link
                to="/auth/login"
                className="text-sm text-brand-500 hover:text-brand-400 hover:underline font-medium"
              >
                Go to login now
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-black px-4 py-12">
      <Card className="w-full max-w-md glass-modern border-brand-500/25">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">
            Reset your password
          </CardTitle>
          <CardDescription className="text-center">
            Enter your new password below
          </CardDescription>
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
                htmlFor="email"
                className="text-sm font-medium text-foreground"
              >
                Email
              </label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={
                  resetPasswordMutation.isPending || !!searchParams.get("email")
                }
                autoComplete="email"
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="resetToken"
                className="text-sm font-medium text-foreground"
              >
                Reset Token
              </label>
              <Input
                id="resetToken"
                type="text"
                placeholder="Enter reset token from email"
                value={resetToken}
                onChange={(e) => setResetToken(e.target.value)}
                required
                disabled={
                  resetPasswordMutation.isPending || !!searchParams.get("token")
                }
              />
              {!searchParams.get("token") && (
                <p className="text-xs text-foreground-secondary">
                  Check your email for the reset token
                </p>
              )}
            </div>

            <div className="space-y-2">
              <label
                htmlFor="password"
                className="text-sm font-medium text-foreground"
              >
                New Password
              </label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={resetPasswordMutation.isPending}
                autoComplete="new-password"
                minLength={8}
              />
              <p className="text-xs text-foreground-secondary">
                At least 8 characters with uppercase, lowercase, and numbers
              </p>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="confirmPassword"
                className="text-sm font-medium text-foreground"
              >
                Confirm New Password
              </label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={resetPasswordMutation.isPending}
                autoComplete="new-password"
                minLength={8}
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={resetPasswordMutation.isPending}
            >
              {resetPasswordMutation.isPending
                ? "Resetting password..."
                : "Reset password"}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-foreground-secondary">
            Remember your password?{" "}
            <Link
              to="/auth/login"
              className="text-brand-500 hover:text-brand-400 hover:underline font-medium"
            >
              Sign in
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
