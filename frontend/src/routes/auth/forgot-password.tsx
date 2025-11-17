import { useState } from "react";
import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { useForgotPassword } from "../../hooks/auth/use-password-reset";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";

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
      <div className="min-h-screen flex items-center justify-center bg-black px-4 py-12">
        <Card className="w-full max-w-md glass-modern border-brand-500/25">
          <CardHeader className="space-y-1">
            <div className="flex justify-center mb-4">
              <CheckCircle2 className="w-16 h-16 text-success-500" />
            </div>
            <CardTitle className="text-2xl font-bold text-center">
              Check your email
            </CardTitle>
            <CardDescription className="text-center">
              If an account exists with {email}, we've sent password reset
              instructions.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <p className="text-sm text-foreground-secondary text-center">
                Didn't receive the email? Check your spam folder or try again.
              </p>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => {
                  setIsSubmitted(false);
                  setEmail("");
                }}
              >
                Try again
              </Button>
              <div className="text-center">
                <Link
                  to="/auth/login"
                  className="text-sm text-brand-500 hover:text-brand-400 hover:underline"
                >
                  Back to login
                </Link>
              </div>
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
            Forgot password?
          </CardTitle>
          <CardDescription className="text-center">
            Enter your email and we'll send you reset instructions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded-lg bg-danger-500/10 border border-danger-500/30 text-danger-500 text-sm">
                {error}
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
                disabled={forgotPasswordMutation.isPending}
                autoComplete="email"
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={forgotPasswordMutation.isPending}
            >
              {forgotPasswordMutation.isPending
                ? "Sending..."
                : "Send reset link"}
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
