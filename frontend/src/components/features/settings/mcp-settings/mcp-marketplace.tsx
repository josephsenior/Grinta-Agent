import { useState, useEffect, useMemo } from "react";
import { Search, Filter, X, Sparkles, TrendingUp, RefreshCw } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import type {
  MCPMarketplaceItem,
  MCPCategory,
  MCPMarketplaceFilters,
} from "#/types/mcp-marketplace";
import { fetchMarketplaceMCPs } from "#/api/mcp-marketplace";
import { MCPMarketplaceCard } from "./mcp-marketplace-card";
import { MCPMarketplaceDetailsModal } from "./mcp-marketplace-details-modal";
import { MCPMarketplaceStats } from "./mcp-marketplace-stats";

interface MCPMarketplaceProps {
  installedServers: string[]; // Array of installed MCP names
  onInstall: (mcp: MCPMarketplaceItem) => void;
}

const CATEGORIES: { value: MCPCategory; label: string; icon: string }[] = [
  { value: "browser", label: "Browser", icon: "🌐" },
  { value: "database", label: "Database", icon: "🗄️" },
  { value: "cloud", label: "Cloud", icon: "☁️" },
  { value: "ai-tools", label: "AI Tools", icon: "🤖" },
  { value: "development", label: "Development", icon: "💻" },
  { value: "productivity", label: "Productivity", icon: "⚡" },
  { value: "file-system", label: "File System", icon: "📁" },
  { value: "api-integration", label: "API Integration", icon: "🔌" },
  { value: "testing", label: "Testing", icon: "🧪" },
  { value: "monitoring", label: "Monitoring", icon: "📊" },
  { value: "security", label: "Security", icon: "🔒" },
  { value: "communication", label: "Communication", icon: "💬" },
  { value: "other", label: "Other", icon: "📦" },
];

