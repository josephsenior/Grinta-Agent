import React from "react";
import { Sparkles, TrendingUp } from "lucide-react";

interface BadgesProps {
  featured?: boolean;
  popular?: boolean;
}

export function Badges({ featured, popular }: BadgesProps) {
  if (!featured && !popular) {
    return null;
  }

  return (
    <div className="absolute top-4 right-4 flex gap-2 z-10">
      {featured && (
        <span className="px-2.5 py-1 text-xs font-semibold bg-gradient-to-r from-brand-500/20 to-brand-600/20 text-brand-400 rounded-full border border-brand-500/30 backdrop-blur-sm shadow-sm">
          <Sparkles className="w-3 h-3 inline mr-1" />
          Featured
        </span>
      )}
      {popular && (
        <span className="px-2.5 py-1 text-xs font-semibold bg-gradient-to-r from-accent-500/20 to-accent-600/20 text-accent-400 rounded-full border border-accent-500/30 backdrop-blur-sm shadow-sm">
          <TrendingUp className="w-3 h-3 inline mr-1" />
          Popular
        </span>
      )}
    </div>
  );
}
