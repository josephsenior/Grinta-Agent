import { cn } from "#/utils/utils";

interface ContextMenuListItemProps {
  testId?: string;
  onClick: (event: React.MouseEvent<HTMLButtonElement>) => void;
  isDisabled?: boolean;
}

export function ContextMenuListItem({
  children,
  testId,
  onClick,
  isDisabled,
}: React.PropsWithChildren<ContextMenuListItemProps>) {
  return (
    <button
      data-testid={testId || "context-menu-list-item"}
      type="button"
      onClick={(e) => {
        // Prevent clicks on menu items from bubbling up to parent NavLink/card
        e.stopPropagation();
        onClick?.(e);
      }}
      disabled={isDisabled}
      className={cn(
        "group text-sm px-6 py-4 w-full text-start hover:bg-background-tertiary cursor-pointer transition-all duration-200",
        "disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-transparent text-nowrap",
        "text-foreground hover:text-violet-500 font-medium",
      )}
    >
      {children}
    </button>
  );
}
