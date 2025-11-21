import React from "react";
import { Check, Download } from "lucide-react";
import type { MCPMarketplaceItem } from "#/types/mcp-marketplace";

interface HeaderSectionProps {
  mcp: MCPMarketplaceItem;
  isInstalled: boolean;
  installCount?: number;
  rating?: number | string;
}

export function HeaderSection({
  mcp,
  isInstalled,
  installCount,
  rating,
}: HeaderSectionProps) {
  const formatInstallCount = (count?: number) => {
    if (!count) return "";
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}k`;
    }
    return count.toString();
  };

  return (
    <div className="flex items-start gap-4 mb-5">
      <div className="flex-shrink-0 w-14 h-14 flex items-center justify-center text-3xl bg-gradient-to-br from-background-tertiary to-background-primary rounded-xl border border-border/60 shadow-sm group-hover:shadow-md group-hover:scale-105 transition-all duration-300">
        {mcp.icon || "📦"}
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-lg font-bold text-foreground truncate group-hover:text-brand-400 transition-colors duration-200">
            {mcp.name}
          </h3>
          {isInstalled && (
            <div className="flex-shrink-0 w-6 h-6 bg-success-500/20 rounded-full flex items-center justify-center">
              <Check className="w-3.5 h-3.5 text-success-500" />
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 text-sm text-foreground-secondary">
          <span className="truncate font-medium">by {mcp.author}</span>
          {installCount && (
            <>
              <span className="text-foreground-tertiary">•</span>
              <span className="flex items-center gap-1.5 px-2 py-1 bg-background-primary/50 rounded-md">
                <Download className="w-3 h-3" />
                <span className="font-medium">
                  {formatInstallCount(installCount)}
                </span>
              </span>
            </>
          )}
          {rating && (
            <>
              <span className="text-foreground-tertiary">•</span>
              <span className="flex items-center gap-1 px-2 py-1 bg-background-primary/50 rounded-md">
                <span className="text-yellow-400">⭐</span>
                <span className="font-medium">
                  {typeof rating === "number" ? rating.toFixed(1) : rating}
                </span>
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
