import { useState, useEffect } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { useLogin } from "../../hooks/auth/use-login";
import { useAuth } from "../../context/auth-context";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
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
    <div className="min-h-screen flex items-center justify-center bg-black px-4 py-12">
      <Card className="w-full max-w-md glass-modern border-brand-500/25">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">
            Welcome back
          </CardTitle>
          <CardDescription className="text-center">
            Sign in to your Forge account
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
                disabled={loginMutation.isPending}
                autoComplete="email"
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label
                  htmlFor="password"
                  className="text-sm font-medium text-foreground"
                >
                  Password
                </label>
                <Link
                  to="/auth/forgot-password"
                  className="text-sm text-brand-500 hover:text-brand-400 hover:underline"
                >
                  Forgot password?
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loginMutation.isPending}
                autoComplete="current-password"
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={loginMutation.isPending}
            >
              {loginMutation.isPending ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-foreground-secondary">
            Don't have an account?{" "}
            <Link
              to="/auth/register"
              className="text-brand-500 hover:text-brand-400 hover:underline font-medium"
            >
              Sign up
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
