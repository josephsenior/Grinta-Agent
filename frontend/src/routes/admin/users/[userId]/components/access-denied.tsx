import { useNavigate } from "react-router-dom";
import { AuthGuard } from "#/components/features/auth/auth-guard";
import { Card, CardContent, CardHeader, CardTitle } from "#/components/ui/card";
import { Button } from "#/components/ui/button";

export function AccessDenied() {
  const navigate = useNavigate();

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
