import { MoreVertical } from "lucide-react";

interface EllipsisButtonProps {
  onClick: (event: React.MouseEvent<HTMLButtonElement>) => void;
}

export function EllipsisButton({ onClick }: EllipsisButtonProps) {
  return (
    <button
      data-testid="ellipsis-button"
      type="button"
      onClick={onClick}
      className="cursor-pointer"
    >
      <MoreVertical color="#a3a3a3" />
    </button>
  );
}
