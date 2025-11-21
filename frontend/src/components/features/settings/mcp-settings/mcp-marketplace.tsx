import {
  useState,
  useEffect,
  useMemo,
  useCallback,
  Dispatch,
  SetStateAction,
} from "react";
import { useTranslation } from "react-i18next";
import { Search, Filter, X, Sparkles, TrendingUp } from "lucide-react";
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

interface MarketplaceControllerParams {
  installedServers: string[];
}

interface MarketplaceController {
  filters: MCPMarketplaceFilters;
  searchInput: string;
  setSearchInput: (value: string) => void;
  showFilters: boolean;
  toggleFilters: () => void;
  activeFiltersCount: number;
  data: Awaited<ReturnType<typeof fetchMarketplaceMCPs>> | undefined;
  isLoading: boolean;
  error: unknown;
  refetch: () => Promise<unknown>;
  handleCategoryFilter: (category: MCPCategory) => void;
  handleTypeFilter: (type: "sse" | "stdio" | "shttp" | "all") => void;
  handleFeaturedFilter: () => void;
  handlePopularFilter: () => void;
  clearFilters: () => void;
  selectedMCP: MCPMarketplaceItem | null;
  setSelectedMCP: Dispatch<SetStateAction<MCPMarketplaceItem | null>>;
  isInstalled: (mcp: MCPMarketplaceItem) => boolean;
}

function useMarketplaceController({
  installedServers,
}: MarketplaceControllerParams): MarketplaceController {
  const [filters, setFilters] = useState<MCPMarketplaceFilters>({});
  const [searchInput, setSearchInput] = useState("");
  const [selectedMCP, setSelectedMCP] = useState<MCPMarketplaceItem | null>(
    null,
  );
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters((prev) => ({ ...prev, search: searchInput || undefined }));
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["mcp-marketplace", filters],
    queryFn: () => fetchMarketplaceMCPs(filters),
  });

  const handleCategoryFilter = useCallback((category: MCPCategory) => {
    setFilters((prev) => ({
      ...prev,
      category: prev.category === category ? undefined : category,
    }));
  }, []);

  const handleTypeFilter = useCallback(
    (type: "sse" | "stdio" | "shttp" | "all") => {
      setFilters((prev) => ({
        ...prev,
        type: type === "all" ? undefined : type,
      }));
    },
    [],
  );

  const handleFeaturedFilter = useCallback(() => {
    setFilters((prev) => ({
      ...prev,
      featured: !prev.featured,
    }));
  }, []);

  const handlePopularFilter = useCallback(() => {
    setFilters((prev) => ({
      ...prev,
      popular: !prev.popular,
    }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({});
    setSearchInput("");
  }, []);

  const isInstalled = useCallback(
    (mcp: MCPMarketplaceItem) =>
      installedServers.some(
        (name) => name.toLowerCase() === mcp.name.toLowerCase(),
      ),
    [installedServers],
  );

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (filters.category) count += 1;
    if (filters.type) count += 1;
    if (filters.featured) count += 1;
    if (filters.popular) count += 1;
    return count;
  }, [filters]);

  const toggleFilters = useCallback(() => {
    setShowFilters((prev) => !prev);
  }, []);

  return {
    filters,
    searchInput,
    setSearchInput,
    showFilters,
    toggleFilters,
    activeFiltersCount,
    data,
    isLoading,
    error,
    refetch,
    handleCategoryFilter,
    handleTypeFilter,
    handleFeaturedFilter,
    handlePopularFilter,
    clearFilters,
    selectedMCP,
    setSelectedMCP,
    isInstalled,
  };
}

function MarketplaceStatsBanner({
  data,
  onRefresh,
}: {
  data: Awaited<ReturnType<typeof fetchMarketplaceMCPs>> | undefined;
  onRefresh: () => Promise<unknown>;
}) {
  if (!data) {
    return null;
  }

  return (
    <MCPMarketplaceStats totalServers={data.total} onRefresh={onRefresh} />
  );
}

