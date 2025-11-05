"""Database connections management API endpoints.

Allows users to configure and test connections to various databases.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, SecretStr

from openhands.core.logger import openhands_logger as logger
from openhands.server.user_auth import get_user_settings_store

if TYPE_CHECKING:
    from openhands.storage.settings.settings_store import SettingsStore

app = APIRouter(prefix="/api/database-connections")


def _validate_query_security(query: str) -> None:
    """Validate query for security concerns.

    Args:
        query: SQL/NoSQL query string

    Raises:
        HTTPException: If query contains dangerous patterns
    """
    # Dangerous keywords that should be logged/warned
    dangerous_keywords = [
        "DROP TABLE",
        "DROP DATABASE",
        "TRUNCATE",
        "DELETE FROM",
        "ALTER TABLE",
        "GRANT",
        "REVOKE",
        "CREATE USER",
        "DROP USER",
    ]

    query_upper = query.upper()

    for keyword in dangerous_keywords:
        if keyword in query_upper:
            logger.warning(
                f"Potentially dangerous query detected: {keyword} in query (first 100 chars): {query[:100]}",
            )

    # Check for SQL injection patterns
    injection_patterns = [
        "';",  # Statement terminator
        "--",  # SQL comment
        "/*",  # Block comment start
        "*/",  # Block comment end
        "xp_",  # SQL Server extended procedures
        "sp_",  # SQL Server system procedures
    ]

    for pattern in injection_patterns:
        if pattern in query:
            logger.warning(
                f"Potential SQL injection pattern detected: {pattern} in query: {query[:100]}",
            )

    # Additional safety checks
    if query.count(";") > 5:
        logger.warning(f"Query contains multiple statements ({query.count(';')}): {query[:100]}")

    if "*" in query and ("LIMIT" not in query_upper and "TOP" not in query_upper):
        logger.warning(f"Query uses SELECT * without LIMIT: {query[:100]}")


class DatabaseType(str, Enum):
    """Supported database types."""

    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    MYSQL = "mysql"
    REDIS = "redis"


class DatabaseConnectionModel(BaseModel):
    """Database connection configuration."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = Field(..., min_length=1, max_length=100)
    type: DatabaseType
    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    database: str | None = None
    username: str | None = None
    password: SecretStr | None = None
    ssl: bool = False
    connection_string: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_tested: str | None = None
    status: str = "untested"


class TestConnectionRequest(BaseModel):
    """Request to test a database connection."""

    type: DatabaseType
    host: str
    port: int
    database: str | None = None
    username: str | None = None
    password: SecretStr | None = None
    ssl: bool = False
    connection_string: str | None = None


class TestConnectionResponse(BaseModel):
    """Response from testing a database connection."""

    success: bool
    message: str
    details: dict[str, Any] | None = None


@app.get("/")
async def list_connections(
    settings_store: Annotated[SettingsStore, Depends(get_user_settings_store)],
) -> list[dict]:
    """List all database connections for the current user."""
    settings = await settings_store.load()

    return getattr(settings, "DATABASE_CONNECTIONS", []) if settings else []


@app.post("/")
async def create_connection(
    connection: DatabaseConnectionModel,
    settings_store: Annotated[SettingsStore, Depends(get_user_settings_store)],
) -> dict:
    """Create a new database connection."""
    settings = await settings_store.load()

    if not settings:
        raise HTTPException(status_code=500, detail="Settings not found")

    # Initialize DATABASE_CONNECTIONS if it doesn't exist
    if not hasattr(settings, "DATABASE_CONNECTIONS"):
        settings.DATABASE_CONNECTIONS = []

    # Add new connection (convert to dict, handling SecretStr)
    connection_dict = connection.model_dump()
    if connection.password:
        connection_dict["password"] = connection.password.get_secret_value()

    settings.DATABASE_CONNECTIONS.append(connection_dict)

    # Save settings
    await settings_store.save(settings)

    logger.info(f"Created database connection: {connection.name} ({connection.type})")

    return {"status": "success", "connection": connection_dict}


