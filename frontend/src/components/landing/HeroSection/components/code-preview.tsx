import { RefObject } from "react";

interface CodePreviewProps {
  codeRef: RefObject<HTMLDivElement | null>;
}

export function CodePreview({ codeRef }: CodePreviewProps) {
  return (
    <div ref={codeRef} className="relative min-w-0">
      <div className="relative glass-effect rounded-2xl p-8 hover-lift min-w-0">
        <div className="absolute inset-0 bg-gradient-to-br from-brand-violet/20 to-transparent rounded-2xl" />
        <div className="relative space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex gap-2">
              <div className="w-3 h-3 bg-red-500 rounded-full" />
              <div className="w-3 h-3 bg-yellow-500 rounded-full" />
              <div className="w-3 h-3 bg-green-500 rounded-full" />
            </div>
            <div className="text-xs text-text-muted font-mono">agent.py</div>
          </div>
          <div className="space-y-2 font-mono text-sm">
            <div className="text-brand-violetLight">
              <span className="text-purple-400">from</span>{" "}
              <span className="text-green-400">forge</span>{" "}
              <span className="text-purple-400">import</span>{" "}
              <span className="text-blue-400">Agent</span>
            </div>
            <div className="h-px bg-border-subtle my-2" />
            <div>
              <span className="text-purple-400">agent</span>{" "}
              <span className="text-text-tertiary">=</span>{" "}
              <span className="text-blue-400">Agent</span>
              <span className="text-text-tertiary">()</span>
            </div>
            <div className="pl-4">
              <span className="text-text-tertiary">.</span>
              <span className="text-blue-300">plan</span>
              <span className="text-text-tertiary">(</span>
              <span className="text-green-400">&quot;Add feature&quot;</span>
              <span className="text-text-tertiary">)</span>
            </div>
            <div className="pl-4">
              <span className="text-text-tertiary">.</span>
              <span className="text-blue-300">execute</span>
              <span className="text-text-tertiary">()</span>
            </div>
            <div className="h-px bg-border-subtle my-2" />
            <div>
              <span className="text-green-400">✓</span>{" "}
              <span className="text-text-tertiary">
                Merge-ready diff generated
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 pt-4 text-xs text-green-400">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span>96% pass rate</span>
          </div>
        </div>
      </div>
      <div className="absolute -bottom-4 -right-4 w-32 h-32 bg-brand-violet/30 rounded-full blur-3xl" />
      <div className="absolute -top-4 -left-4 w-32 h-32 bg-blue-500/20 rounded-full blur-3xl" />
    </div>
  );
}
