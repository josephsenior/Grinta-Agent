import { useState, useEffect } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { useLogin } from "../../hooks/auth/use-login";
import { useAuth } from "../../context/auth-context";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";

export default function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { error: authError, clearError, isAuthenticated } = useAuth();
  const loginMutation = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const redirectTo = searchParams.get("redirect") || "/dashboard";
      navigate(redirectTo);
    }
  }, [isAuthenticated, navigate, searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    clearError();

    try {
      await loginMutation.mutateAsync({ email, password });
      // Redirect to dashboard or previous page
      const redirectTo = searchParams.get("redirect") || "/dashboard";
      navigate(redirectTo);
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message ||
        authError ||
        "Login failed. Please try again.";
      setError(errorMessage);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[var(--bg-primary)] px-4 sm:px-6 py-12">
      <div className="w-full max-w-[440px]">
        <Card className="bg-transparent border-0 shadow-none">
          <CardHeader className="space-y-4 px-0 pb-8">
            <CardTitle className="text-3xl md:text-4xl font-bold text-center text-[var(--text-primary)] leading-tight">
              Welcome back
            </CardTitle>
            <CardDescription className="text-center text-[var(--text-tertiary)] text-sm leading-relaxed">
              Sign in to your Forge account
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
                  disabled={loginMutation.isPending}
                  autoComplete="email"
                  className="w-full h-12 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-input)] px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] transition-all duration-200 focus:outline-none focus:border-[var(--border-accent)] focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>

              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="password"
                    className="text-sm font-medium text-[var(--text-primary)] block"
                  >
                    Password
                  </label>
                  <Link
                    to="/auth/forgot-password"
                    className="text-sm text-[var(--text-accent)] hover:text-[#a78bfa] hover:underline whitespace-nowrap ml-4"
                  >
                    Forgot password?
                  </Link>
                </div>
                <input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loginMutation.isPending}
                  autoComplete="current-password"
                  className="w-full h-12 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-input)] px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] transition-all duration-200 focus:outline-none focus:border-[var(--border-accent)] focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] disabled:opacity-50 disabled:cursor-not-allowed"
                />
              </div>

              <button
                type="submit"
                className="w-full h-12 rounded-lg bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed] text-white font-medium text-sm transition-all duration-150 hover:brightness-110 active:brightness-95 disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={loginMutation.isPending}
              >
                {loginMutation.isPending ? "Signing in..." : "Sign in"}
              </button>

              <div className="pt-2 text-sm text-[var(--text-tertiary)] text-center">
                <span className="block sm:inline">Don't have an account? </span>
                <Link
                  to="/auth/register"
                  className="text-[var(--text-accent)] hover:text-[#a78bfa] hover:underline font-medium"
                >
                  Sign up
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
