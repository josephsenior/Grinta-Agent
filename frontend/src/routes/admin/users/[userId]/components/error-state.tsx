import { useNavigate } from "react-router-dom";
import { AuthGuard } from "#/components/features/auth/auth-guard";
import { Card, CardContent, CardHeader, CardTitle } from "#/components/ui/card";
import { Button } from "#/components/ui/button";

export function ErrorState() {
  const navigate = useNavigate();

  return (
    <AuthGuard requireRole="admin">
      <main className="relative min-h-screen overflow-hidden bg-black text-foreground">
        <div className="flex items-center justify-center min-h-screen">
          <Card className="max-w-md">
            <CardHeader className="min-w-[400px]">
              <CardTitle className="whitespace-normal">Error</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Failed to load user. Please try again.</p>
              <Button onClick={() => navigate("/admin/users")} className="mt-4">
                Back to Users
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </AuthGuard>
  );
}
