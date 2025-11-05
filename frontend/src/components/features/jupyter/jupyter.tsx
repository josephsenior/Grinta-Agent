import React from "react";
import { useSelector } from "react-redux";
import { useTranslation } from "react-i18next";
import { RootState } from "#/store";
import { useScrollToBottom } from "#/hooks/use-scroll-to-bottom";
import { JupyterCell } from "./jupyter-cell";
import { ScrollToBottomButton } from "#/components/shared/buttons/scroll-to-bottom-button";
import { useRuntimeIsReady } from "#/hooks/use-runtime-is-ready";

interface JupyterEditorProps {
  maxWidth: number;
}

export function JupyterEditor({ maxWidth }: JupyterEditorProps) {
  const cells = useSelector((state: RootState) => state.jupyter?.cells ?? []);
  useSelector((state: RootState) => state.agent);
  const runtimeIsReady = useRuntimeIsReady();

  const jupyterRef = React.useRef<HTMLDivElement>(null);

  const { t } = useTranslation();

  const isRuntimeInactive = !runtimeIsReady;

  const { hitBottom, scrollDomToBottom, onChatBodyScroll } =
    useScrollToBottom(jupyterRef);

  return (
    <>
      {isRuntimeInactive && (
        <div className="w-full h-full flex items-center text-center justify-center text-2xl text-foreground-secondary">
          {t("DIFF_VIEWER$WAITING_FOR_RUNTIME")}
        </div>
      )}
      {!isRuntimeInactive && (
        <div className="flex-1 h-full flex flex-col" style={{ maxWidth }}>
          <div
            data-testid="jupyter-container"
            className="flex-1 overflow-y-auto fast-smooth-scroll"
            ref={jupyterRef}
            onScroll={(e) => onChatBodyScroll(e.currentTarget)}
          >
            {cells.map((cell, index) => (
              <JupyterCell
                key={`cell-${index}-${String(cell.content).slice(0, 30)}`}
                cell={cell}
              />
            ))}
          </div>
          {!hitBottom && (
            <div className="sticky bottom-2 flex items-center justify-center">
              <ScrollToBottomButton onClick={scrollDomToBottom} />
            </div>
          )}
        </div>
      )}
    </>
  );
}
