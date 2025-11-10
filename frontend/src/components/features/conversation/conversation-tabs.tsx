import { useTranslation } from "react-i18next";
import { TbFileCode, TbTerminal2, TbWorld } from "react-icons/tb";
import { Container } from "#/components/layout/container";
import { I18nKey } from "#/i18n/declaration";
import { useRuntimeIsReady } from "#/hooks/use-runtime-is-ready";
import { TabContent } from "#/components/layout/tab-content";
import { useConversationId } from "#/hooks/use-conversation-id";

export function ConversationTabs() {
  const runtimeIsReady = useRuntimeIsReady();

  const { conversationId } = useConversationId();

  const { t } = useTranslation();

  const basePath = `/conversations/${conversationId}`;

  return (
    <Container
      className="h-full w-full lavender-gradient-border-strong"
      variant="dark"
      labels={[
        {
          label: "Files",
          to: "",
          icon: <TbFileCode className="w-4 h-4" />,
        },
        // VSCode tab hidden for cleaner, modern UI - route still accessible at /conversations/:id/vscode
        {
          label: t(I18nKey.WORKSPACE$TERMINAL_TAB_LABEL),
          to: "terminal",
          icon: <TbTerminal2 className="w-4 h-4" />,
        },
        // { label: "Jupyter", to: "jupyter", icon: <JupyterIcon /> }, // Hidden per user request
        // { label: <ServedAppLabel />, to: "served", icon: <FaServer /> }, // Hidden "App" (Beta) tab per user request
        {
          label: (
            <div className="flex items-center gap-1">
              {t(I18nKey.BROWSER$TITLE)}
            </div>
          ),
          to: "browser",
          icon: <TbWorld className="w-4 h-4" />,
        },
      ]}
    >
      {/* Use both Outlet and TabContent */}
      <div className="h-full w-full">
        <TabContent conversationPath={basePath} />
      </div>
    </Container>
  );
}