@app.patch("/{connection_id}")
async def update_connection(
    connection_id: str,
    updates: dict,
    settings_store: Annotated[SettingsStore, Depends(get_user_settings_store)],
) -> dict:
    """Update an existing database connection."""
    settings = await settings_store.load()

    if not settings or not hasattr(settings, "DATABASE_CONNECTIONS"):
        raise HTTPException(status_code=404, detail="Connection not found")

    # Find and update the connection
    found = False
    for conn in settings.DATABASE_CONNECTIONS:
        if conn["id"] == connection_id:
            conn.update(updates)
            conn["updated_at"] = datetime.now().isoformat()
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail="Connection not found")

    await settings_store.save(settings)

    logger.info(f"Updated database connection: {connection_id}")

    return {"status": "success"}


@app.delete("/{connection_id}")
async def delete_connection(
    connection_id: str,
    settings_store: Annotated[SettingsStore, Depends(get_user_settings_store)],
) -> dict:
    """Delete a database connection."""
    settings = await settings_store.load()

    if not settings or not hasattr(settings, "DATABASE_CONNECTIONS"):
        raise HTTPException(status_code=404, detail="Connection not found")

    # Filter out the connection to delete
    original_count = len(settings.DATABASE_CONNECTIONS)
    settings.DATABASE_CONNECTIONS = [c for c in settings.DATABASE_CONNECTIONS if c["id"] != connection_id]

    if len(settings.DATABASE_CONNECTIONS) == original_count:
        raise HTTPException(status_code=404, detail="Connection not found")

    await settings_store.save(settings)

    logger.info(f"Deleted database connection: {connection_id}")

    return {"status": "success"}


@app.post("/test")
async def test_connection(request: TestConnectionRequest) -> TestConnectionResponse:
    """Test a database connection without saving it.

    Note: This is a basic implementation that doesn't actually connect to databases.
    In a production environment, you would use asyncpg, pymongo, aiomysql, etc.
    to actually test the connection.
    """
    try:
        # Basic validation
        if request.type == DatabaseType.POSTGRESQL:
            return await _test_postgresql(request)
        if request.type == DatabaseType.MONGODB:
            return await _test_mongodb(request)
        if request.type == DatabaseType.MYSQL:
            return await _test_mysql(request)
        if request.type == DatabaseType.REDIS:
            return await _test_redis(request)
        return TestConnectionResponse(
            success=False,
            message=f"Unsupported database type: {request.type}",
        )
    except Exception as e:
        logger.error(f"Error testing connection: {e!s}")
        return TestConnectionResponse(
            success=False,
            message=f"Connection test failed: {e!s}",
        )


async def _test_postgresql(request: TestConnectionRequest) -> TestConnectionResponse:
    """Test PostgreSQL connection with asyncpg."""
    try:
        # Validate required fields
        if not request.database:
            return TestConnectionResponse(
                success=False,
                message="Database name is required for PostgreSQL",
            )
        if not request.username:
            return TestConnectionResponse(
                success=False,
                message="Username is required for PostgreSQL",
            )

        try:
            import asyncpg  # noqa: F401
        except ImportError:
            return TestConnectionResponse(
                success=False,
                message="asyncpg not installed. Run: poetry add asyncpg",
            )

        # Build connection parameters
        password = request.password.get_secret_value() if request.password else ""

        # Test connection
        logger.info(
            f"Testing PostgreSQL connection to {request.host}:{request.port}/{request.database}",
        )

        conn = await asyncpg.connect(
            host=request.host,
            port=request.port,
            database=request.database,
            user=request.username,
            password=password,
            timeout=5.0,
            ssl="require" if request.ssl else "prefer",
        )

        # Get version info
        version = await conn.fetchval("SELECT version();")

        # Close connection
        await conn.close()

        logger.info("PostgreSQL connection successful")
        return TestConnectionResponse(
            success=True,
            message="Connection successful",
            details={"version": version[:50] if version else "Unknown"},
        )

    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e!s}")
        return TestConnectionResponse(
            success=False,
            message=f"Connection failed: {e!s}",
        )


