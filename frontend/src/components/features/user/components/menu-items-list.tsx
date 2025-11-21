interface MenuItem {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
  badge?: string;
}

interface MenuItemsListProps {
  items: MenuItem[];
}

export function MenuItemsList({ items }: MenuItemsListProps) {
  return (
    <div className="py-2">
      {items.map((item, index) => {
        const Icon = item.icon;
        return (
          <button
            key={index}
            type="button"
            onClick={item.onClick}
            className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-white/80 hover:text-white hover:bg-white/5 transition-colors"
          >
            <Icon className="h-4 w-4 text-white/60" />
            <span className="flex-1 text-left">{item.label}</span>
            {item.badge && (
              <span className="text-xs font-medium text-white/60 bg-white/10 px-2 py-0.5 rounded">
                {item.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
