import { Activity } from "lucide-react";
import { Card } from "#/components/ui/card";
import { useGSAPFadeIn } from "#/hooks/use-gsap-animations";
import { ActivityFeedItem } from "./activity-feed-item";

interface ActivityFeedSectionProps {
  activityFeed: Array<{
    id: string;
    description: string;
    timestamp: string;
  }>;
  activityFeedRef: React.RefObject<HTMLDivElement | null>;
}

export function ActivityFeedSection({
  activityFeed,
  activityFeedRef,
}: ActivityFeedSectionProps) {
  const headerRef = useGSAPFadeIn<HTMLDivElement>({
    delay: 0.4,
    duration: 0.5,
  });

  if (!activityFeed || activityFeed.length === 0) {
    return null;
  }

  return (
    <div ref={activityFeedRef} className="space-y-4">
      <div ref={headerRef}>
        <h2 className="text-[1.5rem] font-semibold text-[#FFFFFF] leading-[1.2] flex items-center gap-2">
          <Activity className="h-5 w-5 text-[#8b5cf6]" />
          Activity Feed
        </h2>
      </div>
      <Card className="bg-[#000000] border border-[#1a1a1a] rounded-xl p-6 shadow-[0_4px_20px_rgba(0,0,0,0.15)]">
        <div className="space-y-0 max-h-96 overflow-y-auto">
          {activityFeed.map((item) => (
            <ActivityFeedItem
              key={item.id}
              description={item.description}
              timestamp={item.timestamp}
            />
          ))}
        </div>
      </Card>
    </div>
  );
}
