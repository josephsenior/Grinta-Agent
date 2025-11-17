import { cn } from "#/utils/utils";

interface StyledSwitchComponentProps {
  isToggled: boolean;
}

export function StyledSwitchComponent({
  isToggled,
}: StyledSwitchComponentProps) {
  return (
    <div
      className={cn(
        "w-12 h-6 rounded-xl flex items-center p-1.5 cursor-pointer transition-all duration-200",
        isToggled
          ? "justify-end bg-white/20 border border-white/20"
          : "justify-start bg-black/60 border border-white/10",
      )}
    >
      <div
        className={cn(
          "w-3 h-3 rounded-xl transition-all duration-200",
          isToggled ? "bg-white" : "bg-foreground-tertiary",
        )}
      />
    </div>
  );
}
