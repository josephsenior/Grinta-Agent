import ClientFormattedDate from "#/components/shared/ClientFormattedDate";

interface ActivityFeedItemProps {
  description: string;
  timestamp: string;
}

export function ActivityFeedItem({
  description,
  timestamp,
}: ActivityFeedItemProps) {
  return (
    <div className="py-3 border-b border-[#1a1a1a] last:border-0">
      <p className="text-sm text-[#FFFFFF] mb-1">{description}</p>
      <p className="text-xs text-[#94A3B8]">
        <ClientFormattedDate iso={timestamp} />
      </p>
    </div>
  );
}
