/**
 * MCP Marketplace types
 */

export interface MCPMarketplaceItem {
  id: string;
  name: string;
  slug: string;
  description: string;
  longDescription?: string;
  author: string;
  icon?: string;
  category: MCPCategory;
  type: "sse" | "stdio" | "shttp";
  featured?: boolean;
  popular?: boolean;
  installCount?: number;
  rating?: number;
  version?: string;
  homepage?: string;
  repository?: string;
  documentation?: string;

  // Installation config
  config: {
    // For stdio servers
    command?: string;
    args?: string[];
    env?: Record<string, string>;

    // For SSE/SHTTP servers
    url?: string;
    requiresApiKey?: boolean;
    apiKeyDescription?: string;
  };

  // Tags for search
  tags?: string[];

  // Requirements
  requirements?: {
    os?: ("windows" | "macos" | "linux")[];
    node?: string;
    python?: string;
    other?: string[];
  };
}

export type MCPCategory =
  | "browser"
  | "database"
  | "cloud"
  | "ai-tools"
  | "development"
  | "productivity"
  | "file-system"
  | "api-integration"
  | "testing"
  | "monitoring"
  | "security"
  | "communication"
  | "other";

export interface MCPMarketplaceFilters {
  category?: MCPCategory;
  search?: string;
  type?: "sse" | "stdio" | "shttp" | "all";
  featured?: boolean;
  popular?: boolean;
}

export interface MCPMarketplaceResponse {
  items: MCPMarketplaceItem[];
  total: number;
  featured: MCPMarketplaceItem[];
  popular: MCPMarketplaceItem[];
  categories: {
    category: MCPCategory;
    count: number;
  }[];
}
