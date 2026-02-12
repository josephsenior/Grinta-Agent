import React from "react";
import { ExtraProps } from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import {
  Copy,
  Play,
  Save,
  MessageSquare,
  Check,
  ListOrdered,
} from "lucide-react";
import { Button } from "#/components/ui/button";
import { cn } from "#/utils/utils";
import {
  displaySuccessToast,
  displayErrorToast,
} from "#/utils/custom-toast-handlers";

interface CodeActionsProps {
  code: string;
  language?: string;
  onAskAbout?: (code: string) => void;
  onRun?: (code: string, language: string) => void;
  showLineNumbers?: boolean;
  onToggleLineNumbers?: () => void;
}

// Helper functions
function isExecutable(lang?: string): boolean {
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
}

function getFileExtension(lang?: string): string {
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
}

function CodeActions({
  code,
  language,
  onAskAbout,
  onRun,
  showLineNumbers,
  onToggleLineNumbers,
}: CodeActionsProps) {
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

      {/* Line Numbers Toggle (bolt.diy style) */}
      {onToggleLineNumbers && (
        <Button
          size="icon"
          variant="ghost"
          onClick={onToggleLineNumbers}
          className={cn(
            "h-8 w-8 bg-background-surface/80 backdrop-blur-sm border border-border-glass text-text-secondary",
            showLineNumbers
              ? "bg-primary-500/20 text-primary-500"
              : "hover:bg-primary-500/10 hover:text-primary-500",
          )}
          title={showLineNumbers ? "Hide line numbers" : "Show line numbers"}
        >
          <ListOrdered className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );
}

/**
 * Enhanced component to render code blocks in markdown with inline actions.
 */
export function enhancedCode(
  onAskAboutCode?: (code: string) => void,
  onRunCode?: (code: string, language: string) => void,
) {
  return function CodeComponent({
    children,
    className,
  }: React.ClassAttributes<HTMLElement> &
    React.HTMLAttributes<HTMLElement> &
    ExtraProps) {
    // Hooks must be called unconditionally at the top level
    const [showLineNumbers, setShowLineNumbers] = React.useState(false);

    const match = /language-(\w+)/.exec(className || "");
    const codeString = String(children).replace(/\n$/, "");

    if (!match) {
      const isMultiline = String(children).includes("\n");

      if (!isMultiline) {
        return (
          <code
            className={cn(className, "bg-[#2a3038] px-[0.4em] py-[0.2em] rounded text-[#e6edf3] border border-[#30363d]")}
          >
            {children}
          </code>
        );
      }

      return (
        <div className="relative group">
          <CodeActions
            code={codeString}
            onAskAbout={onAskAboutCode}
            onRun={onRunCode}
          />
          <pre
            className="bg-[#2a3038] p-[1em] pt-[2.5em] rounded text-[#e6edf3] border border-[#30363d] overflow-auto"
          >
            <code className={className}>{codeString}</code>
          </pre>
        </div>
      );
    }

    return (
      <div className="relative group">
        {/* Language badge (top-left, bolt.diy style) */}
        {match[1] && (
          <div className="absolute top-2 left-2 z-10">
            <span className="px-2 py-0.5 text-xs font-medium rounded-md bg-background-surface/90 backdrop-blur-sm border border-border-glass text-text-secondary">
              {match[1].toUpperCase()}
            </span>
          </div>
        )}

        <CodeActions
          code={codeString}
          language={match[1]}
          onAskAbout={onAskAboutCode}
          onRun={onRunCode}
          showLineNumbers={showLineNumbers}
          onToggleLineNumbers={() => setShowLineNumbers(!showLineNumbers)}
        />
        <div className="pt-[0.5em]">
          <SyntaxHighlighter
            className="rounded-lg"
            style={vscDarkPlus}
            language={match[1]}
            PreTag="div"
            showLineNumbers={showLineNumbers}
          >
            {codeString}
          </SyntaxHighlighter>
        </div>
      </div>
    );
  };
}

// Re-export the original code component for backward compatibility
export { code } from "./code";