interface MarketplaceSearchBarProps {
  searchInput: string;
  setSearchInput: (value: string) => void;
  showFilters: boolean;
  toggleFilters: () => void;
  activeFiltersCount: number;
}

function MarketplaceSearchBar({
  searchInput,
  setSearchInput,
  showFilters,
  toggleFilters,
  activeFiltersCount,
}: MarketplaceSearchBarProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-3">
      <div className="flex-1 relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground-secondary pointer-events-none" />
        <input
          type="text"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
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

      <button
        type="button"
        onClick={toggleFilters}
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
  );
}

function MarketplaceQuickFilters({
  featured,
  popular,
  onToggleFeatured,
  onTogglePopular,
}: {
  featured: boolean;
  popular: boolean;
  onToggleFeatured: () => void;
  onTogglePopular: () => void;
}) {
  return (
    <div>
      <h4 className="text-sm font-medium text-foreground mb-2">
        Quick Filters
      </h4>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onToggleFeatured}
          className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
            featured
              ? "bg-brand-500/20 border-brand-500/30 text-brand-400"
              : "bg-background-tertiary border-border text-foreground-secondary hover:border-brand-500/50"
          }`}
        >
          <Sparkles className="w-3 h-3 inline mr-1" />
          Featured
        </button>
        <button
          type="button"
          onClick={onTogglePopular}
          className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
            popular
              ? "bg-accent-500/20 border-accent-500/30 text-accent-400"
              : "bg-background-tertiary border-border text-foreground-secondary hover:border-accent-500/50"
          }`}
        >
          <TrendingUp className="w-3 h-3 inline mr-1" />
          Popular
        </button>
      </div>
    </div>
  );
}

