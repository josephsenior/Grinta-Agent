import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Search, Loader2 } from "lucide-react";
import { Card } from "#/components/ui/card";
import { Button } from "#/components/ui/button";
import { Input } from "#/components/ui/input";
import { useGlobalSearch } from "#/hooks/query/use-search";
import { AppLayout } from "#/components/layout/AppLayout";
import { AuthGuard } from "#/components/features/auth/auth-guard";
import { SearchResultsLoading } from "./search/search-results-loading";
import { SearchResultsError } from "./search/search-results-error";
import { SearchResultsEmpty } from "./search/search-results-empty";
import { SearchResultsContent } from "./search/search-results-content";

/**
 * Global Search Page
 * Matches design system specifications
 */
export default function SearchPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get("q") || "";
  const initialType =
    (searchParams.get("type") as
      | "conversations"
      | "snippets"
      | "files"
      | "all"
      | null) || "all";

  const [query, setQuery] = useState(initialQuery);
  const [searchType, setSearchType] = useState<
    "conversations" | "snippets" | "files" | "all"
  >(initialType);

  const {
    data: searchResults,
    isLoading: searchLoading,
    error: searchError,
  } = useGlobalSearch(query, searchType === "all" ? undefined : searchType, 10);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      setSearchParams({ q: query, type: searchType });
    }
  };

  const handleResultClick = (url?: string, id?: string) => {
    if (url) {
      navigate(url);
    } else if (id) {
      if (searchType === "conversations" || searchType === "all") {
        navigate(`/conversations/${id}`);
      }
    }
  };

  const totalResults =
    searchResults?.total ??
    (searchResults?.results
      ? Object.values(searchResults.results).reduce(
          (sum, arr) => sum + arr.length,
          0,
        )
      : 0);

  const renderSearchResults = () => {
    if (searchLoading) {
      return <SearchResultsLoading />;
    }
    if (searchError) {
      return <SearchResultsError />;
    }
    if (totalResults === 0) {
      return <SearchResultsEmpty />;
    }
    if (!searchResults) {
      return <SearchResultsEmpty />;
    }
    return (
      <SearchResultsContent
        totalResults={totalResults}
        searchResults={searchResults}
        onResultClick={handleResultClick}
      />
    );
  };

  return (
    <AuthGuard>
      <AppLayout>
        <div className="space-y-8">
          {/* Page Title */}
          <div>
            <h1 className="text-[2.25rem] font-bold text-[#FFFFFF] leading-[1.2] mb-2">
              {t("search.globalSearch", "Global Search")}
            </h1>
            <p className="text-sm text-[#94A3B8]">
              {t(
                "search.description",
                "Search across conversations, snippets, and files in your workspace.",
              )}
            </p>
          </div>

          {/* Search Form */}
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-[#94A3B8]" />
                <Input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t(
                    "search.placeholder",
                    "Search conversations, snippets, files...",
                  )}
                  className="pl-12 pr-4 py-3 bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] placeholder:text-[#94A3B8] rounded-lg focus:border-[#8b5cf6] focus:ring-2 focus:ring-[rgba(139,92,246,0.2)]"
                />
              </div>
              <div className="flex gap-2">
                <select
                  value={searchType}
                  onChange={(e) =>
                    setSearchType(
                      e.target.value as
                        | "conversations"
                        | "snippets"
                        | "files"
                        | "all",
                    )
                  }
                  className="px-4 py-3 bg-[#000000] border border-[#1a1a1a] text-[#FFFFFF] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#8b5cf6] focus:ring-[rgba(139,92,246,0.2)]"
                >
                  <option value="all">{t("search.all", "All")}</option>
                  <option value="conversations">
                    {t("search.conversations", "Conversations")}
                  </option>
                  <option value="snippets">
                    {t("search.snippets", "Snippets")}
                  </option>
                  <option value="files">{t("search.files", "Files")}</option>
                </select>
                <Button
                  type="submit"
                  disabled={!query.trim() || searchLoading}
                  className="bg-gradient-to-r from-[#8b5cf6] to-[#7c3aed] text-white rounded-lg px-6 py-3 hover:brightness-110 active:brightness-95 disabled:opacity-50"
                >
                  {searchLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <Search className="mr-2 h-4 w-4" />
                      {t("search.search", "Search")}
                    </>
                  )}
                </Button>
              </div>
            </div>
          </form>

          {/* Search Results */}
          {query.trim() && (
            <div className="space-y-6">{renderSearchResults()}</div>
          )}

          {/* Empty State - No Search Query */}
          {!query.trim() && (
            <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)] text-center">
              <Search className="h-16 w-16 text-[#94A3B8] opacity-50 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-[#FFFFFF] mb-2">
                {t("COMMON$START_SEARCHING", {
                  defaultValue: "Start searching",
                })}
              </h3>
              <p className="text-sm text-[#94A3B8]">
                {t("COMMON$START_SEARCHING_DESCRIPTION", {
                  defaultValue:
                    "Enter a search query above to find conversations, snippets, and files.",
                })}
              </p>
            </Card>
          )}
        </div>
      </AppLayout>
    </AuthGuard>
  );
}

export const hydrateFallback = <div aria-hidden className="route-loading" />;