async def _test_mongodb(request: TestConnectionRequest) -> TestConnectionResponse:
    """Test MongoDB connection with motor."""
    try:
        if not request.connection_string:
            return TestConnectionResponse(
                success=False,
                message="Connection string is required for MongoDB (mongodb://...)",
            )

        try:
            from motor.motor_asyncio import AsyncIOMotorClient
        except ImportError:
            return TestConnectionResponse(
                success=False,
                message="motor not installed. Run: poetry add motor",
            )

        logger.info("Testing MongoDB connection...")

        # Create client
        client = AsyncIOMotorClient(
            request.connection_string,
            serverSelectionTimeoutMS=5000,
        )

        # Test connection
        await client.admin.command("ping")
        server_info = await client.server_info()

        # Close client
        client.close()

        logger.info("MongoDB connection successful")
        return TestConnectionResponse(
            success=True,
            message="Connection successful",
            details={"version": f"MongoDB {server_info.get('version', 'Unknown')}"},
        )

    except Exception as e:
        logger.error(f"MongoDB connection failed: {e!s}")
        return TestConnectionResponse(
            success=False,
            message=f"Connection failed: {e!s}",
        )


async def _test_mysql(request: TestConnectionRequest) -> TestConnectionResponse:
    """Test MySQL connection with aiomysql."""
    try:
        if not request.database:
            return TestConnectionResponse(
                success=False,
                message="Database name is required for MySQL",
            )
        if not request.username:
            return TestConnectionResponse(
                success=False,
                message="Username is required for MySQL",
            )

        try:
            import aiomysql
        except ImportError:
            return TestConnectionResponse(
                success=False,
                message="aiomysql not installed. Run: poetry add aiomysql",
            )

        password = request.password.get_secret_value() if request.password else ""

        logger.info(
            f"Testing MySQL connection to {request.host}:{request.port}/{request.database}",
        )

        # Create connection
        conn = await aiomysql.connect(
            host=request.host,
            port=request.port,
            user=request.username,
            password=password,
            db=request.database,
            connect_timeout=5,
        )

        try:
            # Get version
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT VERSION();")
                result = await cursor.fetchone()
                version = result[0] if result else "Unknown"

            logger.info("MySQL connection successful")
            return TestConnectionResponse(
                success=True,
                message="Connection successful",
                details={"version": f"MySQL {version[:30]}"},
            )
        finally:
            conn.close()

    except Exception as e:
        logger.error(f"MySQL connection failed: {e!s}")
        return TestConnectionResponse(
            success=False,
            message=f"Connection failed: {e!s}",
        )


async def _test_redis(request: TestConnectionRequest) -> TestConnectionResponse:
    """Test Redis connection with redis-py async."""
    try:
        try:
            import redis.asyncio as redis
        except ImportError:
            return TestConnectionResponse(
                success=False,
                message="redis not installed. Run: poetry add redis",
            )

        password = request.password.get_secret_value() if request.password else None

        logger.info(f"Testing Redis connection to {request.host}:{request.port}")

        # Create Redis client
        client = redis.Redis(
            host=request.host,
            port=request.port,
            password=password,
            decode_responses=True,
            socket_connect_timeout=5,
        )

        try:
            # Test connection
            await client.ping()

            # Get server info
            info = await client.info()
            version = info.get("redis_version", "Unknown")

            logger.info("Redis connection successful")
            return TestConnectionResponse(
                success=True,
                message="Connection successful",
                details={"version": f"Redis {version}"},
            )
        finally:
            await client.close()

    except Exception as e:
        logger.error(f"Redis connection failed: {e!s}")
        return TestConnectionResponse(
            success=False,
            message=f"Connection failed: {e!s}",
        )


# ============================================================================
# SCHEMA INSPECTION ENDPOINTS
# ============================================================================


class SchemaResponse(BaseModel):
    """Schema information response."""

    tables: list[dict] | None = None
    collections: list[dict] | None = None
    keys: list[dict] | None = None


@app.get("/{connection_id}/schema")
async def get_schema(
    connection_id: str,
    settings_store: Annotated[SettingsStore, Depends(get_user_settings_store)],
) -> SchemaResponse:
    """Get database schema (tables, collections, or keys)."""
    settings = await settings_store.load()

    if not settings or not hasattr(settings, "DATABASE_CONNECTIONS"):
        raise HTTPException(status_code=404, detail="Connection not found")

    connection = next(
        (conn for conn in settings.DATABASE_CONNECTIONS if conn["id"] == connection_id),
        None,
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    db_type = connection["type"]

    try:
        if db_type in ["postgresql", "mysql"]:
            return await _get_sql_schema(connection)
        if db_type == "mongodb":
            return await _get_mongodb_schema(connection)
        if db_type == "redis":
            return await _get_redis_schema(connection)
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported database type: {db_type}",
        )
    except Exception as e:
        logger.error(f"Error fetching schema: {e!s}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch schema: {e!s}",
        ) from e


