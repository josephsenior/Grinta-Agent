import React from "react";

interface KnowledgeBaseStats {
  total_collections: number;
  total_documents: number;
  total_chunks: number;
  total_size_mb: number;
}

interface StatsSectionProps {
  stats?: KnowledgeBaseStats;
}

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-background-tertiary/50 rounded-lg p-3">
      <div className="text-2xl font-bold text-foreground">{value}</div>
      <div className="text-xs text-foreground-secondary">{label}</div>
    </div>
  );
}

export function StatsSection({ stats }: StatsSectionProps) {
  if (!stats) {
    return null;
  }

  return (
    <div className="grid grid-cols-4 gap-4">
      <StatCard label="Collections" value={stats.total_collections} />
      <StatCard label="Documents" value={stats.total_documents} />
      <StatCard label="Chunks" value={stats.total_chunks} />
      <StatCard
        label="Total Size"
        value={`${stats.total_size_mb.toFixed(1)} MB`}
      />
    </div>
  );
}
