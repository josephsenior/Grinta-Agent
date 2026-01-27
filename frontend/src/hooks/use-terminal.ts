import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import React from "react";
import { Command } from "#/state/command-slice";
import { useRuntimeIsReady } from "#/hooks/use-runtime-is-ready";
import { useWsClient } from "#/context/ws-client-provider";
import { getTerminalCommand } from "#/services/terminal-service";
import { parseTerminalOutput } from "#/utils/parse-terminal-output";

/*
  NOTE: Tests for this hook are indirectly covered by the tests for the XTermTerminal component.
  The reason for this is that the hook exposes a ref that requires a DOM element to be rendered.
*/

interface UseTerminalConfig {
  commands: Command[];
}

const DEFAULT_TERMINAL_CONFIG: UseTerminalConfig = {
  commands: [],
};

const renderCommand = (
  command: Command,
  terminal: Terminal,
  isUserInput: boolean = false,
) => {
  const { content, type } = command;

  // Skip rendering user input commands that come from the event stream
  // as they've already been displayed in the terminal as the user typed
  if (type === "input" && isUserInput) {
    return;
  }

  terminal.writeln(
    parseTerminalOutput(content.replaceAll("\n", "\r\n").trim()),
  );
};

// Create a persistent reference that survives component unmounts
// This ensures terminal history is preserved when navigating away and back
const persistentLastCommandIndex = { current: 0 };

