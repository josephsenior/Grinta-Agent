import React, { useEffect, useState } from "react";
import { Brain, Sparkles } from "lucide-react";
import { useSelector } from "react-redux";
import { RootState } from "#/store";
import { selectIsStreaming, selectStreamingEnabled, selectStreamContent } from "#/store/streaming-slice";
import { cn } from "#/utils/utils";

interface StreamingThoughtProps {
  // Accept either `eventId` (newer) or `streamId` (legacy tests/consumers)
  eventId?: string;
  streamId?: string;
  // Optional direct thought override (keeps backward compat)
  thought?: string;
  className?: string;
  // speed in ms per character (smaller is faster)
  speed?: number;
}

/**
 * StreamingThought - Displays agent thoughts with real-time typewriter effect
 * 
 * Features:
 * - Character-by-character streaming
 * - Smooth typewriter animation
 * - Thinking indicator icon
 * - Animated cursor while streaming
 * - Beautiful gradient background
 */
export function StreamingThought({
  eventId,
  streamId,
  thought,
  className = "",
  speed = 20,
}: StreamingThoughtProps) {
  const [displayedText, setDisplayedText] = useState("");

  const resolvedId = eventId || streamId || "";

  // Get content from streaming store (preferred) or fallback to prop
  const content = useSelector((state: RootState) =>
    resolvedId ? selectStreamContent(state, resolvedId) : String(thought || "")
  );

  // Check if this stream is actively streaming
  const isStreaming = useSelector((state: RootState) =>
    resolvedId ? selectIsStreaming(state, resolvedId) : false
  );

  const streamingEnabled = useSelector((state: RootState) =>
    selectStreamingEnabled(state)
  );
  
  // Typewriter effect (driven from resolved `content`)
  useEffect(() => {
    // If streaming is disabled or not active, show full text immediately
    if (!streamingEnabled || !isStreaming) {
      setDisplayedText(content);
      return;
    }

    // Handle empty content
    if (!content || content.length === 0) {
      setDisplayedText("");
      return;
    }

    // Character-by-character streaming
    let currentIndex = 0;
    const interval = setInterval(() => {
      currentIndex += 1;
      setDisplayedText(content.slice(0, currentIndex));

      if (currentIndex >= content.length) {
        clearInterval(interval);
      }
    }, Math.max(1, speed));
    
    return () => clearInterval(interval);
  }, [content, isStreaming, streamingEnabled, speed]);
  
  return (
    <div
      className={`group relative my-1.5 max-w-3xl ${className}`}
    >
      {/* Ultra-minimalist Container - Cursor-inspired */}
      <div className="relative flex items-start gap-2.5 py-1.5 px-2.5 rounded-md border-l border-violet-500/20 bg-violet-500/[0.02] hover:bg-violet-500/[0.04] transition-colors duration-200">
        
        {/* Subtle Icon */}
        <div className="flex-shrink-0 mt-0.5">
          <Brain className={cn(
            "w-3 h-3 text-violet-400/60 transition-all duration-300",
            isStreaming && "animate-pulse"
          )} />
        </div>
        
        {/* Thought Content - Smaller, lighter font */}
        <div className="flex-1 min-w-0">
          <p className="text-[11.5px] font-light leading-relaxed text-violet-300/70 whitespace-pre-wrap break-words tracking-wide">
            {displayedText}
            {/* Subtle cursor while streaming */}
            {isStreaming && (
              <span className="inline-block w-[1.5px] h-[12px] bg-violet-400/50 ml-0.5 align-middle animate-cursor-blink" />
            )}
          </p>
        </div>
        
        {/* Minimal streaming dots */}
        {isStreaming && (
          <div className="flex-shrink-0 flex items-center gap-0.5 mt-1">
            <div className="w-0.5 h-0.5 bg-violet-400/40 rounded-full animate-pulse" style={{ animationDelay: "0ms" }} />
            <div className="w-0.5 h-0.5 bg-violet-400/40 rounded-full animate-pulse" style={{ animationDelay: "150ms" }} />
            <div className="w-0.5 h-0.5 bg-violet-400/40 rounded-full animate-pulse" style={{ animationDelay: "300ms" }} />
          </div>
        )}
      </div>
      
      {/* Ultra-subtle progress line */}
      {isStreaming && content.length > 0 && (
        <div className="absolute bottom-0 left-0 right-0 h-[0.5px] bg-background-tertiary overflow-hidden">
          <div
            className="h-full bg-violet-400/30 transition-all duration-100 ease-linear"
            style={{ width: `${(displayedText.length / Math.max(1, content.length)) * 100}%` }}
          />
      </div>
      )}
    </div>
  );
}

/**
 * ThinkingIndicator - Minimalist thinking indicator (Cursor-style)
 * Shows when agent is generating thoughts before content appears
 */
export function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 py-2 px-3 my-2 max-w-3xl">
      {/* Minimal icon */}
      <Brain className="w-3.5 h-3.5 text-violet-500/70 animate-pulse" />
      
      {/* Simple text */}
      <span className="text-[13px] text-foreground-secondary/70 font-normal">
        Thinking
      </span>
      
      {/* Minimal animated dots */}
      <div className="flex items-center gap-0.5">
        <div className="w-1 h-1 bg-brand-500/50 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
        <div className="w-1 h-1 bg-brand-500/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
        <div className="w-1 h-1 bg-brand-500/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
      </div>
    </div>
  );
}

