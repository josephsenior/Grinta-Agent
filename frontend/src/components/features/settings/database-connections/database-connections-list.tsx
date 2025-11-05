import { Database, Trash2, Edit, CheckCircle, XCircle, Circle, Search } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useDatabaseConnections, useDeleteDatabaseConnection } from "#/hooks/query/use-database-connections";
import type { DatabaseConnection } from "#/types/database";

interface DatabaseConnectionsListProps {
  onEdit: (connection: DatabaseConnection) => void;
  onDelete: (connectionId: string) => void;
}

export function DatabaseConnectionsList({
  onEdit,
  onDelete,
}: DatabaseConnectionsListProps) {
  const navigate = useNavigate();
  const { data: connections, isLoading } = useDatabaseConnections();
  const { mutate: deleteConnection } = useDeleteDatabaseConnection();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <div className="animate-spin w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!connections || connections.length === 0) {
    return (
      <div className="text-center p-12 bg-background-secondary border border-border rounded-lg">
        <Database className="w-12 h-12 text-foreground-secondary mx-auto mb-4" />
        <h3 className="text-lg font-medium text-foreground mb-2">
          No Database Connections
        </h3>
        <p className="text-sm text-foreground-secondary">
          Add your first database connection to get started
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {Array.isArray(connections) && connections.map((connection) => (
        <div
          key={connection.id}
          className="flex items-center justify-between p-4 bg-background-secondary border border-border rounded-lg hover:border-brand-500 transition-colors group"
        >
          {/* Left: Info */}
          <div className="flex items-center gap-4 flex-1">
            <div className="p-2 bg-background-tertiary border border-border rounded-md">
              <Database className="w-5 h-5 text-violet-500" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h4 className="font-medium text-foreground">{connection.name}</h4>
                <span className="px-2 py-0.5 text-xs font-medium bg-background-tertiary border border-border rounded text-foreground-secondary">
                  {connection.type.toUpperCase()}
                </span>
              </div>
              <p className="text-sm text-foreground-secondary mt-1">
                {connection.host}:{connection.port}
                {connection.database && ` / ${connection.database}`}
              </p>
            </div>
          </div>

          {/* Center: Status */}
          <div className="flex items-center gap-2 px-4">
            {getStatusIcon(connection.status)}
            <span className={`text-sm ${getStatusColor(connection.status)}`}>
              {connection.status || "untested"}
            </span>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => navigate(`/database-browser?connection=${connection.id}`)}
              className="px-3 py-1.5 text-sm flex items-center gap-2 text-violet-500 hover:text-white hover:bg-brand-500 border border-brand-500 rounded-md transition-colors"
              title="Browse database"
            >
              <Search className="w-4 h-4" />
              Browse
            </button>
            <button
              type="button"
              onClick={() => onEdit(connection)}
              className="p-2 text-foreground-secondary hover:text-foreground hover:bg-background-tertiary rounded-md transition-colors"
              title="Edit connection"
            >
              <Edit className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={() => onDelete(connection.id)}
              className="p-2 text-foreground-secondary hover:text-error-500 hover:bg-error-500/10 rounded-md transition-colors"
              title="Delete connection"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function getStatusIcon(status?: string) {
  switch (status) {
    case "connected":
      return <CheckCircle className="w-4 h-4 text-success-500" />;
    case "error":
    case "disconnected":
      return <XCircle className="w-4 h-4 text-error-500" />;
    default:
      return <Circle className="w-4 h-4 text-foreground-secondary" />;
  }
}

function getStatusColor(status?: string): string {
  switch (status) {
    case "connected":
      return "text-success-500";
    case "error":
    case "disconnected":
      return "text-error-500";
    default:
      return "text-foreground-secondary";
  }
}

