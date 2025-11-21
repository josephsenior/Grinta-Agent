import { useState } from "react";
import { Play, Loader2, Database as DatabaseIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { LazyMonaco } from "#/components/shared/lazy-monaco";
import { BrandButton } from "#/components/features/settings/brand-button";

interface QueryEditorProps {
  onExecute: (query: string) => void;
  isExecuting?: boolean;
  defaultQuery?: string;
}

export function QueryEditor({
  onExecute,
  isExecuting = false,
  defaultQuery = "",
}: QueryEditorProps) {
  const { t } = useTranslation();
  const [query, setQuery] = useState(defaultQuery);

  const handleExecute = () => {
    if (query.trim() && !isExecuting) {
      onExecute(query);
    }
  };

  const handleEditorChange = (value: string | undefined) => {
    setQuery(value || "");
  };

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-3 border-b border-border bg-background-secondary">
        <div className="flex items-center gap-2 text-sm text-foreground-secondary">
          <DatabaseIcon className="w-4 h-4" />
          <span>{t("queryEditor.title", "Query Editor")}</span>
          <span className="text-xs opacity-70">
            {t("queryEditor.shortcut", "(Ctrl+Enter to run)")}
          </span>
        </div>
        <BrandButton
          variant="primary"
          type="button"
          onClick={handleExecute}
          isDisabled={isExecuting || !query.trim()}
          testId="execute-query-button"
          className="flex items-center gap-2"
        >
          {isExecuting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              {t("queryEditor.running", "Running...")}
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              {t("queryEditor.runQuery", "Run Query")}
            </>
          )}
        </BrandButton>
      </div>

      {/* Monaco Editor with SQL syntax highlighting - Lazy loaded */}
      <div className="flex-1 overflow-hidden">
        <LazyMonaco
          value={query}
          onChange={handleEditorChange}
          language="sql"
          height="100%"
          theme="vs-dark"
          options={{
            fontFamily: "'IBM Plex Mono', 'Courier New', monospace",
            tabSize: 2,
            formatOnPaste: true,
            formatOnType: true,
            suggestOnTriggerCharacters: true,
            quickSuggestions: true,
            renderWhitespace: "selection",
            padding: { top: 16, bottom: 16 },
          }}
          onMount={(editor: unknown, monaco: unknown) => {
            // Add Ctrl+Enter shortcut to execute query
            if (
              editor &&
              typeof editor === "object" &&
              "addAction" in editor &&
              typeof editor.addAction === "function" &&
              "focus" in editor &&
              typeof editor.focus === "function" &&
              monaco &&
              typeof monaco === "object" &&
              "KeyMod" in monaco &&
              "KeyCode" in monaco
            ) {
              const monacoEditor = editor as {
                addAction: (action: {
                  id: string;
                  label: string;
                  keybindings: number[];
                  run: () => void;
                }) => void;
                focus: () => void;
              };
              const monacoInstance = monaco as {
                KeyMod: { CtrlCmd: number };
                KeyCode: { Enter: number };
              };
              // Combine key modifiers - Monaco uses bitwise OR for key combinations
              const keyBinding =
                // eslint-disable-next-line no-bitwise
                monacoInstance.KeyMod.CtrlCmd | monacoInstance.KeyCode.Enter;
              monacoEditor.addAction({
                id: "execute-query",
                label: t("queryEditor.executeQuery", "Execute Query"),
                keybindings: [keyBinding],
                run: () => {
                  handleExecute();
                },
              });

              // Focus editor on mount
              monacoEditor.focus();
            }
          }}
        />
      </div>
    </div>
  );
}