export const useTerminal = ({
  commands,
}: UseTerminalConfig = DEFAULT_TERMINAL_CONFIG) => {
  const { send } = useWsClient();
  const runtimeIsReady = useRuntimeIsReady();
  const terminal = React.useRef<Terminal | null>(null);
  const fitAddon = React.useRef<FitAddon | null>(null);
  const ref = React.useRef<HTMLDivElement>(null);
  const lastCommandIndex = persistentLastCommandIndex; // Use the persistent reference
  const keyEventDisposable = React.useRef<{ dispose: () => void } | null>(null);
  const disabled = !runtimeIsReady;

  const getCssVar = (name: string, fallback: string) => {
    try {
      const val = getComputedStyle(document.documentElement).getPropertyValue(
        name,
      );
      return val ? val.trim() : fallback;
    } catch {
      return fallback;
    }
  };

  const createTerminal = () =>
    new Terminal({
      fontFamily: "Menlo, Monaco, 'Courier New', monospace",
      fontSize: 14,
      cursorBlink: true,
      cursorStyle: "block",
      theme: {
        // Use design tokens where possible, fallback to previous hex values
        background: getCssVar("--color-background-primary", "#0a0a0a"),
        foreground: getCssVar("--color-foreground", "#e0e0e0"),
        cursor: getCssVar("--color-brand-500", "#4f46e5"),
        cursorAccent: getCssVar("--color-background-primary", "#0a0a0a"),
        selectionBackground: getCssVar("--color-brand-500", "#4f46e5"),
        selectionForeground: getCssVar("--color-foreground", "#ffffff"),
        // ANSI colors - map to design tokens when available
        black: getCssVar("--color-background-primary", "#0a0a0a"),
        red: getCssVar("--color-danger-400", "#ef4444"),
        green: getCssVar("--color-success-400", "#10b981"),
        yellow: getCssVar("--color-warning-400", "#f59e0b"),
        blue: getCssVar("--color-info-500", "#3b82f6"),
        magenta: getCssVar("--color-brand-500", "#a855f7"),
        cyan: getCssVar("--color-cyan-400", "#06b6d4"),
        white: getCssVar("--color-foreground", "#e0e0e0"),
        // Bright ANSI colors
        brightBlack: getCssVar("--color-foreground-secondary", "#6b7280"),
        brightRed: getCssVar("--color-danger-300", "#f87171"),
        brightGreen: getCssVar("--color-success-300", "#34d399"),
        brightYellow: getCssVar("--color-warning-300", "#fbbf24"),
        brightBlue: getCssVar("--color-info-300", "#60a5fa"),
        brightMagenta: getCssVar("--color-brand-300", "#c084fc"),
        brightCyan: getCssVar("--color-cyan-300", "#22d3ee"),
        brightWhite: getCssVar("--color-foreground", "#ffffff"),
      },
    });

  const initializeTerminal = () => {
    if (terminal.current) {
      if (fitAddon.current) {
        terminal.current.loadAddon(fitAddon.current);
      }
      if (ref.current) {
        terminal.current.open(ref.current);
      }
    }
  };

  const copySelection = (selection: string) => {
    const clipboardItem = new ClipboardItem({
      "text/plain": new Blob([selection], { type: "text/plain" }),
    });

    // Fire-and-forget clipboard write. If it fails it's non-fatal.
    navigator.clipboard.write([clipboardItem]).catch(() => {
      /* swallow clipboard errors intentionally */
    });
  };

  const pasteSelection = (callback: (text: string) => void) => {
    navigator.clipboard
      .readText()
      .then(callback)
      .catch(() => {
        /* swallow clipboard read errors intentionally */
      });
  };

  const pasteHandler = (event: KeyboardEvent, cb: (text: string) => void) => {
    const isControlOrMetaPressed =
      event.type === "keydown" && (event.ctrlKey || event.metaKey);

    if (isControlOrMetaPressed) {
      if (event.code === "KeyV") {
        pasteSelection((text: string) => {
          terminal.current?.write(text);
          cb(text);
        });
      }

      if (event.code === "KeyC") {
        const selection = terminal.current?.getSelection();
        if (selection) {
          copySelection(selection);
        }
      }
    }

    return true;
  };

  const handleEnter = (command: string) => {
    terminal.current?.write("\r\n");
    // Don't write the command again as it will be added to the commands array
    // and rendered by the useEffect that watches commands
    send(getTerminalCommand(command));
    // Don't add the prompt here as it will be added when the command is processed
    // and the commands array is updated
  };

  const handleBackspace = (command: string) => {
    terminal.current?.write("\b \b");
    return command.slice(0, -1);
  };

  // Initialize terminal and handle cleanup
  React.useEffect(() => {
    terminal.current = createTerminal();
    fitAddon.current = new FitAddon();

    if (ref.current) {
      initializeTerminal();
      // Render all commands in array
      // This happens when we just switch to Terminal from other tabs
      if (commands.length > 0) {
        for (let i = 0; i < commands.length; i += 1) {
          if (commands[i].type === "input") {
            terminal.current.write("$ ");
          }
          // Don't pass isUserInput=true here because we're initializing the terminal
          // and need to show all previous commands
          renderCommand(commands[i], terminal.current, false);
        }
        lastCommandIndex.current = commands.length;
      }
      terminal.current.write("$ ");
    }

    return () => {
      terminal.current?.dispose();
    };
  }, []);

  React.useEffect(() => {
    if (
      terminal.current &&
      commands.length > 0 &&
      lastCommandIndex.current < commands.length
    ) {
      let lastCommandType = "";
      for (let i = lastCommandIndex.current; i < commands.length; i += 1) {
        lastCommandType = commands[i].type;
        // Pass true for isUserInput to skip rendering user input commands
        // that have already been displayed as the user typed
        renderCommand(commands[i], terminal.current, true);
      }
      lastCommandIndex.current = commands.length;
      if (lastCommandType === "output") {
        terminal.current.write("$ ");
      }
    }
  }, [commands, disabled]);

  React.useEffect(() => {
    let resizeObserver: ResizeObserver | null = null;

    resizeObserver = new ResizeObserver(() => {
      fitAddon.current?.fit();
    });

    if (ref.current) {
      resizeObserver.observe(ref.current);
    }

    return () => {
      resizeObserver?.disconnect();
    };
  }, []);

  React.useEffect(() => {
    if (terminal.current) {
      // Dispose of existing listeners if they exist
      if (keyEventDisposable.current) {
        keyEventDisposable.current.dispose();
        keyEventDisposable.current = null;
      }

      let commandBuffer = "";

      if (!disabled) {
        // Add new key event listener and store the disposable
        keyEventDisposable.current = terminal.current.onKey(
          ({ key, domEvent }) => {
            if (domEvent.key === "Enter") {
              handleEnter(commandBuffer);
              commandBuffer = "";
            } else if (domEvent.key === "Backspace") {
              if (commandBuffer.length > 0) {
                commandBuffer = handleBackspace(commandBuffer);
              }
            } else {
              // Ignore paste event
              if (key.charCodeAt(0) === 22) {
                return;
              }
              commandBuffer += key;
              terminal.current?.write(key);
            }
          },
        );

        // Add custom key handler and store the disposable
        terminal.current.attachCustomKeyEventHandler((event) =>
          pasteHandler(event, (text) => {
            commandBuffer += text;
          }),
        );
      } else {
        // Add a noop handler when disabled
        keyEventDisposable.current = terminal.current.onKey((e) => {
          e.domEvent.preventDefault();
          e.domEvent.stopPropagation();
        });
      }
    }

    return () => {
      if (keyEventDisposable.current) {
        keyEventDisposable.current.dispose();
        keyEventDisposable.current = null;
      }
    };
  }, [disabled]);

  return ref;
};
