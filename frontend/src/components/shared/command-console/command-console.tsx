import React from "react";
import { useTranslation } from "react-i18next";
import { useWsClient } from "#/context/ws-client-provider";
import ClientFormattedDate from "#/components/shared/ClientFormattedDate";

export default function CommandConsole() {
  const { t } = useTranslation();
  const { parsedEvents } = useWsClient();
  const [open, setOpen] = React.useState(true);

  const looksLikeShell = (s: string) => {
    if (!s) {
      return false;
    }
    const shellTokens = [
      "rm -",
      "&&",
      "||",
      "npm ",
      "yarn ",
      "docker ",
      "kubectl ",
      "/workspace/",
      "cd ",
      "git ",
      "ls ",
      "pwd",
      "echo ",
    ];
    if (s.startsWith("Ran ") || s.startsWith("ran ")) {
      return true;
    }
    for (const tk of shellTokens)
      if (s.includes(tk)) {
        return true;
      }
    if (/\/[A-Za-z0-9_.~-]/.test(s)) {
      return true;
    }
    return false;
  };

  const commands = React.useMemo(() => {
    const out: { id: string; commandText: string; timestamp: string }[] = [];
    for (const ev of parsedEvents) {
      try {
        type ParsedEvent = {
          id?: string;
          args?: unknown;
          content?: unknown;
          message?: unknown;
          action?: string;
          timestamp?: string;
        };

        const pev = ev as unknown as ParsedEvent;

        const getProp = (obj: unknown, key: string): unknown => {
          if (obj && typeof obj === "object") {
            return (obj as Record<string, unknown>)[key];
          }
          return undefined;
        };

        const args = pev?.args;

        const candidatesRaw = [
          getProp(args, "command"),
          getProp(args, "cmd"),
          getProp(args, "shell_command"),
          pev?.content,
          pev?.message,
          getProp(args, "message"),
          typeof args === "string" ? args : undefined,
        ].filter(Boolean) as unknown[];

        const candidates = candidatesRaw.map((x) => String(x));
        const text = candidates.join(" ").trim();

        if (text && (pev?.action === "run" || looksLikeShell(text))) {
          const id = pev?.id
            ? String(pev.id)
            : typeof crypto !== "undefined" &&
                typeof (crypto as any).randomUUID === "function"
              ? (crypto as any).randomUUID()
              : Math.random().toString(36).slice(2, 9);
          out.push({
            id,
            commandText: text,
            timestamp: pev?.timestamp ?? "",
          });
        }
      } catch (err) {
        // Keep a minimal diagnostic so the error isn't silently swallowed
        // which avoids ESLint no-empty and helps debugging.
        // eslint-disable-next-line no-console
        console.warn("command-console: failed to parse event", err);
      }
    }

    return out.slice(-10).reverse();
  }, [parsedEvents]);

  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // ignore
    }
  };

  if (!commands.length) {
    return null;
  }

  return (
    <div className="flex flex-col items-end">
      <div className="flex items-center">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="inline-flex items-center gap-2 px-2 py-1 rounded-md bg-white/6 hover:bg-white/10 text-sm text-foreground"
          aria-expanded={open}
        >
          <span className="font-mono text-xs">
            {t("COMMON$CMD", { defaultValue: "CMD" })}
          </span>
          <svg
            className={`w-3 h-3 transition-transform ${open ? "rotate-180" : ""}`}
            viewBox="0 0 20 20"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M5 8l5 5 5-5"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>

      {open && (
        <div className="mt-2 w-[420px] max-w-[60vw]">
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono text-xs text-stone-400">
              {t("COMMON$EXECUTED_COMMANDS", {
                defaultValue: "Executed commands",
              })}
            </span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="text-stone-400 hover:text-stone-200"
              aria-label={t("COMMON$CLOSE_COMMANDS", {
                defaultValue: "Close commands",
              })}
            >
              {/* eslint-disable-next-line i18next/no-literal-string */}
              <span aria-hidden>✕</span>
              <span className="sr-only">
                {t("COMMON$CLOSE_COMMANDS", { defaultValue: "Close commands" })}
              </span>
            </button>
          </div>
          <div className="px-2 py-2 max-h-48 overflow-y-auto">
            {commands.map((c) => (
              <div
                key={c.id}
                className="mb-2 last:mb-0 flex items-center gap-3"
              >
                <div className="w-1 bg-[#2b2b2b] rounded-full h-full" />
                <div className="flex-1">
                  <div className="relative bg-transparent">
                    <pre className="whitespace-pre-wrap font-mono text-sm text-foreground bg-transparent m-0 p-2 rounded-md overflow-x-auto">
                      {c.commandText}
                    </pre>
                    <div className="absolute right-2 top-1/2 transform -translate-y-1/2">
                      <span
                        className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-green-600 text-white text-xs"
                        aria-hidden
                      >
                        {t("COMMON$CHECK", { defaultValue: "✓" })}
                      </span>
                    </div>
                  </div>
                  {c.timestamp && (
                    <div className="text-[11px] text-stone-500 mt-1">
                      <ClientFormattedDate
                        iso={c.timestamp}
                        options={{ hour: "2-digit", minute: "2-digit" }}
                      />
                    </div>
                  )}
                </div>
                <div className="flex-shrink-0">
                  <button
                    type="button"
                    onClick={() => copy(c.commandText)}
                    className="ml-2 inline-flex items-center justify-center p-1 rounded-md bg-white/6 hover:bg-white/10 text-sm"
                    aria-label={t("COMMON$COPY_COMMAND", {
                      defaultValue: "Copy command",
                    })}
                  >
                    {t("COMMON$COPY", { defaultValue: "Copy" })}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
