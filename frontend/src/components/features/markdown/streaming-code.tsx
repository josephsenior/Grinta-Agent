import React from "react";
import { ExtraProps } from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Copy, Play, Save, MessageSquare, Check } from "lucide-react";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";
import {
  displaySuccessToast,
  displayErrorToast,
} from "#/utils/custom-toast-handlers";

interface StreamingCodeProps {
  code: string;
  language?: string;
  onAskAbout?: (code: string) => void;
  onRun?: (code: string, language: string) => void;
  isStreaming?: boolean;
  streamingSpeed?: number; // Characters per interval
  streamingInterval?: number; // Milliseconds between updates
}

function StreamingCodeActions({
  code,
  language,
  onAskAbout,
  onRun,
}: Omit<
  StreamingCodeProps,
  "isStreaming" | "streamingSpeed" | "streamingInterval"
>) {
  const [copied, setCopied] = React.useState(false);
  const [isVisible, setIsVisible] = React.useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      displaySuccessToast("Code copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      displayErrorToast("Failed to copy code");
    }
  };

  const handleSave = () => {
    try {
      const extension = getFileExtension(language);
      const blob = new Blob([code], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `code${extension}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      displaySuccessToast("Code saved to file");
    } catch (err) {
      displayErrorToast("Failed to save code");
    }
  };

  const handleRun = () => {
    if (onRun && language && isExecutable(language)) {
      onRun(code, language);
    }
  };

  const handleAskAbout = () => {
    if (onAskAbout) {
      onAskAbout(code);
    }
  };

  const isExecutable = (lang?: string): boolean => {
    if (!lang) return false;
    const executableLanguages = [
      "python",
      "javascript",
      "typescript",
      "bash",
      "sh",
      "shell",
    ];
    return executableLanguages.includes(lang.toLowerCase());
  };

  const getFileExtension = (lang?: string): string => {
    const extensions: Record<string, string> = {
      javascript: ".js",
      typescript: ".ts",
      python: ".py",
      java: ".java",
      cpp: ".cpp",
      c: ".c",
      rust: ".rs",
      go: ".go",
      ruby: ".rb",
      php: ".php",
      swift: ".swift",
      kotlin: ".kt",
      bash: ".sh",
      shell: ".sh",
      sh: ".sh",
      css: ".css",
      html: ".html",
      json: ".json",
      yaml: ".yaml",
      yml: ".yml",
    };
    return extensions[lang?.toLowerCase() || ""] || ".txt";
  };

  return (
    <div
      className={cn(
        "absolute top-2 right-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200",
        isVisible && "opacity-100",
      )}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {/* Copy Button */}
      <Button
        size="icon"
        variant="ghost"
        onClick={handleCopy}
        className="h-8 w-8 bg-background-surface/80 backdrop-blur-sm hover:bg-background-surface border border-border-glass text-text-secondary hover:text-text-primary"
        title="Copy code"
      >
        {copied ? (
          <Check className="h-3.5 w-3.5 text-success-500" />
        ) : (
          <Copy className="h-3.5 w-3.5" />
        )}
      </Button>

      {/* Run Button - only for executable languages */}
      {isExecutable(language) && onRun && (
        <Button
          size="icon"
          variant="ghost"
          onClick={handleRun}
          className="h-8 w-8 bg-background-surface/80 backdrop-blur-sm hover:bg-success-500/20 border border-border-glass text-text-secondary hover:text-success-500"
          title={`Run ${language} code`}
        >
          <Play className="h-3.5 w-3.5" />
        </Button>
      )}

      {/* Save to File Button */}
      <Button
        size="icon"
        variant="ghost"
        onClick={handleSave}
        className="h-8 w-8 bg-background-surface/80 backdrop-blur-sm hover:bg-brand-500/20 border border-border-glass text-text-secondary hover:text-violet-500"
        title="Save to file"
      >
        <Save className="h-3.5 w-3.5" />
      </Button>

      {/* Ask About Code Button */}
      {onAskAbout && (
        <Button
          size="icon"
          variant="ghost"
          onClick={handleAskAbout}
          className="h-8 w-8 bg-background-surface/80 backdrop-blur-sm hover:bg-primary-500/20 border border-border-glass text-text-secondary hover:text-primary-500"
          title="Ask about this code"
        >
          <MessageSquare className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );
}

function TypingCursor() {
  return (
    <span
      className="inline-block w-0.5 h-4 bg-primary-500 ml-0.5 animate-pulse"
      style={{
        animation: "blink 1s infinite",
      }}
    />
  );
}

export function StreamingCode({
  code,
  language,
  onAskAbout,
  onRun,
  isStreaming = false,
  streamingSpeed = 3,
  streamingInterval = 50,
}: StreamingCodeProps) {
  const streamingState = useStreamingCodeState({
    code,
    isStreaming,
    streamingSpeed,
    streamingInterval,
  });

  const mode = getStreamingMode({ code, language });

  if (mode === "inline") {
    return renderInlineCode({
      displayedCode: streamingState.displayedCode,
      isComplete: streamingState.isComplete,
    });
  }

  if (mode === "plainBlock") {
    return renderPlainBlock({
      displayedCode: streamingState.displayedCode,
      isComplete: streamingState.isComplete,
      language,
      onAskAbout,
      onRun,
    });
  }

  return renderSyntaxHighlightedBlock({
    displayedCode: streamingState.displayedCode,
    isComplete: streamingState.isComplete,
    language,
    onAskAbout,
    onRun,
  });
}

type StreamingCodeMode = "inline" | "plainBlock" | "syntax";

function useStreamingCodeState({
  code,
  isStreaming,
  streamingSpeed,
  streamingInterval,
}: {
  code: string;
  isStreaming: boolean;
  streamingSpeed: number;
  streamingInterval: number;
}) {
  const [displayedCode, setDisplayedCode] = React.useState("");
  const [isComplete, setIsComplete] = React.useState(!isStreaming);
  const intervalRef = React.useRef<NodeJS.Timeout | null>(null);

  React.useEffect(() => {
    if (!isStreaming) {
      setDisplayedCode(code);
      setIsComplete(true);
      return undefined;
    }

    setDisplayedCode("");
    setIsComplete(false);

    const interval = setInterval(() => {
      setDisplayedCode((previous) => {
        const nextLength = Math.min(
          previous.length + streamingSpeed,
          code.length,
        );
        const nextCode = code.slice(0, nextLength);

        if (nextLength >= code.length) {
          setIsComplete(true);
          clearInterval(interval);
        }

        return nextCode;
      });
    }, streamingInterval);

    intervalRef.current = interval;

    return () => clearInterval(interval);
  }, [code, isStreaming, streamingInterval, streamingSpeed]);

  React.useEffect(
    () => () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    },
    [],
  );

  return { displayedCode, isComplete } as const;
}

const getStreamingMode = ({
  code,
  language,
}: {
  code: string;
  language?: string;
}): StreamingCodeMode => {
  if (language) {
    return "syntax";
  }

  return code.includes("\n") ? "plainBlock" : "inline";
};

const renderInlineCode = ({
  displayedCode,
  isComplete,
}: {
  displayedCode: string;
  isComplete: boolean;
}) => (
  <code
    style={{
      backgroundColor: "#2a3038",
      padding: "0.2em 0.4em",
      borderRadius: "4px",
      color: "#e6edf3",
      border: "1px solid #30363d",
    }}
  >
    {displayedCode}
    {!isComplete && <TypingCursor />}
  </code>
);

const renderPlainBlock = ({
  displayedCode,
  isComplete,
  language,
  onAskAbout,
  onRun,
}: {
  displayedCode: string;
  isComplete: boolean;
  language?: string;
  onAskAbout?: (code: string) => void;
  onRun?: (code: string, language: string) => void;
}) => (
  <div className="relative group">
    {isComplete && (
      <StreamingCodeActions
        code={displayedCode}
        language={language}
        onAskAbout={onAskAbout}
        onRun={onRun}
      />
    )}
    <pre
      style={{
        backgroundColor: "#2a3038",
        padding: "1em",
        paddingTop: isComplete ? "2.5em" : "1em",
        borderRadius: "4px",
        color: "#e6edf3",
        border: "1px solid #30363d",
        overflow: "auto",
      }}
    >
      <code>
        {displayedCode}
        {!isComplete && <TypingCursor />}
      </code>
    </pre>
  </div>
);

const renderSyntaxHighlightedBlock = ({
  displayedCode,
  isComplete,
  language,
  onAskAbout,
  onRun,
}: {
  displayedCode: string;
  isComplete: boolean;
  language?: string;
  onAskAbout?: (code: string) => void;
  onRun?: (code: string, language: string) => void;
}) => (
  <div className="relative group">
    {isComplete && (
      <StreamingCodeActions
        code={displayedCode}
        language={language}
        onAskAbout={onAskAbout}
        onRun={onRun}
      />
    )}
    <div style={{ paddingTop: isComplete ? "0.5em" : "0" }}>
      <SyntaxHighlighter
        className="rounded-lg"
        style={vscDarkPlus}
        language={language}
        PreTag="div"
      >
        {displayedCode + (!isComplete ? "█" : "")}
      </SyntaxHighlighter>
    </div>
  </div>
);

// Enhanced streaming component for markdown integration
export function streamingCode(
  onAskAboutCode?: (code: string) => void,
  onRunCode?: (code: string, language: string) => void,
  isStreaming?: boolean,
  streamingSpeed?: number,
  streamingInterval?: number,
) {
  return function StreamingCodeComponent({
    children,
    className,
  }: React.ClassAttributes<HTMLElement> &
    React.HTMLAttributes<HTMLElement> &
    ExtraProps) {
    const match = /language-(\w+)/.exec(className || "");
    const codeString = String(children).replace(/\n$/, "");

    return (
      <StreamingCode
        code={codeString}
        language={match?.[1]}
        onAskAbout={onAskAboutCode}
        onRun={onRunCode}
        isStreaming={isStreaming}
        streamingSpeed={streamingSpeed}
        streamingInterval={streamingInterval}
      />
    );
  };
}
