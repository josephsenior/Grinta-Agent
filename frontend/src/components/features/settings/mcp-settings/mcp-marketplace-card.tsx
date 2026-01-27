import type { MCPMarketplaceItem } from "#/types/mcp-marketplace";
import { Badges } from "./mcp-marketplace-card/badges";
import { HeaderSection } from "./mcp-marketplace-card/header-section";
import { ActionsSection } from "./mcp-marketplace-card/actions-section";

const CATEGORY_COLORS: Record<string, string> = {
  browser: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  database: "bg-black/20 text-purple-400 border-purple-500/20",
  cloud: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  "ai-tools": "bg-pink-500/10 text-pink-400 border-pink-500/20",
  development: "bg-green-500/10 text-green-400 border-green-500/20",
  productivity: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
  "file-system": "bg-orange-500/10 text-orange-400 border-orange-500/20",
  "api-integration": "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  testing: "bg-red-500/10 text-red-400 border-red-500/20",
  monitoring: "bg-teal-500/10 text-teal-400 border-teal-500/20",
  security: "bg-rose-500/10 text-rose-400 border-rose-500/20",
  communication: "bg-black/20 text-violet-400 border-violet-500/20",
  other: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

interface MCPMarketplaceCardProps {
  mcp: MCPMarketplaceItem;
  isInstalled: boolean;
  onInstall: (mcp: MCPMarketplaceItem) => void;
  onViewDetails: (mcp: MCPMarketplaceItem) => void;
}

export function MCPMarketplaceCard({
  mcp,
  isInstalled,
  onInstall,
  onViewDetails,
}: MCPMarketplaceCardProps) {
  const categoryColor = CATEGORY_COLORS[mcp.category] || CATEGORY_COLORS.other;

  return (
    <div className="group relative overflow-hidden rounded-xl border border-border/50 bg-gradient-to-br from-background-secondary/80 to-background-tertiary/40 backdrop-blur-sm transition-all duration-300 hover:border-brand-500/40 hover:shadow-xl hover:shadow-brand-500/5 hover:-translate-y-1">
      <Badges featured={mcp.featured} popular={mcp.popular} />

      <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-brand-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

      <div className="relative p-6">
        <HeaderSection
          mcp={mcp}
          isInstalled={isInstalled}
          installCount={mcp.installCount}
          rating={mcp.rating}
        />

        <p className="text-sm text-foreground-secondary mb-5 line-clamp-3 min-h-[3.5rem] leading-relaxed">
          {mcp.description}
        </p>

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

        <ActionsSection
          mcp={mcp}
          isInstalled={isInstalled}
          onInstall={onInstall}
          onViewDetails={onViewDetails}
        />
      </div>
    </div>
  );
}
