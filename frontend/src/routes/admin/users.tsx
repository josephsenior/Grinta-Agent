import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Shield,
  Trash2,
  Edit,
  Search,
  ChevronLeft,
  ChevronRight,
  Filter,
} from "lucide-react";
import type { AxiosError } from "axios";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { AppLayout } from "../../components/layout/AppLayout";
import {
  displaySuccessToast,
  displayErrorToast,
} from "../../utils/custom-toast-handlers";
import { filterUsers } from "./users/user-filters";
import type { User } from "#/types/auth";

export default function AdminUsersPage() {
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [userToDelete, setUserToDelete] = useState<string | null>(null);
  const limit = 20;

  const { data, isLoading, error } = useUsers(page, limit);
  const deleteUserMutation = useDeleteUser();

  // Check if user is admin
  if (!isAdmin(currentUser)) {
    return (
      <AuthGuard requireRole="admin">
        <div className="min-h-screen flex items-center justify-center bg-black">
          <Card className="max-w-md">
            <CardHeader className="min-w-[400px]">
              <CardTitle className="whitespace-normal">Access Denied</CardTitle>
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

  const filteredUsers = filterUsers(data?.items || [], {
    searchQuery,
    roleFilter,
    statusFilter,
  });

  const handleDeleteClick = (userId: string) => {
    if (userId === currentUser?.id) {
      displayErrorToast("You cannot delete your own account");
      return;
    }
    setUserToDelete(userId);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!userToDelete) return;
    try {
      await deleteUserMutation.mutateAsync(userToDelete);
      displaySuccessToast("User deleted successfully");
      setDeleteDialogOpen(false);
      setUserToDelete(null);
    } catch (err) {
      const deleteError = err as AxiosError<{ message?: string }>;
      const errorMessage =
        deleteError.response?.data?.message || "Failed to delete user";
      displayErrorToast(errorMessage);
    }
  };

  return (
    <AuthGuard requireRole="admin">
      <AppLayout>
        <div className="space-y-6">
          {/* Page Title: User Management */}
          <div>
            <h1 className="text-[2.25rem] font-bold text-[#FFFFFF] leading-[1.2] mb-2">
              User Management
            </h1>
          </div>

          {/* Search and Filter */}
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-[#94A3B8]" />
              <Input
                type="text"
                placeholder="Search users by email, username, or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-12 pr-4 py-3 bg-[#000000] border-[#1a1a1a] text-[#FFFFFF] placeholder:text-[#94A3B8] rounded-xl focus:border-[#8b5cf6] focus:ring-1 focus:ring-[#8b5cf6]"
              />
            </div>

            {/* Filters */}
            <div className="flex gap-2">
              {/* Role Filter */}
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-[#94A3B8] pointer-events-none" />
                <select
                  value={roleFilter}
                  onChange={(e) => setRoleFilter(e.target.value)}
                  className="pl-10 pr-4 py-3 bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8b5cf6] text-sm"
                >
                  <option value="all">All Roles</option>
                  <option value="admin">Admin</option>
                  <option value="user">User</option>
                </select>
              </div>

              {/* Status Filter */}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-4 py-3 bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#8b5cf6] text-sm"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>

          {/* Users Table */}
          <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl shadow-[0_4px_20px_rgba(0,0,0,0.15)]">
            <CardHeader className="min-w-[400px]">
              <CardTitle className="text-[#FFFFFF] whitespace-normal">
                Users ({data?.total || 0})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {(() => {
                if (isLoading) {
                  return (
                    <div className="flex items-center justify-center py-12">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
                    </div>
                  );
                }
                if (error) {
                  return (
                    <div className="text-center py-12 text-danger-500">
                      Failed to load users. Please try again.
                    </div>
                  );
                }
                if (filteredUsers.length === 0) {
                  return (
                    <div className="text-center py-12 text-white/60">
                      No users found
                    </div>
                  );
                }
                return (
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
                          {filteredUsers.map((user: User) => (
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
                                      onClick={() => handleDeleteClick(user.id)}
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
                );
              })()}
            </CardContent>
          </Card>

          {/* Delete Confirmation Dialog */}
          <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Delete User</DialogTitle>
                <DialogDescription>
                  Are you sure you want to delete this user? This action cannot
                  be undone.
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => {
                    setDeleteDialogOpen(false);
                    setUserToDelete(null);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDeleteConfirm}
                  disabled={deleteUserMutation.isPending}
                >
                  {deleteUserMutation.isPending ? "Deleting..." : "Delete"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </AppLayout>
    </AuthGuard>
  );
}
