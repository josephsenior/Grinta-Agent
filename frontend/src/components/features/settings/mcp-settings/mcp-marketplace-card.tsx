import { useState } from "react";
import {
  ExternalLink,
  Download,
  Info,
  Check,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import type { MCPMarketplaceItem } from "#/types/mcp-marketplace";
import { BrandButton } from "#/components/features/settings/brand-button";

interface MCPMarketplaceCardProps {
  mcp: MCPMarketplaceItem;
  isInstalled: boolean;
  onInstall: (mcp: MCPMarketplaceItem) => void;
  onViewDetails: (mcp: MCPMarketplaceItem) => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  browser: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  database: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  cloud: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  "ai-tools": "bg-pink-500/10 text-pink-400 border-pink-500/20",
  development: "bg-green-500/10 text-green-400 border-green-500/20",
  productivity: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  "file-system": "bg-orange-500/10 text-orange-400 border-orange-500/20",
  "api-integration": "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  testing: "bg-red-500/10 text-red-400 border-red-500/20",
  monitoring: "bg-teal-500/10 text-teal-400 border-teal-500/20",
  security: "bg-rose-500/10 text-rose-400 border-rose-500/20",
  communication: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  other: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

export function MCPMarketplaceCard({
  mcp,
  isInstalled,
  onInstall,
  onViewDetails,
}: MCPMarketplaceCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  const categoryColor = CATEGORY_COLORS[mcp.category] || CATEGORY_COLORS.other;

  const formatInstallCount = (count?: number) => {
    if (!count) return "";
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}k`;
    }
    return count.toString();
  };

  return (
    <div
      className="group relative overflow-hidden rounded-xl border border-border/50 bg-gradient-to-br from-background-secondary/80 to-background-tertiary/40 backdrop-blur-sm transition-all duration-300 hover:border-brand-500/40 hover:shadow-xl hover:shadow-brand-500/5 hover:-translate-y-1"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Featured/Popular badges */}
      <div className="absolute top-4 right-4 flex gap-2 z-10">
        {mcp.featured && (
          <span className="px-2.5 py-1 text-xs font-semibold bg-gradient-to-r from-brand-500/20 to-brand-600/20 text-brand-400 rounded-full border border-brand-500/30 backdrop-blur-sm shadow-sm">
            <Sparkles className="w-3 h-3 inline mr-1" />
            Featured
          </span>
        )}
        {mcp.popular && (
          <span className="px-2.5 py-1 text-xs font-semibold bg-gradient-to-r from-accent-500/20 to-accent-600/20 text-accent-400 rounded-full border border-accent-500/30 backdrop-blur-sm shadow-sm">
            <TrendingUp className="w-3 h-3 inline mr-1" />
            Popular
          </span>
        )}
      </div>

      {/* Gradient overlay for visual depth */}
      <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-brand-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

      {/* Content */}
      <div className="relative p-6">
        {/* Icon and Header */}
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
              {mcp.installCount && (
                <>
                  <span className="text-foreground-tertiary">•</span>
                  <span className="flex items-center gap-1.5 px-2 py-1 bg-background-primary/50 rounded-md">
                    <Download className="w-3 h-3" />
                    <span className="font-medium">
                      {formatInstallCount(mcp.installCount)}
                    </span>
                  </span>
                </>
              )}
              {mcp.rating && (
                <>
                  <span className="text-foreground-tertiary">•</span>
                  <span className="flex items-center gap-1 px-2 py-1 bg-background-primary/50 rounded-md">
                    <span className="text-yellow-400">⭐</span>
                    <span className="font-medium">
                      {typeof mcp.rating === "number"
                        ? mcp.rating.toFixed(1)
                        : mcp.rating}
                    </span>
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-foreground-secondary mb-5 line-clamp-3 min-h-[3.5rem] leading-relaxed">
          {mcp.description}
        </p>

        {/* Tags */}
        <div className="flex flex-wrap gap-2 mb-6">
          <span
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg border backdrop-blur-sm shadow-sm ${categoryColor}`}
          >
            {mcp.category}
          </span>
          <span className="px-3 py-1.5 text-xs font-semibold rounded-lg border bg-background-primary/60 text-foreground-secondary border-border/60 backdrop-blur-sm shadow-sm">
            {mcp.type.toUpperCase()}
          </span>
        </div>

        {/* Actions */}
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
      </div>
    </div>
  );
}
