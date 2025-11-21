import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { useResetPasswordForm } from "./reset-password/hooks/use-reset-password-form";
import {
  ResetPasswordForm,
  SuccessView,
} from "./reset-password/components/reset-password-form";

export default function ResetPasswordPage() {
  const {
    email,
    resetToken,
    password,
    confirmPassword,
    error,
    errors,
    isSuccess,
    isSubmitting,
    handleEmailChange,
    handleResetTokenChange,
    handlePasswordChange,
    handleConfirmPasswordChange,
    handleBlur,
    handleSubmit,
    hasTokenFromUrl,
    hasEmailFromUrl,
  } = useResetPasswordForm();

  if (isSuccess) {
    return <SuccessView />;
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-[var(--bg-primary)] px-4 sm:px-6 py-12">
      <div className="w-full max-w-[440px]">
        <Card className="bg-transparent border-0 shadow-none">
          <CardHeader className="space-y-4 px-0 pb-8">
            <CardTitle className="text-3xl md:text-4xl font-bold text-center text-[var(--text-primary)] leading-tight">
              Reset your password
            </CardTitle>
            <CardDescription className="text-center text-[var(--text-tertiary)] text-sm leading-relaxed">
              Enter your new password below
            </CardDescription>
          </CardHeader>
          <CardContent className="px-0 pt-0">
            <ResetPasswordForm
              email={email}
              resetToken={resetToken}
              password={password}
              confirmPassword={confirmPassword}
              error={error}
              errors={errors}
              isSubmitting={isSubmitting}
              hasTokenFromUrl={hasTokenFromUrl}
              hasEmailFromUrl={hasEmailFromUrl}
              onEmailChange={handleEmailChange}
              onResetTokenChange={handleResetTokenChange}
              onPasswordChange={handlePasswordChange}
              onConfirmPasswordChange={handleConfirmPasswordChange}
              onBlur={handleBlur}
              onSubmit={handleSubmit}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
