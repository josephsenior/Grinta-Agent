import { useState, useEffect } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { Github } from "lucide-react";
import { useRegister } from "../../hooks/auth/use-register";
import { useAuth } from "../../context/auth-context";
import { authApi } from "../../api/auth";
import { tokenStorage } from "../../utils/auth/token-storage";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { error: authError, clearError } = useAuth();
  const registerMutation = useRegister();
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [oauthLoading, setOauthLoading] = useState<string | null>(null);

  // Handle OAuth callback token
  useEffect(() => {
    const token = searchParams.get("token");
    const oauthError = searchParams.get("error");

    if (oauthError) {
      let errorMessage = "OAuth authentication error. Please try again.";
      if (oauthError === "oauth_failed") {
        errorMessage = "OAuth authentication failed. Please try again.";
      } else if (oauthError === "no_email") {
        errorMessage = "Could not retrieve email from OAuth provider.";
      }
      setError(errorMessage);
      // Clean URL
      navigate("/auth/register", { replace: true });
    } else if (token) {
      // Store token and fetch user
      tokenStorage.setToken(token);
      // Fetch user and redirect
      authApi
        .getCurrentUser()
        .then((user) => {
          tokenStorage.setUser(user);
          navigate("/dashboard", { replace: true });
        })
        .catch(() => {
          setError("Failed to authenticate. Please try again.");
          navigate("/auth/register", { replace: true });
        });
    }
  }, [searchParams, navigate]);

  const handleOAuth = async (provider: "github" | "google") => {
    try {
      setOauthLoading(provider);
      setError(null);
      clearError();

      const redirectUri = `${window.location.origin}/auth/register`;
      const authUrl = await authApi.getOAuthUrl(provider, redirectUri);
      window.location.href = authUrl;
    } catch (err: any) {
      setOauthLoading(null);
      const errorMessage =
        err.response?.data?.message ||
        `Failed to initiate ${provider} authentication. Please try again.`;
      setError(errorMessage);
    }
  };

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
    <div className="min-h-screen w-full flex items-center justify-center bg-[var(--bg-primary)] px-4 sm:px-6 py-12">
      <div className="w-full max-w-[440px]">
        <Card className="bg-transparent border-0 shadow-none">
          <CardHeader className="space-y-4 px-0 pb-8">
            <CardTitle className="text-3xl md:text-4xl font-bold text-center text-[var(--text-primary)] leading-tight">
              Create an account
            </CardTitle>
            <CardDescription className="text-center text-[var(--text-tertiary)] text-sm leading-relaxed">
              Sign up to get started with Forge
            </CardDescription>
          </CardHeader>
          <CardContent className="px-0 pt-0">
            <div className="w-full space-y-6">
              {error && (
                <div className="p-3 rounded-lg bg-danger-500/10 border border-danger-500/30 text-danger-500 text-sm">
                  {error}
                </div>
              )}

              {/* OAuth Buttons */}
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={() => handleOAuth("github")}
                  disabled={oauthLoading !== null || registerMutation.isPending}
                  className="w-full h-12 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-input)] text-[var(--text-primary)] font-medium text-sm transition-all duration-150 hover:bg-[var(--bg-elevated)] hover:border-[var(--border-accent)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
                >
                  {oauthLoading === "github" ? (
                    <>
                      <div className="w-4 h-4 border-2 border-[var(--text-primary)]/30 border-t-[var(--text-primary)] rounded-full animate-spin" />
                      <span>Connecting...</span>
                    </>
                  ) : (
                    <>
                      <Github className="w-5 h-5" />
                      <span>Continue with GitHub</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => handleOAuth("google")}
                  disabled={oauthLoading !== null || registerMutation.isPending}
                  className="w-full h-12 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-input)] text-[var(--text-primary)] font-medium text-sm transition-all duration-150 hover:bg-[var(--bg-elevated)] hover:border-[var(--border-accent)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
                >
                  {oauthLoading === "google" ? (
                    <>
                      <div className="w-4 h-4 border-2 border-[var(--text-primary)]/30 border-t-[var(--text-primary)] rounded-full animate-spin" />
                      <span>Connecting...</span>
                    </>
                  ) : (
                    <>
                      <svg
                        className="w-5 h-5"
                        viewBox="0 0 24 24"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <path
                          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                          fill="#4285F4"
                        />
                        <path
                          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                          fill="#34A853"
                        />
                        <path
                          d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                          fill="#FBBC05"
                        />
                        <path
                          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                          fill="#EA4335"
                        />
                      </svg>
                      <span>Continue with Google</span>
                    </>
                  )}
                </button>
              </div>

              {/* Divider */}
              <div className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[var(--border-primary)]" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-[var(--bg-primary)] px-3 text-[var(--text-tertiary)]">
                    Or continue with
                  </span>
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
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
                    disabled={registerMutation.isPending}
                    autoComplete="email"
                    className="w-full h-12 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-input)] px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] transition-all duration-200 focus:outline-none focus:border-[var(--border-accent)] focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                </div>

                <div className="space-y-2.5">
                  <label
                    htmlFor="username"
                    className="text-sm font-medium text-[var(--text-primary)] block"
                  >
                    Username
                  </label>
                  <input
                    id="username"
                    type="text"
                    placeholder="johndoe"
                    value={username}
                    onChange={(e) =>
                      setUsername(
                        e.target.value
                          .toLowerCase()
                          .replace(/[^a-z0-9_-]/g, ""),
                      )
                    }
                    required
                    disabled={registerMutation.isPending}
                    autoComplete="username"
                    minLength={3}
                    maxLength={50}
                    className="w-full h-12 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-input)] px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] transition-all duration-200 focus:outline-none focus:border-[var(--border-accent)] focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <p className="text-xs text-[var(--text-tertiary)] mt-1.5">
                    Letters, numbers, underscores, and hyphens only
                  </p>
                </div>

                <div className="space-y-2.5">
                  <label
                    htmlFor="password"
                    className="text-sm font-medium text-[var(--text-primary)] block"
                  >
                    Password
                  </label>
                  <input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={registerMutation.isPending}
                    autoComplete="new-password"
                    minLength={8}
                    className="w-full h-12 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-input)] px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] transition-all duration-200 focus:outline-none focus:border-[var(--border-accent)] focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                  <p className="text-xs text-[var(--text-tertiary)] mt-1.5">
                    At least 8 characters with uppercase, lowercase, and numbers
                  </p>
                </div>

                <div className="space-y-2.5">
                  <label
                    htmlFor="confirmPassword"
                    className="text-sm font-medium text-[var(--text-primary)] block"
                  >
                    Confirm Password
                  </label>
                  <input
                    id="confirmPassword"
                    type="password"
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    disabled={registerMutation.isPending}
                    autoComplete="new-password"
                    minLength={8}
                    className="w-full h-12 rounded-lg border border-[var(--border-primary)] bg-[var(--bg-input)] px-4 py-3 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] transition-all duration-200 focus:outline-none focus:border-[var(--border-accent)] focus:ring-2 focus:ring-[rgba(139,92,246,0.2)] disabled:opacity-50 disabled:cursor-not-allowed"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full h-12 rounded-lg bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed] text-white font-medium text-sm transition-all duration-150 hover:brightness-110 active:brightness-95 disabled:opacity-50 disabled:cursor-not-allowed"
                  disabled={registerMutation.isPending}
                >
                  {registerMutation.isPending
                    ? "Creating account..."
                    : "Create account"}
                </button>
              </form>

              <div className="pt-2 text-sm text-[var(--text-tertiary)] text-center">
                <span className="block sm:inline">
                  Already have an account?{" "}
                </span>
                <Link
                  to="/auth/login"
                  className="text-[var(--text-accent)] hover:text-[#a78bfa] hover:underline font-medium"
                >
                  Sign in
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
