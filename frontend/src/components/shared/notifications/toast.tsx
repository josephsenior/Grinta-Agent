import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
} from "react";
import { X, CheckCircle, AlertTriangle, Info, AlertCircle } from "lucide-react";
import { cn } from "#/utils/utils";
import { logger } from "#/utils/logger";

export type ToastType = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  dismissible?: boolean;
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => string;
  removeToast: (id: string) => void;
  clearAllToasts: () => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within a ToastProvider");
  return context;
}

interface ToastItemProps {
  toast: Toast;
}

// Presentational toast item
function ToastItem({ toast }: Readonly<ToastItemProps>) {
  const { removeToast } = useToast();
  const [isVisible, setIsVisible] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);

  const handleDismiss = useCallback(() => {
    setIsLeaving(true);
    setTimeout(() => removeToast(toast.id), 300);
  }, [removeToast, toast.id]);

  const handleAction = useCallback(() => {
    toast.action?.onClick();
    handleDismiss();
  }, [toast.action, handleDismiss]);

  useEffect(() => {
    const t = setTimeout(() => setIsVisible(true), 10);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (!toast.duration || toast.duration <= 0) return undefined;
    const t = setTimeout(() => handleDismiss(), toast.duration);
    return () => clearTimeout(t);
  }, [toast.duration, handleDismiss]);

  const typeConfig = {
    success: {
      icon: CheckCircle,
      container:
        "bg-success-DEFAULT/10 border-success-DEFAULT/20 text-success-DEFAULT",
      iconColor: "text-success-DEFAULT",
      accent: "bg-success-DEFAULT",
    },
    error: {
      icon: AlertCircle,
      container:
        "bg-danger-DEFAULT/10 border-danger-DEFAULT/20 text-danger-DEFAULT",
      iconColor: "text-danger-DEFAULT",
      accent: "bg-danger-DEFAULT",
    },
    warning: {
      icon: AlertTriangle,
      container:
        "bg-warning-DEFAULT/10 border-warning-DEFAULT/20 text-warning-DEFAULT",
      iconColor: "text-warning-DEFAULT",
      accent: "bg-warning-DEFAULT",
    },
    info: {
      icon: Info,
      container: "bg-info-DEFAULT/10 border-info-DEFAULT/20 text-info-DEFAULT",
      iconColor: "text-info-DEFAULT",
      accent: "bg-info-DEFAULT",
    },
  } as const;

  const config = typeConfig[toast.type];
  const Icon = config.icon;

  // use data-duration attribute instead of inline style

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl border p-4 shadow-lg",
        "transition-all duration-300 ease-in-out",
        config.container,
        isVisible && !isLeaving && "animate-slide-in-right",
        isLeaving && "animate-slide-out-right opacity-0 scale-95",
      )}
    >
      {toast.duration && toast.duration > 0 && (
        <div className="absolute top-0 left-0 right-0 h-1 bg-background-elevated/20">
          <div
            className={cn(
              "h-full transition-all ease-linear",
              config.accent,
              "toast-progress",
            )}
            data-duration={`${toast.duration}ms`}
          />
        </div>
      )}

      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 pt-0.5">
          <Icon className={cn("w-5 h-5", config.iconColor)} />
        </div>

        <div className="flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="text-sm font-medium">{toast.title}</div>
            <div className="text-xs text-foreground-secondary">
              {/* optional */}
            </div>
          </div>
          {toast.description && (
            <div className="text-sm text-text-secondary mt-1">
              {toast.description}
            </div>
          )}

          {toast.action && (
            <button
              type="button"
              onClick={handleAction}
              className="mt-2 text-xs font-medium underline hover:no-underline transition-all"
            >
              {toast.action.label}
            </button>
          )}
        </div>

        <div className="flex-shrink-0">
          <button
            type="button"
            onClick={handleDismiss}
            className="flex-shrink-0 p-1 rounded-lg hover:bg-background-elevated/50 transition-colors"
            title="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function ToastContainer() {
  const { toasts } = useToast();
  if (!toasts.length) return null;
  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm w-full">
      {toasts.map((t) => (
        <ToastItem key={t.id} toast={t} />
      ))}
    </div>
  );
}

interface ToastProviderProps {
  children: React.ReactNode;
  maxToasts?: number;
}

export function ToastProvider({
  children,
  maxToasts = 5,
}: Readonly<ToastProviderProps>) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const generateId = useCallback((): string => {
    try {
      if (
        typeof crypto !== "undefined" &&
        typeof (crypto as unknown as { randomUUID?: () => string })
          .randomUUID === "function"
      ) {
        return (crypto as unknown as { randomUUID: () => string }).randomUUID();
      }
    } catch (err) {
      if (process.env.NODE_ENV === "development") {
        logger.warn(
          "crypto.randomUUID failed, falling back to Math.random()",
          err,
        );
      }
    }
    return Math.random().toString(36).slice(2, 11);
  }, []);

  const addToast = useCallback(
    (toast: Omit<Toast, "id">) => {
      const id = generateId();
      const newToast: Toast = {
        id,
        duration: 5000,
        dismissible: true,
        ...toast,
      };
      setToasts((prev) => [newToast, ...prev].slice(0, maxToasts));
      return id;
    },
    [generateId, maxToasts],
  );

  const removeToast = useCallback(
    (id: string) => setToasts((prev) => prev.filter((t) => t.id !== id)),
    [],
  );
  const clearAllToasts = useCallback(() => setToasts([]), []);

  const value = React.useMemo(
    () => ({ toasts, addToast, removeToast, clearAllToasts }),
    [toasts, addToast, removeToast, clearAllToasts],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* Scoped styles to drive toast progress animation duration via data-duration attribute */}
      <style>{`
        .toast-progress[data-duration] {
          animation-name: toast-progress;
          animation-timing-function: linear;
          animation-fill-mode: forwards;
          animation-duration: var(--toast-duration, 5000ms);
        }

        @keyframes toast-progress {
          from { transform: scaleX(1); transform-origin: left; }
          to { transform: scaleX(0); }
        }
      `}</style>
      <ToastContainer />
    </ToastContext.Provider>
  );
}

// Convenience hooks
export function useToastHelpers() {
  const { addToast } = useToast();
  const success = useCallback(
    (title: string, description?: string, options?: Partial<Toast>) =>
      addToast({ type: "success", title, description, ...options }),
    [addToast],
  );
  const error = useCallback(
    (title: string, description?: string, options?: Partial<Toast>) =>
      addToast({ type: "error", title, description, ...options }),
    [addToast],
  );
  const warning = useCallback(
    (title: string, description?: string, options?: Partial<Toast>) =>
      addToast({ type: "warning", title, description, ...options }),
    [addToast],
  );
  const info = useCallback(
    (title: string, description?: string, options?: Partial<Toast>) =>
      addToast({ type: "info", title, description, ...options }),
    [addToast],
  );
  return { success, error, warning, info };
}
