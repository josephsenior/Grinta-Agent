import { CheckCircle2, XCircle } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "#/components/ui/card";

interface StatusToggleProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled: boolean;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
}

function StatusToggle({
  label,
  checked,
  onChange,
  disabled,
  description,
  icon: Icon,
  iconColor,
}: StatusToggleProps) {
  const toggleId = `status-toggle-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div className="flex items-center justify-between p-4 rounded-lg border border-white/10 bg-white/5">
      <div className="flex items-center gap-3">
        <Icon className={`h-5 w-5 ${iconColor}`} />
        <div>
          <p className="font-medium text-white">{label}</p>
          <p className="text-sm text-white/60">{description}</p>
        </div>
      </div>
      <label
        htmlFor={toggleId}
        className="relative inline-flex items-center cursor-pointer"
      >
        <input
          id={toggleId}
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className="sr-only peer"
          aria-label={label}
        />
        <div className="w-11 h-6 bg-white/20 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-brand-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand-500" />
      </label>
    </div>
  );
}

interface AccountStatusCardProps {
  formData: {
    is_active: boolean;
    email_verified: boolean;
  };
  onChange: (field: "is_active" | "email_verified", value: boolean) => void;
  disabled: boolean;
  isCurrentUser: boolean;
}

export function AccountStatusCard({
  formData,
  onChange,
  disabled,
  isCurrentUser,
}: AccountStatusCardProps) {
  return (
    <Card>
      <CardHeader className="min-w-[400px]">
        <CardTitle className="whitespace-normal">Account Status</CardTitle>
        <CardDescription className="whitespace-normal">
          Manage account activation and verification
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <StatusToggle
          label="Account Active"
          checked={formData.is_active}
          onChange={(checked) => onChange("is_active", checked)}
          disabled={disabled || isCurrentUser}
          description={
            formData.is_active
              ? "User can login and use the platform"
              : "User account is deactivated"
          }
          icon={formData.is_active ? CheckCircle2 : XCircle}
          iconColor={
            formData.is_active ? "text-success-500" : "text-danger-500"
          }
        />

        <StatusToggle
          label="Email Verified"
          checked={formData.email_verified}
          onChange={(checked) => onChange("email_verified", checked)}
          disabled={disabled}
          description={
            formData.email_verified
              ? "Email address has been verified"
              : "Email address not verified"
          }
          icon={formData.email_verified ? CheckCircle2 : XCircle}
          iconColor={
            formData.email_verified ? "text-success-500" : "text-warning-500"
          }
        />
      </CardContent>
    </Card>
  );
}
