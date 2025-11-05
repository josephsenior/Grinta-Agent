import React from "react";
import { Loader2, Clock, TrendingUp } from "lucide-react";
import { useSelector } from "react-redux";
import { RootState } from "#/store";
import { selectProgressData } from "#/store/streaming-slice";

interface ProgressIndicatorProps {
  operationId: string;
}

/**
 * ProgressIndicator - Shows operation progress with visual feedback
 * 
 * Features:
 * - Animated progress bar
 * - Elapsed time tracking
 * - Estimated time remaining
 * - Item counts (current/total)
 * - Status messages
 * - Smooth animations
 */
export function ProgressIndicator({ operationId }: ProgressIndicatorProps) {
  const progressData = useSelector((state: RootState) => 
    selectProgressData(state, operationId)
  );
  
  if (!progressData) {
    return null;
  }
  
  const { operation, progress, total, current, message, elapsed } = progressData;
  
  // Format time (seconds to human-readable)
  const formatTime = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };
  
  // Estimate remaining time
  const estimatedTotal = progress > 0 ? (elapsed / progress) * 100 : null;
  const remaining = estimatedTotal ? estimatedTotal - elapsed : null;
  
  return (
    <div className="progress-indicator relative rounded-lg overflow-hidden border border-border-secondary bg-gradient-to-br from-background-elevated to-background-surface my-3 shadow-sm">
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-brand-500/20 to-transparent animate-shimmer" />
      </div>
      
      {/* Content */}
      <div className="relative p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 text-violet-500 animate-spin" />
            <span className="text-sm font-semibold text-foreground">
              {operation}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-violet-500 font-mono">
              {progress.toFixed(0)}%
            </span>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="relative w-full h-2 bg-background-surface rounded-full overflow-hidden mb-3">
          {/* Background Animation */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-brand-500/10 to-transparent animate-shimmer" />
          
          {/* Progress Fill */}
          <div
            className="absolute inset-y-0 left-0 bg-gradient-to-r from-brand-500 via-accent-cyan to-brand-500 rounded-full transition-all duration-300 ease-out shadow-lg"
            style={{ 
              width: `${Math.min(100, Math.max(0, progress))}%`,
              backgroundSize: "200% 100%",
              animation: "gradient-shift 2s ease infinite"
            }}
          />
        </div>
        
        {/* Details Grid */}
        <div className="grid grid-cols-3 gap-3 text-xs">
          {/* Current/Total Items */}
          {current !== undefined && total !== undefined && (
            <div className="flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-success-500" />
              <span className="text-foreground-secondary">
                <span className="font-semibold text-foreground">{current.toLocaleString()}</span>
                {" / "}
                <span className="text-foreground-muted">{total.toLocaleString()}</span>
              </span>
            </div>
          )}
          
          {/* Elapsed Time */}
          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-accent-cyan" />
            <span className="text-foreground-secondary">
              <span className="font-medium">{formatTime(elapsed)}</span>
              <span className="text-foreground-muted ml-1">elapsed</span>
            </span>
          </div>
          
          {/* Estimated Remaining */}
          {remaining && remaining > 0 && (
            <div className="flex items-center gap-1.5 justify-end">
              <Clock className="w-3.5 h-3.5 text-warning-500" />
              <span className="text-foreground-secondary">
                <span className="font-medium">~{formatTime(remaining)}</span>
                <span className="text-foreground-muted ml-1">left</span>
              </span>
            </div>
          )}
        </div>
        
        {/* Status Message */}
        {message && (
          <div className="mt-3 px-3 py-2 bg-background-surface/50 rounded-md border border-border-subtle">
            <p className="text-xs text-foreground-secondary leading-relaxed">
              {message}
            </p>
          </div>
        )}
      </div>
      
      {/* Bottom Accent */}
      <div className="h-1 bg-gradient-to-r from-brand-500 via-accent-cyan to-brand-500" style={{ backgroundSize: "200% 100%", animation: "gradient-shift 3s ease infinite" }} />
    </div>
  );
}

/**
 * CompactProgressIndicator - Minimal progress display for inline use
 */
export function CompactProgressIndicator({ operationId }: { operationId: string }) {
  const progressData = useSelector((state: RootState) => 
    selectProgressData(state, operationId)
  );
  
  if (!progressData) {
    return null;
  }
  
  const { operation, progress } = progressData;
  
  return (
    <div className="compact-progress-indicator inline-flex items-center gap-2 px-3 py-1.5 bg-background-tertiary rounded-md border border-border-subtle">
      <Loader2 className="w-3 h-3 text-violet-500 animate-spin" />
      <span className="text-xs text-foreground-secondary">
        {operation}
      </span>
      <span className="text-xs font-mono text-violet-500 font-semibold">
        {progress.toFixed(0)}%
      </span>
    </div>
  );
}

