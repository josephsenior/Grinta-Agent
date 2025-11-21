import React from "react";
import { useTranslation } from "react-i18next";
import { Card } from "#/components/ui/card";

export function SearchResultsError() {
  const { t } = useTranslation();

  return (
    <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)] text-center">
      <p className="text-sm text-[#94A3B8]">
        {t("COMMON$SEARCH_ERROR", {
          defaultValue: "An error occurred while searching.",
        })}
      </p>
    </Card>
  );
}
