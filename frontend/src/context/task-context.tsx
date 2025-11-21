import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
} from "react";

interface Task {
  id: string;
  title: string;
  status: "todo" | "in_progress" | "done" | "cancelled";
  notes?: string;
}

interface TaskContextType {
  tasks: Task[];
  updateTasks: (newTasks: Task[]) => void;
  isTaskPanelOpen: boolean;
  toggleTaskPanel: () => void;
}

const TaskContext = createContext<TaskContextType | undefined>(undefined);

export function TaskProvider({ children }: { children: React.ReactNode }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isTaskPanelOpen, setIsTaskPanelOpen] = useState(false);
  const [hasAutoOpened, setHasAutoOpened] = useState(false);
  const [isInitialLoad, setIsInitialLoad] = useState(true);

  const updateTasks = useCallback(
    (newTasks: Task[]) => {
      const previousTaskCount = tasks.length;
      setTasks(newTasks);

      // Auto-open panel ONLY when:
      // 1. Not on initial load (to prevent opening on page reload)
      // 2. Tasks are being added (not just updating existing tasks)
      // 3. Haven't auto-opened before in this session
      if (
        !isInitialLoad &&
        newTasks.length > previousTaskCount &&
        !hasAutoOpened
      ) {
        setIsTaskPanelOpen(true);
        setHasAutoOpened(true);
      }

      // Mark that initial load is complete after first update
      if (isInitialLoad) {
        setIsInitialLoad(false);
      }
    },
    [hasAutoOpened, isInitialLoad, tasks.length],
  );

  const toggleTaskPanel = useCallback(() => {
    setIsTaskPanelOpen((prev) => !prev);
  }, []);

  const contextValue = useMemo(
    () => ({
      tasks,
      updateTasks,
      isTaskPanelOpen,
      toggleTaskPanel,
    }),
    [tasks, updateTasks, isTaskPanelOpen, toggleTaskPanel],
  );

  return (
    <TaskContext.Provider value={contextValue}>{children}</TaskContext.Provider>
  );
}

export function useTasks() {
  const context = useContext(TaskContext);
  if (!context) {
    throw new Error("useTasks must be used within a TaskProvider");
  }
  return context;
}