export function MCPMarketplace({
  installedServers,
  onInstall,
}: MCPMarketplaceProps) {
  const [filters, setFilters] = useState<MCPMarketplaceFilters>({});
  const [searchInput, setSearchInput] = useState("");
  const [selectedMCP, setSelectedMCP] = useState<MCPMarketplaceItem | null>(
    null,
  );
  const [showFilters, setShowFilters] = useState(false);
  const [smitheryApiKey, setSmitheryApiKey] = useState(
    localStorage.getItem('smithery-api-key') || ''
  );

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters((prev) => ({ ...prev, search: searchInput || undefined }));
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Fetch marketplace data
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["mcp-marketplace", filters],
    queryFn: () => fetchMarketplaceMCPs(filters),
  });

  const handleCategoryFilter = (category: MCPCategory) => {
    setFilters((prev) => ({
      ...prev,
      category: prev.category === category ? undefined : category,
    }));
  };

  const handleTypeFilter = (type: "sse" | "stdio" | "shttp" | "all") => {
    setFilters((prev) => ({
      ...prev,
      type: type === "all" ? undefined : type,
    }));
  };

  const handleFeaturedFilter = () => {
    setFilters((prev) => ({
      ...prev,
      featured: !prev.featured,
    }));
  };

  const handlePopularFilter = () => {
    setFilters((prev) => ({
      ...prev,
      popular: !prev.popular,
    }));
  };

  const clearFilters = () => {
    setFilters({});
    setSearchInput("");
  };

  const isInstalled = (mcp: MCPMarketplaceItem) => {
    return installedServers.some(
      (name) => name.toLowerCase() === mcp.name.toLowerCase(),
    );
  };

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (filters.category) count++;
    if (filters.type) count++;
    if (filters.featured) count++;
    if (filters.popular) count++;
    return count;
  }, [filters]);

  if (error) {
    return (
      <div className="p-8 text-center">
        <p className="text-error-500 text-sm">
          Failed to load marketplace. Please try again later.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Banner */}
      {data && (
        <MCPMarketplaceStats
          totalServers={data.total}
          onRefresh={() => refetch()}
        />
      )}

      {/* Search and Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-secondary pointer-events-none" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search MCPs..."
            className="w-full pl-10 pr-10 py-2.5 bg-background-tertiary border border-border rounded-lg text-sm text-foreground placeholder:text-foreground-secondary focus:outline-none focus:border-brand-500 transition-colors"
          />
          {searchInput && (
            <button
              type="button"
              onClick={() => setSearchInput("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground-secondary hover:text-foreground transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Filter Toggle */}
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border transition-colors ${
            showFilters || activeFiltersCount > 0
              ? "bg-brand-500/10 border-brand-500/30 text-brand-400"
              : "bg-background-tertiary border-border text-foreground-secondary hover:border-brand-500/50"
          }`}
        >
          <Filter className="w-4 h-4" />
          <span className="text-sm font-medium">Filters</span>
          {activeFiltersCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-brand-500 text-white rounded-full">
              {activeFiltersCount}
            </span>
          )}
        </button>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="bg-background-secondary border border-border rounded-lg p-4 space-y-4">
          {/* Quick Filters */}
          <div>
            <h4 className="text-sm font-medium text-foreground mb-2">
              Quick Filters
            </h4>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={handleFeaturedFilter}
                className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                  filters.featured
                    ? "bg-brand-500/20 border-brand-500/30 text-brand-400"
                    : "bg-background-tertiary border-border text-foreground-secondary hover:border-brand-500/50"
                }`}
              >
                <Sparkles className="w-3 h-3 inline mr-1" />
                Featured
              </button>
              <button
                type="button"
                onClick={handlePopularFilter}
                className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                  filters.popular
                    ? "bg-accent-500/20 border-accent-500/30 text-accent-400"
                    : "bg-background-tertiary border-border text-foreground-secondary hover:border-accent-500/50"
                }`}
              >
                <TrendingUp className="w-3 h-3 inline mr-1" />
                Popular
              </button>
            </div>
          </div>

          {/* Type Filter */}
          <div>
            <h4 className="text-sm font-medium text-foreground mb-2">Type</h4>
            <div className="flex flex-wrap gap-2">
              {(["all", "stdio", "sse", "shttp"] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => handleTypeFilter(type)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                    (type === "all" && !filters.type) || filters.type === type
                      ? "bg-brand-500/20 border-brand-500/30 text-brand-400"
                      : "bg-background-tertiary border-border text-foreground-secondary hover:border-brand-500/50"
                  }`}
                >
                  {type === "all" ? "All Types" : type.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Category Filter */}
          <div>
            <h4 className="text-sm font-medium text-foreground mb-2">
              Category
            </h4>
            <div className="flex flex-wrap gap-2">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.value}
                  type="button"
                  onClick={() => handleCategoryFilter(cat.value)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                    filters.category === cat.value
                      ? "bg-brand-500/20 border-brand-500/30 text-brand-400"
                      : "bg-background-tertiary border-border text-foreground-secondary hover:border-brand-500/50"
                  }`}
                >
                  <span className="mr-1">{cat.icon}</span>
                  {cat.label}
                </button>
              ))}
            </div>
          </div>

          {/* Clear Filters */}
          {activeFiltersCount > 0 && (
            <button
              type="button"
              onClick={clearFilters}
              className="text-sm text-brand-400 hover:text-brand-300 transition-colors"
            >
              Clear all filters
            </button>
          )}
        </div>
      )}

      {/* Results Count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-foreground-secondary">
          {isLoading ? (
            "Loading..."
          ) : (
            <>
              {data?.total || 0} MCP{data?.total !== 1 ? "s" : ""} available
              {activeFiltersCount > 0 && " (filtered)"}
            </>
          )}
        </p>
      </div>

      {/* MCP Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="h-72 bg-background-secondary border border-border rounded-lg animate-pulse"
            />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.items.map((mcp) => (
            <MCPMarketplaceCard
              key={mcp.id}
              mcp={mcp}
              isInstalled={isInstalled(mcp)}
              onInstall={onInstall}
              onViewDetails={setSelectedMCP}
            />
          ))}
        </div>
      ) : (
        <div className="py-16 text-center">
          <p className="text-foreground-secondary text-sm mb-2">
            No MCPs found
          </p>
          <button
            type="button"
            onClick={clearFilters}
            className="text-sm text-brand-400 hover:text-brand-300 transition-colors"
          >
            Clear filters
          </button>
        </div>
      )}

      {/* Details Modal */}
      {selectedMCP && (
        <MCPMarketplaceDetailsModal
          mcp={selectedMCP}
          isInstalled={isInstalled(selectedMCP)}
          onInstall={onInstall}
          onClose={() => setSelectedMCP(null)}
        />
      )}
    </div>
  );
}

