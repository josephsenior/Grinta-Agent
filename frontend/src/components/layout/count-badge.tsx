export function CountBadge({ count }: { count: number }) {
  return (
    <span className="text-[11px] leading-5 text-base bg-brand-500 px-1 rounded-xl">
      {count}
    </span>
  );
}
