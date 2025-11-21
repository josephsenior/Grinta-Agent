import React from "react";

export function ProgressBlock({ progress }: { progress: number }) {
  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium text-neutral-300">Progress</h4>
        <span className="text-sm text-brand-400">{progress}%</span>
      </div>
      <div className="w-full bg-neutral-800 rounded-full h-2">
        <div
          className="bg-brand-500 h-2 rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

export default ProgressBlock;
