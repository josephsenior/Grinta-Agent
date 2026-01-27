import { useNavigate } from "react-router-dom";
import {
  Settings,
} from "lucide-react";

interface MenuItem {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
}

interface UseMenuItemsProps {
  onClose: () => void;
}

export function useMenuItems({
  onClose,
}: UseMenuItemsProps): MenuItem[] {
  const navigate = useNavigate();

  return [
    {
      icon: Settings,
      label: "Settings",
      onClick: () => {
        navigate("/settings");
        onClose();
      },
    },
  ];
}
