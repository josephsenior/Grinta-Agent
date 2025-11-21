import { ArrowRight } from "lucide-react";
import { cn } from "#/utils/utils";

interface QuickActionButtonProps {
  icon: React.ElementType;
  title: string;
  description: string;
  onClick: () => void;
  variant?: "default" | "primary";
}

export function QuickActionButton({
  icon: Icon,
  title,
  description,
  onClick,
  variant = "default",
}: QuickActionButtonProps) {
  if (variant === "primary") {
    return (
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "group w-full text-left",
          "bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed]",
          "text-white rounded-lg px-6 py-3",
          "transition-all duration-150",
          "hover:brightness-110 active:brightness-95",
          "shadow-[0_4px_20px_rgba(139,92,246,0.15)]",
        )}
      >
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-white/10 p-2">
            <Icon className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-white">{title}</h3>
            <p className="text-xs text-white/80">{description}</p>
          </div>
          <ArrowRight className="h-4 w-4 text-white/60 transition-transform group-hover:translate-x-1" />
        </div>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group w-full text-left",
        "bg-[#000000] border border-[#1a1a1a] rounded-lg px-6 py-3",
        "text-[#FFFFFF]",
        "transition-all duration-150",
        "hover:bg-[rgba(139,92,246,0.1)] hover:border-[#8b5cf6]",
      )}
    >
      <div className="flex items-center gap-3">
        <div className="rounded-lg bg-[rgba(0,0,0,0.6)] p-2">
          <Icon className="h-5 w-5 text-[#F1F5F9]" />
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-[#FFFFFF]">{title}</h3>
          <p className="text-xs text-[#94A3B8]">{description}</p>
        </div>
        <ArrowRight className="h-4 w-4 text-[#94A3B8] transition-transform group-hover:translate-x-1" />
      </div>
    </button>
  );
}
