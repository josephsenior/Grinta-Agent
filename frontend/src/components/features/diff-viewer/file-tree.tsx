import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import clsx from "clsx";
import { useTranslation } from "react-i18next";
import { ChevronRight, Folder, FolderOpen } from "lucide-react";
import FileIcon from "#/components/ui/file-icon";

export type GitChangeStatus = "A" | "M" | "D" | "R" | "U";
export type GitChange = { path: string; status: GitChangeStatus };

type FileNode = {
  type: "file";
  name: string;
  path: string;
  status: GitChangeStatus;
  depth: number;
};
type FolderNode = {
  type: "folder";
  name: string;
  path: string;
  children: Array<FileNode | FolderNode>;
  depth: number;
};
type Node = FileNode | FolderNode;

export type FileTreeProps = {
  changes: GitChange[];
  selected?: string | null;
  onSelect?: (path: string, status?: GitChangeStatus) => void;
  className?: string;
};

function buildTree(changes: GitChange[]): Node[] {
  const map = new Map<string, FolderNode | FileNode>();

  changes.forEach((c) => {
    // Check if path exists and is a valid string
    if (!c.path || typeof c.path !== 'string') {
      return;
    }
    
    const parts = c.path.split("/").filter(Boolean);
    if (parts.length === 0) {
      return;
    }
    if (parts.length === 1) {
      map.set(parts[0], {
        type: "file",
        name: parts[0],
        path: c.path,
        status: c.status,
        depth: 0,
      });
      return;
    }

    let cur = "";
    parts.slice(0, -1).forEach((name, i) => {
      cur = cur ? `${cur}/${name}` : name;
      if (!map.has(cur)) {
        map.set(cur, {
          type: "folder",
          name,
          path: cur,
          children: [],
          depth: i,
        });
      }
      const folder = map.get(cur) as FolderNode;
      if (i === parts.length - 2) {
        const fileName = parts[parts.length - 1];
        folder.children.push({
          type: "file",
          name: fileName,
          path: c.path,
          status: c.status,
          depth: i + 1,
        });
      }
    });
  });

  const roots = Array.from(map.values());
  roots.sort((a, b) => {
    if (a.type === b.type) {
      return a.name.localeCompare(b.name);
    }
    return a.type === "folder" ? -1 : 1;
  });
  return roots;
}

export default function FileTree({
  changes,
  selected = null,
  onSelect,
  className,
}: FileTreeProps) {
  const { t } = useTranslation();
  const tree = useMemo(() => buildTree(changes || []), [changes]);
  const [open, setOpen] = useState<Set<string>>(new Set());
  const heights = useRef(new Map<string, number>());
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!selected || typeof selected !== 'string') {
      return;
    }
    const parts = selected.split("/").slice(0, -1);
    if (parts.length === 0) {
      return;
    }
    setOpen((prev) => {
      const next = new Set(prev);
      let cur = "";
      for (const p of parts) {
        cur = cur ? `${cur}/${p}` : p;
        next.add(cur);
      }
      return next;
    });
  }, [selected]);

  const toggle = useCallback(
    (path: string) =>
      setOpen((prev) => {
        const next = new Set(prev);
        if (next.has(path)) {
          next.delete(path);
        } else {
          next.add(path);
        }
        return next;
      }),
    [],
  );

  const getStatusColor = (status: GitChangeStatus) => {
    switch (status) {
      case "A":
        return "text-emerald-400";
      case "M":
        return "text-amber-400";
      case "D":
        return "text-error-500";
      case "R":
        return "text-violet-500";
      default:
        return "text-foreground-secondary";
    }
  };

  const getStatusLabel = (status: GitChangeStatus) => {
    switch (status) {
      case "A":
        return "A";
      case "M":
        return "M";
      case "D":
        return "D";
      case "R":
        return "R";
      default:
        return "U";
    }
  };

  const renderNode = useCallback(
    (node: Node) => {
      if (node.type === "file") {
        const isSelected = node.path === selected;
        return (
          <button
            key={node.path}
            type="button"
            onClick={() => onSelect?.(node.path, node.status)}
            className={clsx(
              "group flex items-center gap-2 w-full px-2 py-1 rounded text-sm transition-all duration-150",
              "hover:bg-background-tertiary",
              isSelected && "bg-background-tertiary border-l-2 border-brand-500",
            )}
            style={{ paddingLeft: 8 + node.depth * 16 }}
          >
            <div className="flex-shrink-0">
              <FileIcon filename={node.name} size={16} status={node.status} />
            </div>
            <span
              className={clsx(
                "flex-1 truncate text-left text-xs",
                isSelected ? "text-foreground font-medium" : "text-foreground-secondary",
              )}
            >
              {node.name}
            </span>
            <span
              className={clsx(
                "flex-shrink-0 text-[10px] font-semibold",
                getStatusColor(node.status),
              )}
            >
              {getStatusLabel(node.status)}
            </span>
          </button>
        );
      }
      const isOpen = open.has(node.path);
      return (
        <div key={node.path} className="select-none">
          <button
            type="button"
            onClick={() => toggle(node.path)}
            className="group flex items-center gap-2 w-full px-2 py-1 rounded text-sm transition-all duration-150 hover:bg-background-tertiary"
            style={{ paddingLeft: 8 + node.depth * 16 }}
          >
            <ChevronRight
              className={clsx(
                "w-3 h-3 text-foreground-secondary transition-transform duration-150 flex-shrink-0",
                isOpen && "rotate-90",
              )}
            />
            {isOpen ? (
              <FolderOpen className="w-4 h-4 text-violet-500 flex-shrink-0" />
            ) : (
              <Folder className="w-4 h-4 text-foreground-secondary flex-shrink-0" />
            )}
            <span className="flex-1 truncate text-left text-xs text-foreground-secondary">
              {node.name}
            </span>
          </button>
          <div
            className={clsx("overflow-hidden transition-all duration-200")}
            ref={(el) => {
              if (el) heights.current.set(node.path, el.scrollHeight);
            }}
            style={
              isOpen
                ? {
                    maxHeight: heights.current.get(node.path) ?? 9999,
                    opacity: 1,
                  }
                : { maxHeight: 0, opacity: 0 }
            }
          >
            {node.children.map((c) => renderNode(c))}
          </div>
        </div>
      );
    },
    [open, onSelect, selected, toggle],
  );

  return (
    <div
      ref={containerRef}
      className={clsx("space-y-0.5", className)}
      role="tree"
    >
      {tree.map((n) => renderNode(n))}
    </div>
  );
}
