import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Save } from "lucide-react";
import { useAuth } from "../../../context/auth-context";
import { isAdmin } from "../../../utils/auth/permissions";
import { Button } from "../../../components/ui/button";
import { AppLayout } from "../../../components/layout/AppLayout";
import { PageHero } from "../../../components/layout/PageHero";
import AnimatedBackground from "../../../components/landing/AnimatedBackground";
import { AuthGuard } from "../../../components/features/auth/auth-guard";
import { useEditUserForm } from "./[userId]/hooks/use-edit-user-form";
import { UserFormFields } from "./[userId]/components/user-form-fields";
import { AccountStatusCard } from "./[userId]/components/account-status-card";
import { LoadingState } from "./[userId]/components/loading-state";
import { ErrorState } from "./[userId]/components/error-state";
import { AccessDenied } from "./[userId]/components/access-denied";

export default function EditUserPage() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();

  const {
    formData,
    handleFieldChange,
    handleSubmit,
    isLoading,
    error,
    user,
    isSubmitting,
  } = useEditUserForm(userId);

  if (!isAdmin(currentUser)) {
    return <AccessDenied />;
  }

  if (isLoading) {
    return <LoadingState />;
  }

  if (error || !user) {
    return <ErrorState />;
  }

  const isCurrentUser = userId === currentUser?.id;

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
              <UserFormFields
                formData={formData}
                onChange={handleFieldChange}
                disabled={isSubmitting}
                isCurrentUser={isCurrentUser}
              />

              <AccountStatusCard
                formData={formData}
                onChange={handleFieldChange}
                disabled={isSubmitting}
                isCurrentUser={isCurrentUser}
              />

              <div className="flex items-center justify-end gap-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate("/admin/users")}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting}>
                  <Save className="mr-2 h-4 w-4" />
                  {isSubmitting ? "Saving..." : "Save Changes"}
                </Button>
              </div>
            </form>
          </div>
        </AppLayout>
      </main>
    </AuthGuard>
  );
}
