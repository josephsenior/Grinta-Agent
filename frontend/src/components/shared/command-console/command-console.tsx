import React from "react";
import { useTranslation } from "react-i18next";
import { useWsClient } from "#/context/ws-client-provider";
import ClientFormattedDate from "#/components/shared/client-formatted-date";
import { logger } from "#/utils/logger";

function getNestedProperty(source: unknown, key: string) {
  if (source && typeof source === "object") {
    return (source as Record<string, unknown>)[key];
  }
  return undefined;
}

function extractCommandText(event: {
  args?: unknown;
  content?: unknown;
  message?: unknown;
}) {
  const props = ["command", "cmd", "shell_command", "message"];
  const { args } = event;

  const directCandidates = props
    .map((key) => getNestedProperty(args, key))
    .filter(Boolean);

  const additional = [
    event.content,
    event.message,
    typeof args === "string" ? args : undefined,
  ]
    .filter(Boolean)
    .map((value) => String(value));

  const candidates = [...directCandidates.map(String), ...additional];
  const text = candidates.join(" ").trim();
  return text || null;
}

function looksLikeShellCommand(value: string) {
  if (!value) {
    return false;
  }

  if (value.startsWith("Ran ") || value.startsWith("ran ")) {
    return true;
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

  if (shellTokens.some((token) => value.includes(token))) {
    return true;
  }

  return /\/[A-Za-z0-9_.~-]/.test(value);
}

function generateCommandId() {
  if (
    typeof crypto !== "undefined" &&
    "randomUUID" in crypto &&
    typeof (crypto as { randomUUID: () => string }).randomUUID === "function"
  ) {
    return (crypto as { randomUUID: () => string }).randomUUID();
  }
  return Math.random().toString(36).slice(2, 9);
}

function parseCommandEvent(event: unknown) {
  try {
    const normalized = event as {
      id?: string;
      args?: unknown;
      content?: unknown;
      message?: unknown;
      action?: string;
      timestamp?: string;
    };

    const text = extractCommandText(normalized);
    if (!text) {
      return null;
    }

    const shouldRecord =
      normalized.action === "run" || looksLikeShellCommand(text);
    if (!shouldRecord) {
      return null;
    }

    return {
      id: normalized.id ? String(normalized.id) : generateCommandId(),
      commandText: text,
      timestamp: normalized.timestamp ?? "",
    };
  } catch (error) {
    logger.warn("command-console: failed to parse event", error);
    return null;
  }
}

function buildCommandHistory(events: unknown[]) {
  const commands: { id: string; commandText: string; timestamp: string }[] = [];

  for (const event of events) {
    const parsed = parseCommandEvent(event);
    if (parsed) {
      commands.push(parsed);
    }
  }

  return commands.slice(-10).reverse();
}

export default function CommandConsole() {
  const { t } = useTranslation();
  const { parsedEvents } = useWsClient();
  const [open, setOpen] = React.useState(true);

  const commands = React.useMemo(
    () => buildCommandHistory(parsedEvents),
    [parsedEvents],
  );

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
