import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useRegister } from "../../hooks/auth/use-register";
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

export default function RegisterPage() {
  const navigate = useNavigate();
  const { error: authError, clearError } = useAuth();
  const registerMutation = useRegister();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    clearError();

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

    try {
      await registerMutation.mutateAsync({ email, username, password });
      // Redirect to dashboard after successful registration
      navigate("/dashboard");
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message ||
        authError ||
        "Registration failed. Please try again.";
      setError(errorMessage);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black px-4 py-12">
      <Card className="w-full max-w-md glass-modern border-brand-500/25">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">
            Create an account
          </CardTitle>
          <CardDescription className="text-center">
            Sign up to get started with Forge
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
                disabled={registerMutation.isPending}
                autoComplete="email"
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="username"
                className="text-sm font-medium text-foreground"
              >
                Username
              </label>
              <Input
                id="username"
                type="text"
                placeholder="johndoe"
                value={username}
                onChange={(e) =>
                  setUsername(
                    e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""),
                  )
                }
                required
                disabled={registerMutation.isPending}
                autoComplete="username"
                minLength={3}
                maxLength={50}
              />
              <p className="text-xs text-foreground-secondary">
                Letters, numbers, underscores, and hyphens only
              </p>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="password"
                className="text-sm font-medium text-foreground"
              >
                Password
              </label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={registerMutation.isPending}
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
                Confirm Password
              </label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={registerMutation.isPending}
                autoComplete="new-password"
                minLength={8}
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={registerMutation.isPending}
            >
              {registerMutation.isPending
                ? "Creating account..."
                : "Create account"}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-foreground-secondary">
            Already have an account?{" "}
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
