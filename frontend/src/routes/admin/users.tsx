import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Shield,
  Trash2,
  Edit,
  Search,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { useUsers, useDeleteUser } from "../../hooks/query/use-users";
import { useAuth } from "../../context/auth-context";
import { AuthGuard } from "../../components/features/auth/auth-guard";
import { isAdmin } from "../../utils/auth/permissions";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { AppLayout } from "../../components/layout/AppLayout";
import { PageHero } from "../../components/layout/PageHero";
import AnimatedBackground from "../../components/landing/AnimatedBackground";
import {
  displaySuccessToast,
  displayErrorToast,
} from "../../utils/custom-toast-handlers";

export default function AdminUsersPage() {
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const limit = 20;

  const { data, isLoading, error } = useUsers(page, limit);
  const deleteUserMutation = useDeleteUser();

  // Check if user is admin
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

  const filteredUsers =
    data?.items.filter((user) => {
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        user.email.toLowerCase().includes(query) ||
        user.username.toLowerCase().includes(query) ||
        user.id.toLowerCase().includes(query)
      );
    }) || [];

  const handleDelete = async (userId: string) => {
    if (userId === currentUser?.id) {
      displayErrorToast("You cannot delete your own account");
      return;
    }
    if (
      confirm(
        "Are you sure you want to delete this user? This action cannot be undone.",
      )
    ) {
      try {
        await deleteUserMutation.mutateAsync(userId);
        displaySuccessToast("User deleted successfully");
      } catch (err: any) {
        const errorMessage =
          err.response?.data?.message || "Failed to delete user";
        displayErrorToast(errorMessage);
      }
    }
  };

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
              title="User Management"
              description="Manage user accounts, roles, and permissions"
              align="left"
            />

            {/* Search */}
            <div className="mb-6">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-white/40" />
                <Input
                  type="text"
                  placeholder="Search users by email, username, or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {/* Users Table */}
            <Card>
              <CardHeader>
                <CardTitle>Users ({data?.total || 0})</CardTitle>
              </CardHeader>
              <CardContent>
                {isLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
                  </div>
                ) : error ? (
                  <div className="text-center py-12 text-danger-500">
                    Failed to load users. Please try again.
                  </div>
                ) : filteredUsers.length === 0 ? (
                  <div className="text-center py-12 text-white/60">
                    No users found
                  </div>
                ) : (
                  <>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-white/10">
                            <th className="text-left py-3 px-4 text-sm font-semibold text-white/80">
                              User
                            </th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-white/80">
                              Email
                            </th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-white/80">
                              Role
                            </th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-white/80">
                              Status
                            </th>
                            <th className="text-left py-3 px-4 text-sm font-semibold text-white/80">
                              Created
                            </th>
                            <th className="text-right py-3 px-4 text-sm font-semibold text-white/80">
                              Actions
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredUsers.map((user) => (
                            <tr
                              key={user.id}
                              className="border-b border-white/5 hover:bg-white/5"
                            >
                              <td className="py-3 px-4">
                                <div className="flex items-center gap-3">
                                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-accent-500 flex items-center justify-center">
                                    <span className="text-xs font-semibold text-white">
                                      {user.username?.[0]?.toUpperCase() ||
                                        user.email[0].toUpperCase()}
                                    </span>
                                  </div>
                                  <div>
                                    <div className="font-medium text-white">
                                      {user.username || "N/A"}
                                    </div>
                                    <div className="text-xs text-white/60">
                                      {user.id.slice(0, 8)}...
                                    </div>
                                  </div>
                                </div>
                              </td>
                              <td className="py-3 px-4 text-white/80">
                                {user.email}
                              </td>
                              <td className="py-3 px-4">
                                <span
                                  className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                                    user.role === "admin"
                                      ? "bg-brand-500/20 text-brand-400"
                                      : "bg-white/10 text-white/60"
                                  }`}
                                >
                                  {user.role === "admin" && (
                                    <Shield className="h-3 w-3" />
                                  )}
                                  {user.role.charAt(0).toUpperCase() +
                                    user.role.slice(1)}
                                </span>
                              </td>
                              <td className="py-3 px-4">
                                <span
                                  className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                                    user.is_active
                                      ? "bg-success-500/20 text-success-400"
                                      : "bg-danger-500/20 text-danger-400"
                                  }`}
                                >
                                  {user.is_active ? "Active" : "Inactive"}
                                </span>
                              </td>
                              <td className="py-3 px-4 text-white/60 text-sm">
                                {new Date(user.created_at).toLocaleDateString()}
                              </td>
                              <td className="py-3 px-4">
                                <div className="flex items-center justify-end gap-2">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() =>
                                      navigate(`/admin/users/${user.id}`)
                                    }
                                    title="Edit user"
                                  >
                                    <Edit className="h-4 w-4" />
                                  </Button>
                                  {user.id !== currentUser?.id && (
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => handleDelete(user.id)}
                                      disabled={deleteUserMutation.isPending}
                                    >
                                      <Trash2 className="h-4 w-4 text-danger-400" />
                                    </Button>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Pagination */}
                    {data && data.total_pages > 1 && (
                      <div className="flex items-center justify-between mt-6 pt-6 border-t border-white/10">
                        <div className="text-sm text-white/60">
                          Showing {(page - 1) * limit + 1} to{" "}
                          {Math.min(page * limit, data.total)} of {data.total}{" "}
                          users
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setPage((p) => Math.max(1, p - 1))}
                            disabled={page === 1}
                          >
                            <ChevronLeft className="h-4 w-4" />
                            Previous
                          </Button>
                          <div className="text-sm text-white/60 px-4">
                            Page {page} of {data.total_pages}
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              setPage((p) => Math.min(data.total_pages, p + 1))
                            }
                            disabled={page === data.total_pages}
                          >
                            Next
                            <ChevronRight className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </AppLayout>
      </main>
    </AuthGuard>
  );
}
