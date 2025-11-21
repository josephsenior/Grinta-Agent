import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { cn } from "#/utils/utils";
import { Card } from "#/components/ui/card";
import { useGSAPHover } from "#/hooks/use-gsap-animations";

interface QuickStatCardProps {
  icon: React.ElementType;
  label: string;
  value: string | number;
  href?: string;
}

export function QuickStatCard({
  icon: Icon,
  label,
  value,
  href,
}: QuickStatCardProps) {
  const cardRef = useGSAPHover<HTMLDivElement>({
    scale: 1.02,
    y: -2,
    duration: 0.3,
  });

  const content = (
    <Card
      ref={cardRef}
      className={cn(
        "group relative overflow-hidden",
        "bg-[#000000] border border-[#1a1a1a] rounded-xl p-6",
        "shadow-[0_4px_20px_rgba(0,0,0,0.15)]",
        "transition-all duration-300",
        "hover:border-[#8b5cf6] hover:shadow-[0_8px_40px_rgba(0,0,0,0.2)]",
        href && "cursor-pointer",
      )}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs font-medium text-[#94A3B8]">
            <Icon className="h-4 w-4" />
            <span>{label}</span>
          </div>
          <p className="text-2xl font-bold text-[#FFFFFF] leading-tight">
            {value}
          </p>
        </div>
        {href && (
          <ArrowRight className="h-5 w-5 text-[#94A3B8] transition-transform group-hover:translate-x-1 group-hover:text-[#8b5cf6]" />
        )}
      </div>
    </Card>
  );

  if (href) {
    return <Link to={href}>{content}</Link>;
  }

  return content;
}
