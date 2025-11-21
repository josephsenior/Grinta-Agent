import { RefreshCw } from "lucide-react";
import { useState } from "react";
import { clearMarketplaceCache } from "#/api/mcp-marketplace";

interface MCPMarketplaceStatsProps {
  totalServers: number;
  onRefresh: () => void;
}

export function MCPMarketplaceStats({
  totalServers,
  onRefresh,
}: MCPMarketplaceStatsProps) {
  const [smitheryApiKey, setSmitheryApiKey] = useState(
    localStorage.getItem("smithery-api-key") || "",
  );

  const handleClearCache = () => {
    clearMarketplaceCache();
    onRefresh();
  };

  const handleApiKeyChange = (key: string) => {
    setSmitheryApiKey(key);
    if (key) {
      localStorage.setItem("smithery-api-key", key);
    } else {
      localStorage.removeItem("smithery-api-key");
    }
    // Refresh data when API key changes
    setTimeout(() => {
      clearMarketplaceCache();
      onRefresh();
    }, 500);
  };

  return (
    <div className="flex items-center justify-between p-4 bg-background-tertiary border border-border rounded-lg">
      <div className="flex items-center gap-6">
        <div>
          <p className="text-sm text-foreground-secondary">Total Servers</p>
          <p className="text-2xl font-bold text-foreground">{totalServers}</p>
        </div>
        <div className="h-10 w-px bg-border" />
        <div>
          <p className="text-sm text-foreground-secondary">Sources</p>
          <p className="text-sm text-foreground">
            Smithery • npm • GitHub • Official
          </p>
        </div>
        <div className="h-10 w-px bg-border" />
        <div>
          <p className="text-sm text-foreground-secondary">Cache</p>
          <p className="text-sm text-foreground">24h auto-refresh</p>
        </div>
      </div>
      <div className="flex items-center gap-3">
        {/* Smithery API Key Input */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="smithery-api-key-input"
            className="text-xs text-foreground-secondary"
          >
            Smithery API:
          </label>
          <input
            id="smithery-api-key-input"
            type="password"
            value={smitheryApiKey}
            onChange={(e) => handleApiKeyChange(e.target.value)}
            placeholder="API key for premium servers"
            className="px-2 py-1 text-xs border border-border rounded bg-background-secondary text-foreground placeholder:text-foreground-secondary focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-transparent w-40"
          />
        </div>
        <button
          type="button"
          onClick={handleClearCache}
          className="flex items-center gap-2 px-3 py-2 text-sm text-foreground-secondary hover:text-foreground bg-background-secondary hover:bg-background-primary border border-border rounded-md transition-colors"
          title="Clear cache and reload from APIs"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh Data
        </button>
      </div>
    </div>
  );
}