async def _get_sql_schema(connection: dict) -> SchemaResponse:
    """Get schema for SQL databases (PostgreSQL/MySQL) with real connections."""
    db_type = connection["type"]

    try:
        if db_type == "postgresql":
            return await _get_postgresql_schema(connection)
        if db_type == "mysql":
            return await _get_mysql_schema(connection)
        msg = f"Unsupported SQL database type: {db_type}"
        raise ValueError(msg)
    except ImportError as e:
        logger.error(f"Database driver not installed: {e!s}")
        # Return empty schema with error info
        return SchemaResponse(tables=[])
    except Exception as e:
        logger.error(f"Error fetching {db_type} schema: {e!s}")
        raise


async def _connect_to_postgresql(connection: dict):
    """Establish PostgreSQL connection.

    Args:
        connection: Connection configuration dict

    Returns:
        asyncpg connection object
    """
    import asyncpg

    password = connection.get("password", "")

    return await asyncpg.connect(
        host=connection["host"],
        port=connection["port"],
        database=connection["database"],
        user=connection["username"],
        password=password,
        timeout=10.0,
        ssl="require" if connection.get("ssl") else "prefer",
    )


async def _get_postgresql_schema(connection: dict) -> SchemaResponse:
    """Get real PostgreSQL schema using asyncpg.

    Args:
        connection: Connection configuration dict

    Returns:
        SchemaResponse with table information
    """
    try:
        import asyncpg  # noqa: F401
    except ImportError:
        logger.warning("asyncpg not installed, returning empty schema")
        return SchemaResponse(tables=[])

    logger.info(f"Fetching PostgreSQL schema from {connection['host']}:{connection['port']}/{connection['database']}")

    conn = await _connect_to_postgresql(connection)

    try:
        tables_result = await _fetch_table_list(conn)
        tables = await _build_table_schemas(conn, tables_result)
        return SchemaResponse(tables=tables)
    finally:
        await conn.close()


async def _fetch_table_list(conn) -> list:
    """Fetch list of tables in public schema.

    Args:
        conn: Database connection

    Returns:
        List of table rows
    """
    tables_query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """
    return await conn.fetch(tables_query)


async def _build_table_schemas(conn, tables_result: list) -> list[dict]:
    """Build complete schema for all tables.

    Args:
        conn: Database connection
        tables_result: List of table rows

    Returns:
        List of table schema dictionaries
    """
    tables = []

    for table_row in tables_result:
        table_name = table_row["table_name"]
        table_schema = await _build_single_table_schema(conn, table_name)
        tables.append(table_schema)

    return tables


async def _build_single_table_schema(conn, table_name: str) -> dict:
    """Build schema for a single table.

    Args:
        conn: Database connection
        table_name: Name of table

    Returns:
        Table schema dictionary
    """
    columns_result, pk_columns, fk_map, indexes_map = await _fetch_table_metadata(conn, table_name)
    row_count = await _get_table_row_count(conn, table_name)
    columns = _build_column_list(columns_result, pk_columns, fk_map)

    return {
        "name": table_name,
        "schema": "public",
        "columns": columns,
        "indexes": list(indexes_map.values()),
        "rowCount": row_count,
    }


async def _fetch_table_metadata(conn, table_name: str) -> tuple:
    """Fetch all metadata for a table.

    Args:
        conn: Database connection
        table_name: Table name

    Returns:
        Tuple of (columns_result, pk_columns, fk_map, indexes_map)
    """
    # Fetch columns
    columns_query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        ORDER BY ordinal_position;
    """
    columns_result = await conn.fetch(columns_query, table_name)

    # Fetch primary keys
    pk_query = """
        SELECT a.attname
        FROM pg_index i
        JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
        WHERE i.indrelid = $1::regclass AND i.indisprimary;
    """
    pk_result = await conn.fetch(pk_query, table_name)
    pk_columns = {row["attname"] for row in pk_result}

    # Fetch foreign keys
    fk_query = """
        SELECT
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = $1;
    """
    fk_result = await conn.fetch(fk_query, table_name)
    fk_map = {
        row["column_name"]: {
            "table": row["foreign_table_name"],
            "column": row["foreign_column_name"],
        }
        for row in fk_result
    }

    # Fetch and group indexes
    indexes_map = await _fetch_and_group_indexes(conn, table_name)

    return columns_result, pk_columns, fk_map, indexes_map


