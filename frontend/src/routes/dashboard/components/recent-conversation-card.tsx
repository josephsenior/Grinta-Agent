import { MessageSquare, ArrowRight } from "lucide-react";
import { cn } from "#/utils/utils";
import { useGSAPHover } from "#/hooks/use-gsap-animations";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";

interface RecentConversationCardProps {
  title: string;
  updatedAt: string;
  onClick: () => void;
}

export function RecentConversationCard({
  title,
  updatedAt,
  onClick,
}: RecentConversationCardProps) {
  const cardRef = useGSAPHover<HTMLButtonElement>({
    scale: 1.01,
    y: -2,
    duration: 0.25,
  });

  return (
    <button
      ref={cardRef}
      type="button"
      onClick={onClick}
      className={cn(
        "group w-full text-left",
        "bg-[#000000] border border-[#1a1a1a] rounded-xl p-6",
        "shadow-[0_4px_20px_rgba(0,0,0,0.15)]",
        "transition-all duration-200",
        "hover:border-[#8b5cf6] hover:shadow-[0_8px_40px_rgba(0,0,0,0.2)]",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <MessageSquare className="h-4 w-4 text-[#8b5cf6] flex-shrink-0" />
            <p className="text-sm font-medium text-[#FFFFFF] truncate">
              {title}
            </p>
          </div>
          <p className="text-xs text-[#94A3B8]">
            <ClientFormattedDate iso={updatedAt} />
          </p>
        </div>
        <ArrowRight className="h-4 w-4 text-[#94A3B8] transition-transform group-hover:translate-x-1 group-hover:text-[#8b5cf6] flex-shrink-0" />
      </div>
    </button>
  );
}
