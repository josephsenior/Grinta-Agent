import { useState } from "react";
import { Play, Loader2, Database as DatabaseIcon } from "lucide-react";
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
          <span>Query Editor</span>
          <span className="text-xs opacity-70">(Ctrl+Enter to run)</span>
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
              Running...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Run Query
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
            wordWrap: "on",
            formatOnPaste: true,
            formatOnType: true,
            suggestOnTriggerCharacters: true,
            quickSuggestions: true,
            renderWhitespace: "selection",
            padding: { top: 16, bottom: 16 },
          }}
          onMount={(editor: any, monaco: any) => {
            // Add Ctrl+Enter shortcut to execute query
            editor.addAction({
              id: "execute-query",
              label: "Execute Query",
              keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter],
              run: () => {
                handleExecute();
              },
            });

            // Focus editor on mount
            editor.focus();
          }}
        />
      </div>
    </div>
  );
}