async def _fetch_and_group_indexes(conn, table_name: str) -> dict:
    """Fetch and group indexes for a table.

    Args:
        conn: Database connection
        table_name: Table name

    Returns:
        Dictionary mapping index names to index info
    """
    idx_query = """
        SELECT
            i.relname as index_name,
            a.attname as column_name,
            ix.indisunique as is_unique
        FROM pg_class t
        JOIN pg_index ix ON t.oid = ix.indrelid
        JOIN pg_class i ON i.oid = ix.indexrelid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
        WHERE t.relname = $1;
    """
    idx_result = await conn.fetch(idx_query, table_name)

    indexes_map = {}
    for row in idx_result:
        idx_name = row["index_name"]
        if idx_name not in indexes_map:
            indexes_map[idx_name] = {
                "name": idx_name,
                "columns": [],
                "unique": row["is_unique"],
            }
        indexes_map[idx_name]["columns"].append(row["column_name"])

    return indexes_map


async def _get_table_row_count(conn, table_name: str) -> int | None:
    """Get row count for a table with timeout protection.

    Args:
        conn: Database connection
        table_name: Table name

    Returns:
        Row count or None if timeout/error
    """
    try:
        count_query = f'SELECT COUNT(*) FROM "{table_name}"'
        return await asyncio.wait_for(conn.fetchval(count_query), timeout=5.0)
    except (asyncio.TimeoutError, Exception):
        return None


def _build_column_list(columns_result: list, pk_columns: set, fk_map: dict) -> list[dict]:
    """Build list of column info dictionaries.

    Args:
        columns_result: Column query results
        pk_columns: Set of primary key column names
        fk_map: Foreign key mapping

    Returns:
        List of column info dictionaries
    """
    columns = []

    for col_row in columns_result:
        col_name = col_row["column_name"]
        column_info = {
            "name": col_name,
            "type": col_row["data_type"],
            "nullable": col_row["is_nullable"] == "YES",
            "default": col_row["column_default"],
            "isPrimaryKey": col_name in pk_columns,
        }

        if col_name in fk_map:
            column_info["isForeignKey"] = True
            column_info["foreignKeyTable"] = fk_map[col_name]["table"]
            column_info["foreignKeyColumn"] = fk_map[col_name]["column"]

        columns.append(column_info)

    return columns


async def _get_mysql_schema(connection: dict) -> SchemaResponse:
    """Get real MySQL schema (to be implemented)."""
    logger.info("MySQL schema fetching not yet implemented, returning empty schema")
    return SchemaResponse(tables=[])


