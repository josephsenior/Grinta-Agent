import ArrowSendIcon from "#/icons/arrow-send.svg?react";

interface ScrollToBottomButtonProps {
  onClick: () => void;
}

export function ScrollToBottomButton({ onClick }: ScrollToBottomButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid="scroll-to-bottom"
      aria-label="Scroll to bottom"
      className="inline-flex items-center justify-center p-2 rounded-lg bg-white/6 text-foreground hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-yellow-400 transition rotate-180"
    >
      <span className="w-4 h-4">
        <ArrowSendIcon width={15} height={15} />
      </span>
    </button>
  );
}