function MarketplaceTypeFilter({
  selectedType,
  onSelectType,
}: {
  selectedType: MCPMarketplaceFilters["type"];
  onSelectType: (type: "sse" | "stdio" | "shttp" | "all") => void;
}) {
  const options = ["all", "stdio", "sse", "shttp"] as const;

  return (
    <div>
      <h4 className="text-sm font-medium text-foreground mb-2">Type</h4>
      <div className="flex flex-wrap gap-2">
        {options.map((type) => {
          const isSelected =
            (type === "all" && !selectedType) || selectedType === type;
          return (
            <button
              key={type}
              type="button"
              onClick={() => onSelectType(type)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                isSelected
                  ? "bg-brand-500/20 border-brand-500/30 text-brand-400"
                  : "bg-background-tertiary border-border text-foreground-secondary hover:border-brand-500/50"
              }`}
            >
              {type === "all" ? "All Types" : type.toUpperCase()}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function MarketplaceCategoryFilter({
  selectedCategory,
  onSelectCategory,
}: {
  selectedCategory: MCPMarketplaceFilters["category"];
  onSelectCategory: (category: MCPCategory) => void;
}) {
  return (
    <div>
      <h4 className="text-sm font-medium text-foreground mb-2">Category</h4>
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => {
          const isSelected = selectedCategory === cat.value;
          return (
            <button
              key={cat.value}
              type="button"
              onClick={() => onSelectCategory(cat.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                isSelected
                  ? "bg-brand-500/20 border-brand-500/30 text-brand-400"
                  : "bg-background-tertiary border-border text-foreground-secondary hover-border-brand-500/50"
              }`}
            >
              <span className="mr-1">{cat.icon}</span>
              {cat.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function MarketplaceFilterPanel({
  controller,
}: {
  controller: MarketplaceController;
}) {
  if (!controller.showFilters) {
    return null;
  }

  return (
    <div className="bg-background-secondary border border-border rounded-lg p-4 space-y-4">
      <MarketplaceQuickFilters
        featured={controller.filters.featured ?? false}
        popular={controller.filters.popular ?? false}
        onToggleFeatured={controller.handleFeaturedFilter}
        onTogglePopular={controller.handlePopularFilter}
      />
      <MarketplaceTypeFilter
        selectedType={controller.filters.type}
        onSelectType={controller.handleTypeFilter}
      />
      <MarketplaceCategoryFilter
        selectedCategory={controller.filters.category}
        onSelectCategory={controller.handleCategoryFilter}
      />
      {controller.activeFiltersCount > 0 && (
        <button
          type="button"
          onClick={controller.clearFilters}
          className="text-sm text-brand-400 hover:text-brand-300 transition-colors"
        >
          Clear all filters
        </button>
      )}
    </div>
  );
}

function MarketplaceResultsSummary({
  isLoading,
  total,
  activeFiltersCount,
}: {
  isLoading: boolean;
  total: number;
  activeFiltersCount: number;
}) {
  return (
    <div className="flex items-center justify-between">
      <p className="text-sm text-foreground-secondary">
        {isLoading ? (
          "Loading..."
        ) : (
          <>
            {total || 0} MCP
            {total !== 1 ? "s" : ""} available
            {activeFiltersCount > 0 && " (filtered)"}
          </>
        )}
      </p>
    </div>
  );
}

function MarketplaceResultsGrid({
  controller,
  onInstall,
}: {
  controller: MarketplaceController;
  onInstall: (mcp: MCPMarketplaceItem) => void;
}) {
  if (controller.isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, index) => (
          <div
            key={index}
            className="h-72 bg-background-secondary border border-border rounded-lg animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (!controller.data || controller.data.items.length === 0) {
    return (
      <div className="py-16 text-center">
        <p className="text-foreground-secondary text-sm mb-2">No MCPs found</p>
        <button
          type="button"
          onClick={controller.clearFilters}
          className="text-sm text-brand-400 hover:text-brand-300 transition-colors"
        >
          Clear filters
        </button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {controller.data.items.map((mcp) => (
        <MCPMarketplaceCard
          key={mcp.id}
          mcp={mcp}
          isInstalled={controller.isInstalled(mcp)}
          onInstall={onInstall}
          onViewDetails={controller.setSelectedMCP}
        />
      ))}
    </div>
  );
}

function MarketplaceResultsSection({
  controller,
  onInstall,
}: {
  controller: MarketplaceController;
  onInstall: (mcp: MCPMarketplaceItem) => void;
}) {
  return (
    <div className="space-y-4">
      <MarketplaceResultsSummary
        isLoading={controller.isLoading}
        total={controller.data?.total ?? 0}
        activeFiltersCount={controller.activeFiltersCount}
      />
      <MarketplaceResultsGrid controller={controller} onInstall={onInstall} />
    </div>
  );
}

function MarketplaceDetailsModalWrapper({
  controller,
  onInstall,
}: {
  controller: MarketplaceController;
  onInstall: (mcp: MCPMarketplaceItem) => void;
}) {
  const selected = controller.selectedMCP;
  if (!selected) {
    return null;
  }

  return (
    <MCPMarketplaceDetailsModal
      mcp={selected}
      isInstalled={controller.isInstalled(selected)}
      onInstall={onInstall}
      onClose={() => controller.setSelectedMCP(null)}
    />
  );
}

export function MCPMarketplace({
  installedServers,
  onInstall,
}: MCPMarketplaceProps) {
  const controller = useMarketplaceController({ installedServers });

  const { t } = useTranslation();

  if (controller.error) {
    return (
      <div className="p-8 text-center">
        <p className="text-error-500 text-sm">
          {t(
            "Failed to load marketplace. Please try again later.",
            "Failed to load marketplace. Please try again later.",
          )}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <MarketplaceStatsBanner
        data={controller.data}
        onRefresh={controller.refetch}
      />
      <MarketplaceSearchBar
        searchInput={controller.searchInput}
        setSearchInput={controller.setSearchInput}
        showFilters={controller.showFilters}
        toggleFilters={controller.toggleFilters}
        activeFiltersCount={controller.activeFiltersCount}
      />
      <MarketplaceFilterPanel controller={controller} />
      <MarketplaceResultsSection
        controller={controller}
        onInstall={onInstall}
      />
      <MarketplaceDetailsModalWrapper
        controller={controller}
        onInstall={onInstall}
      />
    </div>
  );
}
