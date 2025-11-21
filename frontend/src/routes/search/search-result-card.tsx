import React from "react";
import { LucideIcon, ArrowRight } from "lucide-react";
import { Card } from "#/components/ui/card";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";
import { cn } from "#/utils/utils";

interface SearchResultCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  timestamp?: string;
  onClick: () => void;
}

export function SearchResultCard({
  icon: Icon,
  title,
  description,
  timestamp,
  onClick,
}: SearchResultCardProps) {
  return (
    <Card
      className={cn(
        "bg-[#000000] border border-[#1a1a1a] rounded-xl p-4 shadow-[0_4px_20px_rgba(0,0,0,0.15)]",
        "hover:border-[#8b5cf6] hover:shadow-[0_4px_20px_rgba(139,92,246,0.2)]",
        "transition-all duration-200 cursor-pointer group",
      )}
      onClick={onClick}
    >
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0 mt-1">
          <Icon className="h-5 w-5 text-[#8b5cf6]" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-base font-semibold text-[#FFFFFF] mb-1 group-hover:text-[#8b5cf6] transition-colors">
            {title}
          </h4>
          <p className="text-sm text-[#94A3B8] line-clamp-2 mb-2">
            {description}
          </p>
          {timestamp && (
            <div className="flex items-center gap-2 text-xs text-[#64748B]">
              <ClientFormattedDate iso={timestamp} />
            </div>
          )}
        </div>
        <div className="flex-shrink-0 mt-1">
          <ArrowRight className="h-4 w-4 text-[#64748B] group-hover:text-[#8b5cf6] group-hover:translate-x-1 transition-all" />
        </div>
      </div>
    </Card>
  );
}
