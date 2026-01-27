import { InteractiveBrowser } from "#/components/features/browser/interactive-browser";

export default function BrowserTab() {
  return (
    <div className="h-full w-full bg-[var(--bg-primary)]">
      <InteractiveBrowser />
    </div>
  );
}
