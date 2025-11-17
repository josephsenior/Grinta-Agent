import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Save, CheckCircle2, XCircle } from "lucide-react";
import React, { useState, useEffect } from "react";
import { useUser, useUpdateUser } from "../../../hooks/query/use-users";
import { useAuth } from "../../../context/auth-context";
import { AuthGuard } from "../../../components/features/auth/auth-guard";
import { isAdmin } from "../../../utils/auth/permissions";
import { Button } from "../../../components/ui/button";
import { Input } from "../../../components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "../../../components/ui/card";
import { AppLayout } from "../../../components/layout/AppLayout";
import { PageHero } from "../../../components/layout/PageHero";
import AnimatedBackground from "../../../components/landing/AnimatedBackground";
import {
  displaySuccessToast,
  displayErrorToast,
} from "../../../utils/custom-toast-handlers";

export default function EditUserPage() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const { data: user, isLoading, error } = useUser(userId || "");
  const updateUserMutation = useUpdateUser();

  const [formData, setFormData] = useState({
    username: "",
    email: "",
    role: "user" as "admin" | "user" | "service",
    is_active: true,
    email_verified: false,
  });

  // Update form when user data changes
  useEffect(() => {
    if (user) {
      setFormData({
        username: user.username || "",
        email: user.email || "",
        role: user.role,
        is_active: user.is_active,
        email_verified: user.email_verified,
      });
    }
  }, [user]);

  if (!isAdmin(currentUser)) {
    return (
      <AuthGuard requireRole="admin">
        <div className="min-h-screen flex items-center justify-center bg-black">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Access Denied</CardTitle>
            </CardHeader>
            <CardContent>
              <p>You need admin privileges to access this page.</p>
              <Button onClick={() => navigate("/")} className="mt-4">
                Go Home
              </Button>
            </CardContent>
          </Card>
        </div>
      </AuthGuard>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId) return;

    try {
      await updateUserMutation.mutateAsync({
        userId,
        data: formData,
      });
      displaySuccessToast("User updated successfully");
      navigate("/admin/users");
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.message || "Failed to update user";
      displayErrorToast(errorMessage);
    }
  };

  if (isLoading) {
    return (
      <AuthGuard requireRole="admin">
        <main className="relative min-h-screen overflow-hidden bg-black text-foreground">
          <div className="flex items-center justify-center min-h-screen">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500" />
          </div>
        </main>
      </AuthGuard>
    );
  }

  if (error || !user) {
    return (
      <AuthGuard requireRole="admin">
        <main className="relative min-h-screen overflow-hidden bg-black text-foreground">
          <div className="flex items-center justify-center min-h-screen">
            <Card className="w-full max-w-md">
              <CardHeader>
                <CardTitle>Error</CardTitle>
              </CardHeader>
              <CardContent>
                <p>Failed to load user. Please try again.</p>
                <Button
                  onClick={() => navigate("/admin/users")}
                  className="mt-4"
                >
                  Back to Users
                </Button>
              </CardContent>
            </Card>
          </div>
        </main>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard requireRole="admin">
      <main className="relative min-h-screen overflow-hidden bg-black text-foreground">
        <div aria-hidden className="pointer-events-none">
          <AnimatedBackground />
        </div>
        <AppLayout>
          <div className="rounded-3xl border border-white/10 bg-black/60 backdrop-blur-xl p-6 sm:p-8 lg:p-10">
            <PageHero
              eyebrow="Admin"
              title={`Edit User: ${user.username || user.email}`}
              description="Update user information and permissions"
              align="left"
              actions={
                <Button
                  variant="outline"
                  onClick={() => navigate("/admin/users")}
                  className="border border-white/20 bg-transparent text-foreground hover:bg-white/10"
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Back to Users
                </Button>
              }
            />

            <form onSubmit={handleSubmit} className="mt-8 space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>User Information</CardTitle>
                  <CardDescription>Basic user account details</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <label
                      htmlFor="username"
                      className="text-sm font-medium text-foreground"
                    >
                      Username
                    </label>
                    <Input
                      id="username"
                      value={formData.username}
                      onChange={(e) =>
                        setFormData({ ...formData, username: e.target.value })
                      }
                      placeholder="johndoe"
                      disabled={updateUserMutation.isPending}
                    />
                  </div>

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
                      value={formData.email}
                      onChange={(e) =>
                        setFormData({ ...formData, email: e.target.value })
                      }
                      placeholder="user@example.com"
                      disabled={updateUserMutation.isPending}
                    />
                  </div>

                  <div className="space-y-2">
                    <label
                      htmlFor="role"
                      className="text-sm font-medium text-foreground"
                    >
                      Role
                    </label>
                    <select
                      id="role"
                      value={formData.role}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          role: e.target.value as any,
                        })
                      }
                      disabled={
                        updateUserMutation.isPending ||
                        userId === currentUser?.id
                      }
                      className="flex h-10 w-full rounded-lg border border-brand-500/25 bg-black/70 backdrop-blur-sm px-4 py-2 text-[15px] transition-all duration-200"
                    >
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                      <option value="service">Service</option>
                    </select>
                    {userId === currentUser?.id && (
                      <p className="text-xs text-white/60">
                        You cannot change your own role
                      </p>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Account Status</CardTitle>
                  <CardDescription>
                    Manage account activation and verification
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-lg border border-white/10 bg-white/5">
                    <div className="flex items-center gap-3">
                      {formData.is_active ? (
                        <CheckCircle2 className="h-5 w-5 text-success-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-danger-500" />
                      )}
                      <div>
                        <p className="font-medium text-white">Account Active</p>
                        <p className="text-sm text-white/60">
                          {formData.is_active
                            ? "User can login and use the platform"
                            : "User account is deactivated"}
                        </p>
                      </div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.is_active}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            is_active: e.target.checked,
                          })
                        }
                        disabled={
                          updateUserMutation.isPending ||
                          userId === currentUser?.id
                        }
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-white/20 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-brand-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-500" />
                    </label>
                  </div>

                  <div className="flex items-center justify-between p-4 rounded-lg border border-white/10 bg-white/5">
                    <div className="flex items-center gap-3">
                      {formData.email_verified ? (
                        <CheckCircle2 className="h-5 w-5 text-success-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-warning-500" />
                      )}
                      <div>
                        <p className="font-medium text-white">Email Verified</p>
                        <p className="text-sm text-white/60">
                          {formData.email_verified
                            ? "Email address has been verified"
                            : "Email address not verified"}
                        </p>
                      </div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.email_verified}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            email_verified: e.target.checked,
                          })
                        }
                        disabled={updateUserMutation.isPending}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-white/20 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-brand-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-500" />
                    </label>
                  </div>
                </CardContent>
              </Card>

              <div className="flex items-center justify-end gap-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate("/admin/users")}
                  disabled={updateUserMutation.isPending}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={updateUserMutation.isPending}>
                  <Save className="mr-2 h-4 w-4" />
                  {updateUserMutation.isPending ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </form>
          </div>
        </AppLayout>
      </main>
    </AuthGuard>
  );
}
