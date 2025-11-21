import { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { useForgotPassword } from "#/hooks/auth/use-password-reset";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "#/components/ui/card";

export default function ForgotPasswordPage() {
  const forgotPasswordMutation = useForgotPassword();
  const [email, setEmail] = useState("");
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      await forgotPasswordMutation.mutateAsync({ email });
      setIsSubmitted(true);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message ||
        "Failed to send reset email. Please try again.";
      setError(errorMessage);
    }
  };

  if (isSubmitted) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-[var(--bg-primary)] px-4 sm:px-6 py-12">
        <div className="w-full max-w-[440px]">
          <Card className="bg-transparent border-0 shadow-none">
            <CardHeader className="space-y-4 px-0 pb-8">
              <div className="mb-2 flex justify-center">
                <CheckCircle2 className="w-16 h-16 text-success-500" />
              </div>
              <CardTitle className="text-3xl md:text-4xl font-bold text-center text-[var(--text-primary)] leading-tight">
                Check your email
              </CardTitle>
              <CardDescription className="text-center text-[var(--text-tertiary)] text-sm leading-relaxed">
                If an account exists with {email}, we've sent password reset
                instructions.
              </CardDescription>
            </CardHeader>
            <CardContent className="px-0 pt-0">
              <div className="w-full space-y-5 text-center">
                <p className="text-sm text-[var(--text-tertiary)]">
                  Didn't receive the email? Check your spam folder or try again.
                </p>
                <button
                  type="button"
                  className="w-full h-12 rounded-lg border border-[var(--border-primary)] bg-transparent text-[var(--text-primary)] font-medium text-sm transition-all duration-150 hover:bg-[var(--bg-elevated)] hover:border-[var(--border-accent)] disabled:opacity-50 disabled:cursor-not-allowed"
                  onClick={() => {
                    setIsSubmitted(false);
                    setEmail("");
                  }}
                >
                  Try again
                </button>
                <div className="pt-2">
                  <Link
                    to="/auth/login"
                    className="text-sm text-brand-500 hover:text-brand-400 hover:underline font-medium"
                  >
                    Back to login
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[var(--bg-primary)] px-4 sm:px-6 py-12">
      <div className="w-full max-w-[440px]">
        <Card className="bg-transparent border-0 shadow-none">
          <CardHeader className="space-y-4 px-0 pb-8">
            <CardTitle className="text-3xl md:text-4xl font-bold text-center text-[var(--text-primary)] leading-tight">
              Forgot password?
            </CardTitle>
            <CardDescription className="text-center text-[var(--text-tertiary)] text-sm leading-relaxed">
              Enter your email and we'll send you reset instructions
            </CardDescription>
          </CardHeader>
          <CardContent className="px-0 pt-0">
            <form onSubmit={handleSubmit} className="w-full space-y-6">
              {error && (
                <div className="p-3 rounded-lg bg-danger-500/10 border border-danger-500/30 text-danger-500 text-sm">
                  {error}
                </div>
              )}

              <div className="space-y-2.5">
                <label
                  htmlFor="email"
                  className="text-sm font-medium text-[var(--text-primary)] block"
                >
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={forgotPasswordMutation.isPending}
                  autoComplete="email"
                  className="w-full h-12 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-input)] px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] transition-all duration-200 focus:outline-none focus:border-[var(--border-accent)] focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>

              <button
                type="submit"
                className="w-full h-12 rounded-lg bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed] text-white font-medium text-sm transition-all duration-150 hover:brightness-110 active:brightness-95 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={forgotPasswordMutation.isPending}
              >
                {forgotPasswordMutation.isPending
                  ? "Sending..."
                  : "Send reset link"}
              </button>

              <div className="pt-2 text-sm text-[var(--text-tertiary)] text-center">
                <span className="block sm:inline">
                  Remember your password?{" "}
                </span>
                <Link
                  to="/auth/login"
                  className="text-[var(--text-accent)] hover:text-[#a78bfa] hover:underline font-medium"
                >
                  Sign in
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
