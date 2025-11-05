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
    <div className="h-full p-3 min-h-0 flex-grow bg-background-primary">
      {isRuntimeInactive && (
        <div className="w-full h-full flex items-center text-center justify-center text-2xl text-foreground-secondary">
          {t("DIFF_VIEWER$WAITING_FOR_RUNTIME")}
        </div>
      )}
      <div
        ref={ref}
        className={
          isRuntimeInactive
            ? "w-0 h-0 opacity-0 overflow-hidden"
            : "h-full w-full rounded-lg border border-border/30 overflow-hidden"
        }
      />
    </div>
  );
}

export default Terminal;
