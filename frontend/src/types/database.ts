/**
 * Database connection types and interfaces
 */

export type DatabaseType = "postgresql" | "mongodb" | "mysql" | "redis";

export interface DatabaseConnection {
  id: string;
  name: string;
  type: DatabaseType;
  host: string;
  port: number;
  database?: string; // Not needed for Redis
  username?: string;
  password?: string;
  ssl?: boolean;
  connectionString?: string; // Alternative to individual fields (mainly for MongoDB)
  createdAt: string;
  updatedAt: string;
  lastTested?: string;
  status?: "connected" | "disconnected" | "error" | "untested";
}

export interface PostgreSQLConfig {
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl: boolean;
}

export interface MongoDBConfig {
  connectionString: string; // mongodb://username:password@host:port/database
  database?: string;
}

export interface MySQLConfig {
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl: boolean;
}

export interface RedisConfig {
  host: string;
  port: number;
  password?: string;
  database?: number; // Redis database number (0-15)
  ssl?: boolean;
}

export interface TestConnectionRequest {
  type: DatabaseType;
  host: string;
  port: number;
  database?: string;
  username?: string;
  password?: string;
  ssl?: boolean;
  connectionString?: string;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  details?: {
    version?: string;
    serverInfo?: string;
    databases?: string[];
  };
}

export interface SchemaInfo {
  // For SQL databases (PostgreSQL, MySQL)
  tables?: Array<{
    name: string;
    schema?: string; // PostgreSQL schemas
    columns: Array<{
      name: string;
      type: string;
      nullable: boolean;
      default?: string;
      isPrimaryKey?: boolean;
      isForeignKey?: boolean;
    }>;
    indexes?: Array<{
      name: string;
      columns: string[];
      unique: boolean;
    }>;
  }>;

  // For MongoDB
  collections?: Array<{
    name: string;
    documentCount?: number;
    sampleDocument?: Record<string, unknown>;
  }>;

  // For Redis
  keys?: Array<{
    key: string;
    type: string; // string, list, set, zset, hash
    ttl?: number;
  }>;
}

export interface QueryRequest {
  connectionId: string;
  query: string;
  limit?: number;
}

export interface QueryResponse {
  success: boolean;
  data?: unknown[];
  affectedRows?: number;
  executionTime?: number;
  error?: string;
  rowCount?: number;
  columns?: string[];
}

// Query history
export interface QueryHistoryItem {
  id: string;
  connectionId: string;
  connectionName: string;
  query: string;
  executedAt: string;
  executionTime: number;
  rowCount?: number;
  success: boolean;
  error?: string;
}

// Table/Collection metadata
export interface TableColumn {
  name: string;
  type: string;
  nullable: boolean;
  default?: string;
  isPrimaryKey?: boolean;
  isForeignKey?: boolean;
  foreignKeyTable?: string;
  foreignKeyColumn?: string;
}

export interface TableInfo {
  name: string;
  schema?: string;
  columns: TableColumn[];
  indexes: Array<{
    name: string;
    columns: string[];
    unique: boolean;
    type?: string;
  }>;
  rowCount?: number;
}
