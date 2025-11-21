import { Input } from "#/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "#/components/ui/card";

interface UserFormFieldsProps {
  formData: {
    username: string;
    email: string;
    role: "admin" | "user" | "service";
  };
  onChange: (field: string, value: string) => void;
  disabled: boolean;
  isCurrentUser: boolean;
}

export function UserFormFields({
  formData,
  onChange,
  disabled,
  isCurrentUser,
}: UserFormFieldsProps) {
  return (
    <Card>
      <CardHeader className="min-w-[400px]">
        <CardTitle className="whitespace-normal">User Information</CardTitle>
        <CardDescription className="whitespace-normal">
          Basic user account details
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <label
            htmlFor="username"
            className="text-sm font-medium text-foreground"
          >
            Username
          </label>
          <Input
            id="username"
            value={formData.username}
            onChange={(e) => onChange("username", e.target.value)}
            placeholder="johndoe"
            disabled={disabled}
          />
        </div>

        <div className="space-y-2">
          <label
            htmlFor="email"
            className="text-sm font-medium text-foreground"
          >
            Email
          </label>
          <Input
            id="email"
            type="email"
            value={formData.email}
            onChange={(e) => onChange("email", e.target.value)}
            placeholder="user@example.com"
            disabled={disabled}
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="role" className="text-sm font-medium text-foreground">
            Role
          </label>
          <select
            id="role"
            value={formData.role}
            onChange={(e) => onChange("role", e.target.value)}
            disabled={disabled || isCurrentUser}
            className="flex h-10 w-full rounded-lg border border-brand-500/25 bg-black/70 backdrop-blur-sm px-4 py-2 text-[15px] transition-all duration-200"
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
            <option value="service">Service</option>
          </select>
          {isCurrentUser && (
            <p className="text-xs text-white/60">
              You cannot change your own role
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
