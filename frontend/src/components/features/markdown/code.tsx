import React, { useState } from "react";
import { ExtraProps } from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Copy, Check } from "lucide-react";
import { cn } from "#/utils/utils";
import { MermaidDiagramViewer } from "#/components/features/orchestration/mermaid-diagram-viewer";

// See https://github.com/remarkjs/react-markdown?tab=readme-ov-file#use-custom-components-syntax-highlight

/**
 * Copy button component for code blocks
 */
function CopyCodeButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy code:", err);
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className={cn(
        "absolute top-2 right-2 p-1.5 rounded-md transition-all duration-200",
        "bg-background-secondary/80 hover:bg-background-secondary",
        "border border-border-subtle",
        "opacity-0 group-hover:opacity-100",
        "focus:opacity-100 focus:outline-none focus:ring-2 focus:ring-brand-500",
      )}
      title={copied ? "Copied!" : "Copy code"}
      aria-label="Copy code to clipboard"
    >
      {copied ? (
        <Check className="w-3.5 h-3.5 text-success-500" />
      ) : (
        <Copy className="w-3.5 h-3.5 text-text-secondary" />
      )}
    </button>
  );
}

/**
 * Component to render code blocks in markdown.
 */
export function code({
  children,
  className,
}: React.ClassAttributes<HTMLElement> &
  React.HTMLAttributes<HTMLElement> &
  ExtraProps) {
  const match = /language-(\w+)/.exec(className || ""); // get the language
  const codeString = String(children).replace(/\n$/, "");

  // Render Mermaid diagrams interactively
  const language = match?.[1];
  if (language === "mermaid") {
    return (
      <div className="my-4">
        <MermaidDiagramViewer
          diagram={codeString}
          className="rounded-lg border border-border"
          showExportButtons
          exportFilename="diagram"
          enableFullscreen
          enableZoom
        />
      </div>
    );
  }

  if (!match) {
    const isMultiline = String(children).includes("\n");

    if (!isMultiline) {
      return (
        <code
          className={className}
          style={{
            backgroundColor: "#2a3038",
            padding: "0.2em 0.4em",
            borderRadius: "4px",
            color: "#e6edf3",
            border: "1px solid #30363d",
          }}
        >
          {children}
        </code>
      );
    }

    return (
      <div className="relative group">
        <CopyCodeButton code={codeString} />
        <pre
          style={{
            backgroundColor: "#2a3038",
            padding: "1em",
            paddingRight: "3em", // Make room for copy button
            borderRadius: "4px",
            color: "#e6edf3",
            border: "1px solid #30363d",
            overflow: "auto",
          }}
        >
          <code className={className}>{codeString}</code>
        </pre>
      </div>
    );
  }

  return (
    <div className="relative group">
      <CopyCodeButton code={codeString} />
      <SyntaxHighlighter
        className="rounded-lg"
        style={vscDarkPlus}
        language={match?.[1]}
        PreTag="div"
      >
        {codeString}
      </SyntaxHighlighter>
    </div>
  );
}
