import React from "react";
import { cn } from "#/utils/utils";

const VALID_WIDTHS = ["w-1/4", "w-1/2", "w-3/4"];

function pickRandomWidth() {
  return VALID_WIDTHS[Math.floor(Math.random() * VALID_WIDTHS.length)];
}

function pickRandomNumber(from = 3, to = 5) {
  return Math.floor(Math.random() * (to - from + 1)) + from;
}

function TaskCardSkeleton(): React.ReactElement {
  const [widthClass, setWidthClass] = React.useState<string>("w-1/2");

  // Defer randomness to client after mount to avoid SSR/CSR mismatches
  React.useEffect(() => {
    setWidthClass(pickRandomWidth());
  }, []);

  return (
    <li className="py-3 border-b border-[#717888] flex items-center pr-6">
      <div className="h-5 w-8 skeleton" />

      <div className="w-full pl-8">
        <div className="h-5 w-24 skeleton mb-2" />
        <div className={cn("h-5 skeleton", widthClass)} />
      </div>

      <div className="h-5 w-16 skeleton" />
    </li>
  );
}

interface TaskGroupSkeletonProps {
  items?: number;
}

function TaskGroupSkeleton({ items = 3 }: Readonly<TaskGroupSkeletonProps>) {
  const [count, setCount] = React.useState<number>(items);
  const groupId = React.useId();

  React.useEffect(() => {
    setCount(pickRandomNumber(3, 5));
  }, []);

  return (
    <div data-testid="task-group-skeleton">
      <div className="py-3 border-b border-[#717888]">
        <div className="h-6 w-40 skeleton" />
      </div>

      <ul>
        {Array.from({ length: count }).map((_, index) => (
          <TaskCardSkeleton key={`${groupId}-task-${index}`} />
        ))}
      </ul>
    </div>
  );
}

export function TaskSuggestionsSkeleton(): React.ReactElement {
  const [groups, setGroups] = React.useState<number>(2);
  const rootId = React.useId();

  React.useEffect(() => {
    setGroups(pickRandomNumber(2, 3));
  }, []);

  return (
    <>
      {Array.from({ length: groups }).map((_, index) => (
        <TaskGroupSkeleton key={`${rootId}-group-${index}`} />
      ))}
    </>
  );
}