async def _get_mongodb_schema(connection: dict) -> SchemaResponse:
    """Get real MongoDB schema using motor."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError:
        logger.warning("motor not installed, returning empty schema")
        return SchemaResponse(collections=[])

    logger.info("Fetching MongoDB schema...")

    client = AsyncIOMotorClient(
        connection.get("connection_string"),
        serverSelectionTimeoutMS=10000,
    )

    try:
        # Get database
        db_name = connection.get("database") or client.get_database().name
        db = client[db_name]

        # List all collections
        collection_names = await db.list_collection_names()

        collections = []
        for coll_name in collection_names:
            collection = db[coll_name]

            # Get document count
            try:
                doc_count = await asyncio.wait_for(
                    collection.count_documents({}),
                    timeout=5.0,
                )
            except asyncio.TimeoutError:
                doc_count = None
            except Exception:
                doc_count = None

            # Get sample document
            try:
                sample_doc = await collection.find_one()
                if sample_doc and "_id" in sample_doc:
                    # Convert ObjectId to string
                    sample_doc["_id"] = str(sample_doc["_id"])
            except Exception:
                sample_doc = None

            collections.append(
                {
                    "name": coll_name,
                    "documentCount": doc_count,
                    "sampleDocument": sample_doc,
                },
            )

        return SchemaResponse(collections=collections)

    finally:
        client.close()


async def _get_redis_schema(connection: dict) -> SchemaResponse:
    """Get keys for Redis using SCAN.    """
    try:
        import redis.asyncio as redis  # noqa: F401
    except ImportError:
        logger.warning("redis not installed, returning empty schema")
        return SchemaResponse(keys=[])

    password = connection.get("password")

    logger.info(f"Fetching Redis keys from {connection['host']}:{connection['port']}")

    client = redis.Redis(
        host=connection["host"],
        port=connection["port"],
        password=password,
        decode_responses=True,
        socket_connect_timeout=10,
    )

    try:
        keys_list = []

        # Use SCAN to get keys (safer than KEYS *)
        # Limit to first 100 keys to avoid performance issues
        cursor = 0
        count = 0
        max_keys = 100

        while count < max_keys:
            cursor, keys = await client.scan(cursor=cursor, count=10)

            for key in keys:
                if count >= max_keys:
                    break

                # Get key type and TTL
                key_type = await client.type(key)
                ttl = await client.ttl(key)

                keys_list.append(
                    {
                        "key": key,
                        "type": key_type,
                        "ttl": ttl,
                    },
                )
                count += 1

            if cursor == 0:  # SCAN completed
                break

        return SchemaResponse(keys=keys_list)

    finally:
        await client.close()


# ============================================================================
# QUERY EXECUTION ENDPOINTS
# ============================================================================


class QueryRequest(BaseModel):
    """Query execution request."""

    query: str
    limit: int = Field(default=1000, ge=1, le=10000)
    timeout: int = Field(default=30, ge=1, le=300)  # seconds


class QueryResult(BaseModel):
    """Query execution result."""

    success: bool
    data: list[dict] | None = None
    columns: list[str] | None = None
    rowCount: int = 0
    affectedRows: int = 0
    executionTime: float = 0.0
    error: str | None = None


@app.post("/{connection_id}/query")
async def execute_query(
    connection_id: str,
    request: QueryRequest,
    settings_store: Annotated[SettingsStore, Depends(get_user_settings_store)],
) -> QueryResult:
    """Execute a query against the database.

    Args:
        connection_id: Database connection ID
        request: Query request
        settings_store: Settings store dependency

    Returns:
        Query execution result
    """
    connection = await _get_connection_by_id(connection_id, settings_store)
    _validate_query_request(request)

    try:
        return await _dispatch_query_by_type(connection, request)
    except Exception as e:
        logger.error(f"Error executing query: {e!s}")
        return QueryResult(success=False, error=str(e), executionTime=0.0)


async def _get_connection_by_id(connection_id: str, settings_store: SettingsStore) -> dict:
    """Get database connection by ID.

    Args:
        connection_id: Connection ID to find
        settings_store: Settings store

    Returns:
        Connection configuration dict

    Raises:
        HTTPException: If connection not found
    """
    settings = await settings_store.load()

    if not settings or not hasattr(settings, "DATABASE_CONNECTIONS"):
        raise HTTPException(status_code=404, detail="Connection not found")

    connection = next(
        (conn for conn in settings.DATABASE_CONNECTIONS if conn["id"] == connection_id),
        None,
    )
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")

    return connection


def _validate_query_request(request: QueryRequest) -> None:
    """Validate query request parameters.

    Args:
        request: Query request to validate

    Raises:
        HTTPException: If validation fails
    """
    # Security validation
    _validate_query_security(request.query)

    # Size validation
    if len(request.query) > 100_000:  # 100KB max
        raise HTTPException(
            status_code=400,
            detail="Query too long. Maximum size is 100KB.",
        )

    # Empty query check
    if not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty.",
        )


async def _dispatch_query_by_type(connection: dict, request: QueryRequest) -> QueryResult:
    """Dispatch query to appropriate handler based on database type.

    Args:
        connection: Database connection config
        request: Query request

    Returns:
        Query execution result

    Raises:
        HTTPException: If database type is unsupported
    """
    db_type = connection["type"]

    if db_type in ["postgresql", "mysql"]:
        return await _execute_sql_query(connection, request)
    if db_type == "mongodb":
        return await _execute_mongodb_query(connection, request)
    if db_type == "redis":
        return await _execute_redis_command(connection, request)
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported database type: {db_type}",
    )


async def _execute_sql_query(connection: dict, request: QueryRequest) -> QueryResult:
    """Execute real SQL query using asyncpg or aiomysql."""
    db_type = connection["type"]

    if db_type == "postgresql":
        return await _execute_postgresql_query(connection, request)
    if db_type == "mysql":
        return await _execute_mysql_query(connection, request)
    return QueryResult(
        success=False,
        error=f"Unsupported database type: {db_type}",
    )


async def _execute_postgresql_query(connection: dict, request: QueryRequest) -> QueryResult:
    """Execute real PostgreSQL query using asyncpg.

    Args:
        connection: Database connection configuration
        request: Query request

    Returns:
        Query execution result
    """
    import time

    try:
        import asyncpg  # noqa: F401
    except ImportError:
        return QueryResult(success=False, error="asyncpg not installed. Run: poetry add asyncpg")

    logger.info(f"Executing PostgreSQL query: {request.query[:100]}...")
    start_time = time.time()

    try:
        conn = await _connect_to_postgresql(connection)

        try:
            rows = await asyncio.wait_for(conn.fetch(request.query), timeout=30.0)
            execution_time = round((time.time() - start_time) * 1000, 2)
            return _build_query_result_from_rows(rows, execution_time)
        finally:
            await conn.close()

    except asyncio.TimeoutError:
        return QueryResult(
            success=False,
            error="Query execution timed out after 30 seconds",
            executionTime=round((time.time() - start_time) * 1000, 2),
        )
    except Exception as e:
        logger.error(f"PostgreSQL query execution failed: {e!s}")
        return QueryResult(
            success=False,
            error=str(e),
            executionTime=round((time.time() - start_time) * 1000, 2),
        )


def _build_query_result_from_rows(rows, execution_time: float) -> QueryResult:
    """Build QueryResult from database rows.

    Args:
        rows: Database rows from query
        execution_time: Query execution time in ms

    Returns:
        QueryResult object
    """
    if rows:
        columns = list(rows[0].keys())
        data = [dict(row) for row in rows]

        # Convert special types to JSON-serializable
        for row in data:
            for key, value in row.items():
                if value is not None and not isinstance(value, (str, int, float, bool, type(None))):
                    row[key] = str(value)

        return QueryResult(
            success=True,
            data=data,
            columns=columns,
            rowCount=len(data),
            executionTime=execution_time,
        )
    # Query returned no rows
    return QueryResult(
        success=True,
        data=[],
        columns=[],
        rowCount=0,
        affectedRows=0,
        executionTime=execution_time,
    )


async def _execute_mysql_query(connection: dict, request: QueryRequest) -> QueryResult:
    """Execute real MySQL query (to be implemented)."""
    return QueryResult(
        success=False,
        error="MySQL query execution not yet implemented",
    )


async def _execute_mongodb_query(
    connection: dict,
    request: QueryRequest,
) -> QueryResult:
    """Execute real MongoDB query using motor."""
    import json
    import time

    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ImportError:
        return QueryResult(
            success=False,
            error="motor not installed. Run: poetry add motor",
        )

    start_time = time.time()

    try:
        logger.info(f"Executing MongoDB query: {request.query[:100]}...")

        # Connect to MongoDB
        client = AsyncIOMotorClient(
            connection.get("connection_string"),
            serverSelectionTimeoutMS=10000,
        )

        try:
            # Get database
            db_name = connection.get("database") or client.get_database().name
            db = client[db_name]

            # Parse query (expect JSON format: {"collection": "users", "filter": {...}, "limit": 10})
            try:
                query_obj = json.loads(request.query)
                collection_name = query_obj.get("collection")
                filter_obj = query_obj.get("filter", {})
                limit = query_obj.get("limit", 100)

                if not collection_name:
                    return QueryResult(
                        success=False,
                        error="Query must include 'collection' field. Example: {\"collection\": \"users\", \"filter\": {}, \"limit\": 10}",
                    )

                collection = db[collection_name]

                # Execute find query with timeout
                cursor = collection.find(filter_obj).limit(limit)
                documents = await asyncio.wait_for(
                    cursor.to_list(length=limit),
                    timeout=30.0,
                )

                execution_time = round((time.time() - start_time) * 1000, 2)

                # Convert ObjectId to string
                for doc in documents:
                    if "_id" in doc:
                        doc["_id"] = str(doc["_id"])

                # Get column names from first document
                columns = list(documents[0].keys()) if documents else []

                return QueryResult(
                    success=True,
                    data=documents,
                    columns=columns,
                    rowCount=len(documents),
                    executionTime=execution_time,
                )

            except json.JSONDecodeError:
                return QueryResult(
                    success=False,
                    error='Invalid JSON query format. Example: {"collection": "users", "filter": {"age": {"$gt": 18}}, "limit": 10}',
                )

        finally:
            client.close()

    except asyncio.TimeoutError:
        return QueryResult(
            success=False,
            error="Query execution timed out after 30 seconds",
            executionTime=round((time.time() - start_time) * 1000, 2),
        )
    except Exception as e:
        logger.error(f"MongoDB query execution failed: {e!s}")
        return QueryResult(
            success=False,
            error=str(e),
            executionTime=round((time.time() - start_time) * 1000, 2),
        )


async def _execute_redis_command(
    connection: dict,
    request: QueryRequest,
) -> QueryResult:
    """Execute real Redis command.

    Args:
        connection: Redis connection configuration
        request: Query request with Redis command

    Returns:
        Query execution result
    """
    import time

    try:
        import redis.asyncio as redis  # noqa: F401
    except ImportError:
        return QueryResult(success=False, error="redis not installed. Run: poetry add redis")

    logger.info(f"Executing Redis command: {request.query[:100]}...")
    start_time = time.time()

    try:
        client = await _create_redis_client(connection)

        try:
            command, args = _parse_redis_command(request.query)
            result = await asyncio.wait_for(client.execute_command(command, *args), timeout=30.0)
            execution_time = round((time.time() - start_time) * 1000, 2)

            return _build_redis_result(result, execution_time)

        finally:
            await client.close()

    except asyncio.TimeoutError:
        return QueryResult(
            success=False,
            error="Command execution timed out after 30 seconds",
            executionTime=round((time.time() - start_time) * 1000, 2),
        )
    except Exception as e:
        logger.error(f"Redis command execution failed: {e!s}")
        return QueryResult(
            success=False,
            error=str(e),
            executionTime=round((time.time() - start_time) * 1000, 2),
        )


async def _create_redis_client(connection: dict):
    """Create Redis client from connection config.

    Args:
        connection: Redis connection configuration

    Returns:
        Redis client instance
    """
    import redis.asyncio as redis

    return redis.Redis(
        host=connection["host"],
        port=connection["port"],
        password=connection.get("password"),
        decode_responses=True,
        socket_connect_timeout=10,
    )


def _parse_redis_command(query: str) -> tuple[str, list[str]]:
    """Parse Redis command string into command and arguments.

    Args:
        query: Redis command string (e.g., "GET mykey")

    Returns:
        Tuple of (command, args)

    Raises:
        ValueError: If command is empty
    """
    parts = query.strip().split()
    if not parts:
        msg = "Empty command"
        raise ValueError(msg)

    return parts[0].upper(), parts[1:]


def _build_redis_result(result, execution_time: float) -> QueryResult:
    """Build QueryResult from Redis command result.

    Args:
        result: Redis command result
        execution_time: Execution time in ms

    Returns:
        QueryResult object
    """
    # Format result based on type
    if result is None:
        data = [{"result": "nil"}]
    elif isinstance(result, (list, tuple)):
        data = [{"index": i, "value": str(v)} for i, v in enumerate(result)]
    elif isinstance(result, dict):
        data = [{"key": k, "value": str(v)} for k, v in result.items()]
    else:
        data = [{"result": str(result)}]

    columns = list(data[0].keys()) if data else ["result"]

    return QueryResult(
        success=True,
        data=data,
        columns=columns,
        rowCount=len(data),
        executionTime=execution_time,
    )
