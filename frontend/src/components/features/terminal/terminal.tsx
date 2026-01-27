import { useSelector } from "react-redux";
import { useTranslation } from "react-i18next";
import { RootState } from "#/store";
import { useTerminal } from "#/hooks/use-terminal";
import "@xterm/xterm/css/xterm.css";
import { useRuntimeIsReady } from "#/hooks/use-runtime-is-ready";

function Terminal() {
  const { commands } = useSelector((state: RootState) => state.cmd);
  const runtimeIsReady = useRuntimeIsReady();
  const isRuntimeInactive = !runtimeIsReady;
  const { t } = useTranslation();

  const ref = useTerminal({
    commands,
  });

  return (
    <div className="h-full p-4 min-h-0 flex-grow bg-[var(--bg-primary)]">
      {isRuntimeInactive && (
        <div className="w-full h-full flex flex-col items-center text-center justify-center gap-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--text-accent)]" />
          <div className="text-sm font-medium text-[var(--text-tertiary)] uppercase tracking-widest">
            {t("DIFF_VIEWER$WAITING_FOR_RUNTIME")}
          </div>
        </div>
      )}
      <div
        ref={ref}
        className={
          isRuntimeInactive
            ? "w-0 h-0 opacity-0 overflow-hidden"
            : "h-full w-full rounded-xl border border-[var(--border-primary)] overflow-hidden shadow-inner bg-[var(--bg-input)]"
        }
      />
    </div>
  );
}

export default Terminal;
