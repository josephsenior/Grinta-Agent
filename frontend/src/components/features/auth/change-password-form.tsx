import { useTranslation } from "react-i18next";
import { Button } from "../../ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../ui/card";
import { useChangePasswordForm } from "./change-password-form/hooks/use-change-password-form";
import { SuccessView } from "./change-password-form/components/success-view";
import { PasswordFormFields } from "./change-password-form/components/password-form-fields";

interface ChangePasswordFormProps {
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function ChangePasswordForm({
  onSuccess,
  onCancel,
}: ChangePasswordFormProps) {
  const { t } = useTranslation();
  const {
    currentPassword,
    setCurrentPassword,
    newPassword,
    setNewPassword,
    confirmPassword,
    setConfirmPassword,
    showCurrentPassword,
    setShowCurrentPassword,
    showNewPassword,
    setShowNewPassword,
    showConfirmPassword,
    setShowConfirmPassword,
    error,
    isSuccess,
    isPending,
    handleSubmit,
  } = useChangePasswordForm({ onSuccess });

  if (isSuccess) {
    return <SuccessView />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("auth.changePassword", "Change Password")}</CardTitle>
        <CardDescription>
          {t("auth.updatePasswordDescription", "Update your account password")}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <PasswordFormFields
            currentPassword={currentPassword}
            newPassword={newPassword}
            confirmPassword={confirmPassword}
            showCurrentPassword={showCurrentPassword}
            showNewPassword={showNewPassword}
            showConfirmPassword={showConfirmPassword}
            onCurrentPasswordChange={setCurrentPassword}
            onNewPasswordChange={setNewPassword}
            onConfirmPasswordChange={setConfirmPassword}
            onToggleShowCurrentPassword={() =>
              setShowCurrentPassword(!showCurrentPassword)
            }
            onToggleShowNewPassword={() => setShowNewPassword(!showNewPassword)}
            onToggleShowConfirmPassword={() =>
              setShowConfirmPassword(!showConfirmPassword)
            }
            disabled={isPending}
            error={error}
          />

          <div className="flex items-center justify-end gap-3 pt-4">
            {onCancel && (
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                disabled={isPending}
              >
                {t("common.cancel", "Cancel")}
              </Button>
            )}
            <Button type="submit" disabled={isPending}>
              {isPending
                ? t("auth.changingPassword", "Changing password...")
                : t("auth.changePassword", "Change Password")}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
