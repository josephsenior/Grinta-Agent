import { useNavigate } from "react-router-dom";
import {
  User,
  Settings,
  CreditCard,
  LayoutDashboard,
  Shield,
} from "lucide-react";

interface MenuItem {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
  badge?: string;
}

interface UseMenuItemsProps {
  isUserAdmin: boolean;
  isSaas: boolean;
  balance: number | undefined;
  onClose: () => void;
}

export function useMenuItems({
  isUserAdmin,
  isSaas,
  balance,
  onClose,
}: UseMenuItemsProps): MenuItem[] {
  const navigate = useNavigate();

  const baseItems: MenuItem[] = [
    {
      icon: LayoutDashboard,
      label: "Dashboard",
      onClick: () => {
        navigate("/dashboard");
        onClose();
      },
    },
    {
      icon: User,
      label: "Profile",
      onClick: () => {
        navigate("/profile");
        onClose();
      },
    },
    {
      icon: Settings,
      label: "Settings",
      onClick: () => {
        navigate("/settings");
        onClose();
      },
    },
  ];

  const adminItem: MenuItem | null = isUserAdmin
    ? {
        icon: Shield,
        label: "Admin Panel",
        onClick: () => {
          navigate("/admin/users");
          onClose();
        },
      }
    : null;

  const billingItem: MenuItem | null =
    isSaas && balance !== undefined
      ? {
          icon: CreditCard,
          label: "Billing & Credits",
          onClick: () => {
            navigate("/settings/billing");
            onClose();
          },
          badge: `$${Number(balance).toFixed(2)}`,
        }
      : null;

  return [
    ...baseItems,
    ...(adminItem ? [adminItem] : []),
    ...(billingItem ? [billingItem] : []),
  ];
}
