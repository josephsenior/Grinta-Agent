import React from "react";
import { Check, Download, Info, ExternalLink } from "lucide-react";
import { BrandButton } from "#/components/features/settings/brand-button";
import type { MCPMarketplaceItem } from "#/types/mcp-marketplace";

interface ActionsSectionProps {
  mcp: MCPMarketplaceItem;
  isInstalled: boolean;
  onInstall: (mcp: MCPMarketplaceItem) => void;
  onViewDetails: (mcp: MCPMarketplaceItem) => void;
}

export function ActionsSection({
  mcp,
  isInstalled,
  onInstall,
  onViewDetails,
}: ActionsSectionProps) {
  return (
    <div className="flex items-center gap-3">
      <BrandButton
        type="button"
        variant={isInstalled ? "secondary" : "primary"}
        className="flex-1 h-11 font-semibold transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
        onClick={() => onInstall(mcp)}
        isDisabled={isInstalled}
      >
        {isInstalled ? (
          <>
            <Check className="w-4 h-4" />
            <span>Installed</span>
          </>
        ) : (
          <>
            <Download className="w-4 h-4" />
            <span>Install</span>
          </>
        )}
      </BrandButton>

      <button
        type="button"
        onClick={() => onViewDetails(mcp)}
        className="p-3 rounded-lg border border-border/60 bg-background-primary/60 hover:bg-background-primary hover:border-brand-500/50 transition-all duration-200 hover:scale-105 active:scale-95 backdrop-blur-sm shadow-sm"
        aria-label="View details"
      >
        <Info className="w-4 h-4 text-foreground-secondary hover:text-brand-400 transition-colors" />
      </button>

      {mcp.homepage && (
        <a
          href={mcp.homepage}
          target="_blank"
          rel="noopener noreferrer"
          className="p-3 rounded-lg border border-border/60 bg-background-primary/60 hover:bg-background-primary hover:border-brand-500/50 transition-all duration-200 hover:scale-105 active:scale-95 backdrop-blur-sm shadow-sm"
          aria-label="Open homepage"
          onClick={(e) => e.stopPropagation()}
        >
          <ExternalLink className="w-4 h-4 text-foreground-secondary hover:text-brand-400 transition-colors" />
        </a>
      )}
    </div>
  );
}
