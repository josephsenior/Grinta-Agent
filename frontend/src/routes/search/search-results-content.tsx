import React from "react";
import { useTranslation } from "react-i18next";
import { MessageSquare, Code, FileText } from "lucide-react";
import { SearchResultCard } from "./search-result-card";

import type { SearchResults } from "#/api/search";

interface SearchResultsContentProps {
  totalResults: number;
  searchResults: {
    results: SearchResults;
  };
  onResultClick: (url: string, id: string) => void;
}

export function SearchResultsContent({
  totalResults,
  searchResults,
  onResultClick,
}: SearchResultsContentProps) {
  const { t } = useTranslation();

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-[#94A3B8]">
          {t("COMMON$RESULTS_COUNT", {
            defaultValue: `Found ${totalResults} result${totalResults !== 1 ? "s" : ""}`,
            count: totalResults,
          })}
        </p>
      </div>

      {searchResults.results.conversations &&
        searchResults.results.conversations.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-[1.5rem] font-semibold text-[#FFFFFF] leading-[1.2] flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-[#8b5cf6]" />
              Conversations
            </h3>
            <div className="space-y-3">
              {searchResults.results.conversations.map((result) => (
                <SearchResultCard
                  key={result.id}
                  icon={MessageSquare}
                  title={result.title}
                  description={result.description || ""}
                  timestamp={result.metadata?.created_at as string | undefined}
                  onClick={() => onResultClick(result.url || "", result.id)}
                />
              ))}
            </div>
          </div>
        )}

      {searchResults.results.snippets &&
        searchResults.results.snippets.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-[1.5rem] font-semibold text-[#FFFFFF] leading-[1.2] flex items-center gap-2">
              <Code className="h-5 w-5 text-[#8b5cf6]" />
              Snippets
            </h3>
            <div className="space-y-3">
              {searchResults.results.snippets.map((result) => (
                <SearchResultCard
                  key={result.id}
                  icon={Code}
                  title={result.title}
                  description={result.description || ""}
                  timestamp={result.metadata?.created_at as string | undefined}
                  onClick={() => onResultClick(result.url || "", result.id)}
                />
              ))}
            </div>
          </div>
        )}

      {searchResults.results.files &&
        searchResults.results.files.length > 0 && (
          <div className="space-y-4">
            <h3 className="text-[1.5rem] font-semibold text-[#FFFFFF] leading-[1.2] flex items-center gap-2">
              <FileText className="h-5 w-5 text-[#8b5cf6]" />
              Files
            </h3>
            <div className="space-y-3">
              {searchResults.results.files.map((result) => (
                <SearchResultCard
                  key={result.id}
                  icon={FileText}
                  title={result.title}
                  description={result.description || ""}
                  timestamp={result.metadata?.created_at as string | undefined}
                  onClick={() => onResultClick(result.url || "", result.id)}
                />
              ))}
            </div>
          </div>
        )}
    </>
  );
}
