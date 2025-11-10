/**
 * Analytics and usage tracking types
 */

// Time period for analytics queries
export type AnalyticsPeriod = "today" | "week" | "month" | "all";

// Model usage statistics
export interface ModelUsageStats {
  modelName: string;
  requestCount: number;
  totalPromptTokens: number;
  totalCompletionTokens: number;
  totalCost: number;
  avgLatency: number;
  cacheHitTokens: number;
  cacheWriteTokens: number;
}

// Time-series data point
export interface TimeSeriesDataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

// Cost breakdown
export interface CostBreakdown {
  totalCost: number;
  byModel: Record<string, number>;
  byDay: TimeSeriesDataPoint[];
  topExpensiveConversations: Array<{
    conversationId: string;
    title: string;
    cost: number;
    timestamp: string;
  }>;
}

// Performance metrics
export interface PerformanceMetrics {
  avgResponseTime: number;
  p95ResponseTime: number;
  p99ResponseTime: number;
  slowestRequests: Array<{
    conversationId: string;
    responseId: string;
    latency: number;
    model: string;
    timestamp: string;
  }>;
  requestsByHour: TimeSeriesDataPoint[];
}

// Conversation analytics
export interface ConversationAnalytics {
  totalConversations: number;
  activeConversations: number;
  avgConversationDuration: number;
  conversationsOverTime: TimeSeriesDataPoint[];
  conversationsByTrigger: Record<string, number>;
  conversationsByStatus: Record<string, number>;
}

// File modification stats
export interface FileModificationStats {
  totalFilesModified: number;
  totalLinesAdded: number;
  totalLinesRemoved: number;
  topModifiedFiles: Array<{
    path: string;
    modifications: number;
    linesChanged: number;
  }>;
  fileTypeBreakdown: Record<string, number>;
}

// Agent activity stats
export interface AgentActivityStats {
  totalActions: number;
  actionsByType: Record<string, number>;
  successRate: number;
  errorRate: number;
  avgIterationsPerTask: number;
  topAgents: Array<{
    agentName: string;
    usageCount: number;
    successRate: number;
  }>;
}

// Productivity insights
export interface ProductivityInsights {
  estimatedTimeSaved: number; // in hours
  tasksCompleted: number;
  tasksRejected: number;
  avgTaskCompletionTime: number; // in minutes
  codeQualityTrend: number; // percentage change
  productivityScore: number; // 0-100
}

// Complete analytics dashboard data
export interface AnalyticsDashboard {
  period: AnalyticsPeriod;
  generatedAt: string;
  summary: {
    totalCost: number;
    totalTokens: number;
    totalConversations: number;
    totalRequests: number;
    avgResponseTime: number;
  };
  costs: CostBreakdown;
  performance: PerformanceMetrics;
  conversations: ConversationAnalytics;
  files: FileModificationStats;
  agents: AgentActivityStats;
  productivity: ProductivityInsights;
  models: ModelUsageStats[];
}

// Analytics filters
export interface AnalyticsFilters {
  period: AnalyticsPeriod;
  startDate?: string;
  endDate?: string;
  models?: string[];
  conversationIds?: string[];
}

// Export format
export interface AnalyticsExport {
  format: "json" | "csv" | "pdf";
  period: AnalyticsPeriod;
  sections: Array<
    | "summary"
    | "costs"
    | "performance"
    | "conversations"
    | "files"
    | "agents"
    | "productivity"
  >;
}

// Analytics summary (matches the summary field in AnalyticsDashboard)
export interface AnalyticsSummary {
  totalCost: number;
  totalTokens: number;
  totalConversations: number;
  totalRequests: number;
  avgResponseTime: number;
}
