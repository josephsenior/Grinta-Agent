import { Link } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "#/components/ui/card";

export function SuccessView() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[var(--bg-primary)] px-4 sm:px-6 py-12">
      <div className="w-full max-w-[440px]">
        <Card className="bg-transparent border-0 shadow-none">
          <CardHeader className="space-y-4 px-0 pb-8">
            <div className="mb-2 flex justify-center">
              <CheckCircle2 className="w-16 h-16 text-success-500" />
            </div>
            <CardTitle className="text-3xl md:text-4xl font-bold text-center text-[var(--text-primary)] leading-tight">
              Password reset successful
            </CardTitle>
            <CardDescription className="text-center text-[var(--text-tertiary)] text-sm leading-relaxed">
              Your password has been reset. Redirecting to login...
            </CardDescription>
          </CardHeader>
          <CardContent className="px-0 pt-0">
            <div className="w-full text-center">
              <Link
                to="/auth/login"
                className="text-sm text-brand-500 hover:text-brand-400 hover:underline font-medium"
              >
                Go to login now
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
