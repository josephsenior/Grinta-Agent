import React from "react";
import { useTranslation } from "react-i18next";
import { Search } from "lucide-react";
import { Card } from "#/components/ui/card";

export function SearchResultsEmpty() {
  const { t } = useTranslation();

  return (
    <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)] text-center">
      <Search className="h-16 w-16 text-[#94A3B8] opacity-50 mx-auto mb-4" />
      <h3 className="text-lg font-semibold text-[#FFFFFF] mb-2">
        {t("COMMON$NO_RESULTS", {
          defaultValue: "No results found",
        })}
      </h3>
      <p className="text-sm text-[#94A3B8]">
        {t("COMMON$NO_RESULTS_DESCRIPTION", {
          defaultValue: "Try adjusting your search terms or filters.",
        })}
      </p>
    </Card>
  );
}
