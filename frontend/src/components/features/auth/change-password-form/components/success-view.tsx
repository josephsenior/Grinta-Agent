import { useTranslation } from "react-i18next";
import { CheckCircle2 } from "lucide-react";
import { Card, CardContent } from "../../../../ui/card";

export function SuccessView() {
  const { t } = useTranslation();
  return (
    <Card className="border-success-500/25">
      <CardContent className="pt-6">
        <div className="flex items-center gap-3 text-success-500">
          <CheckCircle2 className="h-5 w-5" />
          <p className="font-medium">
            {t("auth.passwordChangedSuccess", "Password changed successfully!")}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
