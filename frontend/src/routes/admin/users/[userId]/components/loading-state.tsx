import { AuthGuard } from "#/components/features/auth/auth-guard";

export function LoadingState() {
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
