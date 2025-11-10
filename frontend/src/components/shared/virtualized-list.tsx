import React, { useRef } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { cn } from "#/utils/utils";

interface VirtualizedListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  estimateSize?: number;
  overscan?: number;
  className?: string;
  itemClassName?: string;
  getItemKey?: (item: T, index: number) => string | number;
}

/**
 * High-performance virtualized list component
 * Only renders visible items, dramatically improving performance for long lists
 *
 * @example
 * <VirtualizedList
 *   items={conversations}
 *   estimateSize={100}
 *   renderItem={(conversation) => (
 *     <ConversationCard conversation={conversation} />
 *   )}
 *   getItemKey={(conversation) => conversation.id}
 * />
 */
export function VirtualizedList<T>({
  items,
  renderItem,
  estimateSize = 80,
  overscan = 5,
  className,
  itemClassName,
  getItemKey,
}: VirtualizedListProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan,
  });

  const virtualItems = virtualizer.getVirtualItems();

  return (
    <div
      ref={parentRef}
      className={cn("h-full overflow-auto", className)}
      style={{
        contain: "strict",
      }}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: "100%",
          position: "relative",
        }}
      >
        {virtualItems.map((virtualRow) => {
          const item = items[virtualRow.index];
          const key = getItemKey
            ? getItemKey(item, virtualRow.index)
            : virtualRow.index;

          return (
            <div
              key={key}
              data-index={virtualRow.index}
              className={itemClassName}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              {renderItem(item, virtualRow.index)}
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface VirtualizedGridProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  columns: number;
  estimateSize?: number;
  overscan?: number;
  className?: string;
  itemClassName?: string;
  getItemKey?: (item: T, index: number) => string | number;
}

/**
 * High-performance virtualized grid component
 * Only renders visible items in a grid layout
 *
 * @example
 * <VirtualizedGrid
 *   items={mcpServers}
 *   columns={3}
 *   estimateSize={200}
 *   renderItem={(server) => (
 *     <MCPMarketplaceCard server={server} />
 *   )}
 *   getItemKey={(server) => server.id}
 * />
 */
export function VirtualizedGrid<T>({
  items,
  renderItem,
  columns,
  estimateSize = 200,
  overscan = 3,
  className,
  itemClassName,
  getItemKey,
}: VirtualizedGridProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  // Calculate row count
  const rowCount = Math.ceil(items.length / columns);

  const virtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan,
  });

  const virtualRows = virtualizer.getVirtualItems();

  return (
    <div
      ref={parentRef}
      className={cn("h-full overflow-auto", className)}
      style={{
        contain: "strict",
      }}
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: "100%",
          position: "relative",
        }}
      >
        {virtualRows.map((virtualRow) => {
          const startIndex = virtualRow.index * columns;
          const rowItems = items.slice(startIndex, startIndex + columns);

          return (
            <div
              key={virtualRow.index}
              data-index={virtualRow.index}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
                display: "grid",
                gridTemplateColumns: `repeat(${columns}, 1fr)`,
                gap: "1rem",
              }}
            >
              {rowItems.map((item, colIndex) => {
                const itemIndex = startIndex + colIndex;
                const key = getItemKey
                  ? getItemKey(item, itemIndex)
                  : itemIndex;

                return (
                  <div key={key} className={itemClassName}>
                    {renderItem(item, itemIndex)}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
