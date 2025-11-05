/**
 * API client for database connections
 */

import { openHands } from "./open-hands-axios";
import type {
  DatabaseConnection,
  TestConnectionRequest,
  TestConnectionResponse,
  SchemaInfo,
  QueryRequest,
  QueryResponse,
} from "#/types/database";

/**
 * List all database connections for the current user
 */
export async function listDatabaseConnections(): Promise<DatabaseConnection[]> {
  const response = await openHands.get("/api/database-connections");
  return response.data;
}

/**
 * Create a new database connection
 */
export async function createDatabaseConnection(
  connection: Omit<DatabaseConnection, "id" | "createdAt" | "updatedAt">,
): Promise<DatabaseConnection> {
  const response = await openHands.post("/api/database-connections", connection);
  return response.data.connection;
}

/**
 * Update an existing database connection
 */
export async function updateDatabaseConnection(
  connectionId: string,
  updates: Partial<DatabaseConnection>,
): Promise<DatabaseConnection> {
  const response = await openHands.patch(
    `/api/database-connections/${connectionId}`,
    updates,
  );
  return response.data.connection;
}

/**
 * Delete a database connection
 */
export async function deleteDatabaseConnection(
  connectionId: string,
): Promise<void> {
  await openHands.delete(`/api/database-connections/${connectionId}`);
}

/**
 * Get database schema (tables, collections, or keys)
 */
export async function getDatabaseSchema(
  connectionId: string,
): Promise<any> {
  const response = await openHands.get(
    `/api/database-connections/${connectionId}/schema`,
  );
  return response.data;
}

/**
 * Execute a query against a database
 */
export async function executeQuery(
  connectionId: string,
  query: string,
  limit?: number,
  timeout?: number,
): Promise<any> {
  const response = await openHands.post(
    `/api/database-connections/${connectionId}/query`,
    {
      query,
      limit: limit || 1000,
      timeout: timeout || 30,
    },
  );
  return response.data;
}

/**
 * Test a database connection (before saving)
 */
export async function testDatabaseConnection(
  request: TestConnectionRequest,
): Promise<TestConnectionResponse> {
  const response = await openHands.post(
    "/api/database-connections/test",
    request,
  );
  return response.data;
}
