import React from "react";
import { useTranslation } from "react-i18next";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";

interface TerminalSnippetProps {
  text: string;
  status?: "success" | "error";
  timestamp?: string;
  variant?: "card" | "inline";
}

export function TerminalSnippet({
  text,
  status = "success",
  timestamp,
  variant = "card",
}: TerminalSnippetProps) {
  const { t } = useTranslation();
  const copy = async (textToCopy: string) => {
    try {
      await navigator.clipboard.writeText(textToCopy);
    } catch {
      // ignore
    }
  };
  if (variant === "inline") {
    return (
      <div className="inline-flex items-center gap-3">
        <div className="rounded-md bg-[#0b0b0c] border border-border px-3 py-2">
          <code className="font-mono text-sm text-foreground">{text}</code>
        </div>
        <button
          type="button"
          onClick={() => copy(text)}
          className="ml-2 inline-flex items-center justify-center p-1 rounded-md bg-white/6 hover:bg-white/10 text-sm"
          aria-label={t("COMMON$COPY_COMMAND", {
            defaultValue: "Copy command",
          })}
        >
          {t("COMMON$COPY", { defaultValue: "Copy" })}
        </button>
      </div>
    );
  }

  return (
    <div className="mt-2 w-full max-w-[60vw] bg-[#0b0b0c] border border-border rounded-md shadow-lg">
      <div className="px-3 py-2 border-b border-border text-xs text-stone-400 flex items-center justify-between">
        <span className="font-mono">
          {t("COMMON$COMMAND", { defaultValue: "Command" })}
        </span>
        <div className="flex items-center gap-2">
          {timestamp && (
            <span className="text-[11px] text-stone-500">
              <ClientFormattedDate
                iso={timestamp}
                options={{ hour: "2-digit", minute: "2-digit" }}
              />
            </span>
          )}
          <button
            type="button"
            onClick={() => copy(text)}
            className="inline-flex items-center justify-center p-1 rounded-md bg-white/6 hover:bg-white/10 text-sm"
            aria-label={t("COMMON$COPY_COMMAND", {
              defaultValue: "Copy command",
            })}
          >
            {t("COMMON$COPY", { defaultValue: "Copy" })}
          </button>
        </div>
      </div>

      <div className="px-2 py-2">
        <div className="mb-2 last:mb-0 flex items-center gap-3">
          <div className="w-1 bg-[#2b2b2b] rounded-full h-full" />
          <div className="flex-1">
            <div className="relative bg-transparent">
              <pre className="whitespace-pre-wrap font-mono text-sm text-foreground bg-transparent m-0 p-3 rounded-md overflow-x-auto">
                {text}
              </pre>
              <div className="absolute right-2 top-1/2 transform -translate-y-1/2">
                <span
                  className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-white text-xs ${status === "success" ? "bg-green-600" : "bg-rose-600"}`}
                >
                  {status === "success" ? "✓" : "!"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TerminalSnippet;
