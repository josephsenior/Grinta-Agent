import React from "react";
import { Plus, Search, Database } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "#/components/ui/button";
import { Input } from "#/components/ui/input";
import { StatsSection } from "./stats-section";

interface HeaderSectionProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onCreateCollection: () => void;
  stats?: {
    total_collections: number;
    total_documents: number;
    total_chunks: number;
    total_size_mb: number;
  };
}

export function HeaderSection({
  searchQuery,
  onSearchChange,
  onCreateCollection,
  stats,
}: HeaderSectionProps) {
  const { t } = useTranslation();
  return (
    <div className="border-b border-border bg-background-secondary px-6 py-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Database className="w-6 h-6 text-violet-500" />
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              {t("KB$KNOWLEDGE_BASE", "Knowledge Base")}
            </h1>
            <p className="text-sm text-foreground-secondary">
              {t(
                "KB$MANAGE_COLLECTIONS_DESCRIPTION",
                "Manage your document collections and AI context",
              )}
            </p>
          </div>
        </div>
        <Button onClick={onCreateCollection}>
          <Plus className="w-4 h-4 mr-2" />
          {t("KB$NEW_COLLECTION", "New Collection")}
        </Button>
      </div>

      <StatsSection stats={stats} />

      <div className="mt-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-foreground-secondary" />
          <Input
            type="text"
            placeholder={t("KB$SEARCH_COLLECTIONS", "Search collections...")}
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>
    </div>
  );
}
