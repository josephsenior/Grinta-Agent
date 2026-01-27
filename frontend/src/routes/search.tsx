import React from "react";
import { GlobalSearch } from "#/components/features/search/global-search";

export default function SearchRoute() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4">
      <div className="w-full max-w-2xl">
        <GlobalSearch variant="inline" />
      </div>
    </div>
  );
}
