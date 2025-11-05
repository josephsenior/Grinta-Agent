import { cn } from "#/utils/utils";

interface ContextMenuIconTextProps {
  icon: React.ComponentType<{ className?: string }>;
  text: string;
  className?: string;
  iconClassName?: string;
}

export function ContextMenuIconText({
  icon: Icon,
  text,
  className,
  iconClassName,
}: ContextMenuIconTextProps) {
  return (
    <div className={cn("flex items-center gap-4 px-1", className)}>
      <Icon
        className={cn(
          "w-5 h-5 shrink-0 text-violet-500/80 group-hover:text-violet-500 transition-colors duration-300",
          iconClassName,
        )}
      />
      <span className="text-foreground group-hover:text-violet-500 transition-colors duration-300">
        {text}
      </span>
    </div>
  );
}
