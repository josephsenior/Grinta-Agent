import React from "react";
import { Card } from "#/components/ui/card";
import { LoadingSpinner } from "#/components/shared/loading-spinner";

export function SearchResultsLoading() {
  return (
    <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-12 shadow-[0_4px_20px_rgba(0,0,0,0.15)]">
      <div className="flex items-center justify-center">
        <LoadingSpinner size="medium" />
      </div>
    </Card>
  );
}
