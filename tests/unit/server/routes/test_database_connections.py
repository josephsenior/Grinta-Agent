"""Unit tests for database connections routes and helpers."""

from __future__ import annotations

import asyncio
import builtins
import json
import sys
from datetime import datetime
from types import ModuleType, SimpleNamespace
from typing import Any, Mapping, cast

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from forge.server.routes import database_connections as db_routes
from forge.server.routes.database_connections import (
    DatabaseConnectionModel,
    DatabaseType,
    QueryRequest,
    TestConnectionRequest,
    TestConnectionResponse,
)
from forge.storage.settings.settings_store import SettingsStore


class FakeSettings:
    def __init__(self, connections: list[dict[str, Any]] | None = None):
        self.DATABASE_CONNECTIONS: list[dict[str, Any]] = (
            connections if connections is not None else []
        )


class FakeSettingsStore:
    def __init__(self, settings: Any | None):
        self._settings: Any | None = settings
        self.saved_settings: Any | None = None

    async def load(self) -> Any | None:
        return self._settings

    async def save(self, settings: Any) -> None:
        self.saved_settings = settings


@pytest.mark.asyncio
async def test_list_connections_returns_list():
    settings = FakeSettings(connections=[{"id": "1"}])
    store = FakeSettingsStore(settings)
    result = await db_routes.list_connections(store)
    assert result == [{"id": "1"}]


@pytest.mark.asyncio
async def test_list_connections_missing_settings():
    store = FakeSettingsStore(None)
    result = await db_routes.list_connections(store)
    assert result == []


@pytest.mark.asyncio
async def test_create_connection_success(monkeypatch):
    settings = FakeSettings()
    store = FakeSettingsStore(settings)
    connection = DatabaseConnectionModel(
        name="primary",
        type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
        password=SecretStr("secret"),
    )
    response = await db_routes.create_connection(connection, store)
    assert response["status"] == "success"
    assert store.saved_settings is not None
    assert store.saved_settings.DATABASE_CONNECTIONS[0]["password"] == "secret"


@pytest.mark.asyncio
async def test_create_connection_no_settings():
    store = FakeSettingsStore(None)
    with pytest.raises(HTTPException) as exc:
        await db_routes.create_connection(
            DatabaseConnectionModel(
                name="test", type=DatabaseType.REDIS, host="x", port=1
            ),
            store,
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_create_connection_initializes_collection():
    class EmptySettings:
        pass

    empty_settings = EmptySettings()
    store = FakeSettingsStore(empty_settings)
    connection = DatabaseConnectionModel(
        name="primary",
        type=DatabaseType.POSTGRESQL,
        host="localhost",
        port=5432,
    )
    await db_routes.create_connection(connection, store)
    assert hasattr(empty_settings, "DATABASE_CONNECTIONS")


@pytest.mark.asyncio
async def test_update_connection_updates_entry():
    connection = DatabaseConnectionModel(
        name="source", type=DatabaseType.REDIS, host="x", port=1
    )
    settings = FakeSettings(connections=[connection.model_dump()])
    store = FakeSettingsStore(settings)
    await db_routes.update_connection(connection.id, {"host": "new"}, store)
    assert store.saved_settings is not None
    assert store.saved_settings.DATABASE_CONNECTIONS[0]["host"] == "new"


@pytest.mark.asyncio
async def test_update_connection_not_found():
    settings = FakeSettings(connections=[])
    store = FakeSettingsStore(settings)
    with pytest.raises(HTTPException) as exc:
        await db_routes.update_connection("missing", {}, store)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_connection_missing_attribute():
    class EmptySettings:
        pass

    store = FakeSettingsStore(EmptySettings())
    with pytest.raises(HTTPException) as exc:
        await db_routes.update_connection("missing", {}, store)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_connection_success():
    connection = DatabaseConnectionModel(
        name="source", type=DatabaseType.REDIS, host="x", port=1
    )
    settings = FakeSettings(connections=[connection.model_dump()])
    store = FakeSettingsStore(settings)
    response = await db_routes.delete_connection(connection.id, store)
    assert response["status"] == "success"


@pytest.mark.asyncio
async def test_delete_connection_not_found():
    settings = FakeSettings(connections=[])
    store = FakeSettingsStore(settings)
    with pytest.raises(HTTPException):
        await db_routes.delete_connection("missing", store)


@pytest.mark.asyncio
async def test_delete_connection_missing_attribute():
    class EmptySettings:
        pass

    store = FakeSettingsStore(EmptySettings())
    with pytest.raises(HTTPException):
        await db_routes.delete_connection("missing", store)


def _remove_module(monkeypatch, name: str):
    monkeypatch.delitem(sys.modules, name, raising=False)


def _block_import(monkeypatch, module_name: str) -> None:
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == module_name or name.startswith(f"{module_name}."):
            raise ImportError(f"{module_name} blocked")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def test_validate_query_security():
    # Ensure no exception is raised for dangerous patterns (warnings only)
    db_routes._validate_query_security(
        "SELECT * FROM users; DROP TABLE accounts; -- comment"
    )


def test_validate_query_security_many_statements():
    db_routes._validate_query_security(";" * 6)


@pytest.mark.asyncio
async def test_test_connection_unsupported():
    request = TestConnectionRequest.model_construct(type="custom", host="x", port=1)
    response = await db_routes.test_connection(request)
    assert response.success is False


@pytest.mark.asyncio
async def test_test_connection_dispatches_postgresql(monkeypatch):
    expected = TestConnectionResponse(success=True, message="ok")

    async def fake_pg(request):
        return expected

    monkeypatch.setattr(db_routes, "_test_postgresql", fake_pg)
    request = TestConnectionRequest(
        type=DatabaseType.POSTGRESQL, host="x", port=1, database="d", username="u"
    )
    response = await db_routes.test_connection(request)
    assert response is expected


@pytest.mark.asyncio
async def test_test_connection_dispatches_mongodb(monkeypatch):
    expected = TestConnectionResponse(success=True, message="ok")

    async def fake_mongo(request):
        return expected

    monkeypatch.setattr(db_routes, "_test_mongodb", fake_mongo)
    request = TestConnectionRequest(
        type=DatabaseType.MONGODB, host="x", port=1, connection_string="mongodb://"
    )
    response = await db_routes.test_connection(request)
    assert response is expected


@pytest.mark.asyncio
async def test_test_connection_dispatches_mysql(monkeypatch):
    expected = TestConnectionResponse(success=True, message="ok")

    async def fake_mysql(request):
        return expected

    monkeypatch.setattr(db_routes, "_test_mysql", fake_mysql)
    request = TestConnectionRequest(
        type=DatabaseType.MYSQL, host="x", port=1, database="d", username="u"
    )
    response = await db_routes.test_connection(request)
    assert response is expected


@pytest.mark.asyncio
async def test_test_connection_dispatches_redis(monkeypatch):
    expected = TestConnectionResponse(success=True, message="ok")

    async def fake_redis(request):
        return expected

    monkeypatch.setattr(db_routes, "_test_redis", fake_redis)
    request = TestConnectionRequest(type=DatabaseType.REDIS, host="x", port=1)
    response = await db_routes.test_connection(request)
    assert response is expected


@pytest.mark.asyncio
async def test_test_connection_handles_exception(monkeypatch):
    async def failing_pg(request):
        raise RuntimeError("boom")

    monkeypatch.setattr(db_routes, "_test_postgresql", failing_pg)
    request = TestConnectionRequest(
        type=DatabaseType.POSTGRESQL, host="x", port=1, database="d", username="u"
    )
    response = await db_routes.test_connection(request)
    assert response.success is False
    assert "boom" in response.message


@pytest.mark.asyncio
async def test_postgresql_missing_database():
    request = TestConnectionRequest(
        type=DatabaseType.POSTGRESQL, host="x", port=5432, username="u"
    )
    response = await db_routes._test_postgresql(request)
    assert response.success is False


@pytest.mark.asyncio
async def test_postgresql_missing_username():
    request = TestConnectionRequest(
        type=DatabaseType.POSTGRESQL, host="x", port=5432, database="db"
    )
    response = await db_routes._test_postgresql(request)
    assert response.success is False


@pytest.mark.asyncio
async def test_postgresql_import_error(monkeypatch):
    _remove_module(monkeypatch, "asyncpg")
    _block_import(monkeypatch, "asyncpg")
    request = TestConnectionRequest(
        type=DatabaseType.POSTGRESQL,
        host="x",
        port=5432,
        database="db",
        username="user",
    )
    response = await db_routes._test_postgresql(request)
    assert response.success is False


@pytest.mark.asyncio
async def test_postgresql_success(monkeypatch):
    module = ModuleType("asyncpg")

    class DummyConn:
        async def fetchval(self, query):
            return "PostgreSQL 14"

        async def close(self):
            self.closed = True

    async def connect(**kwargs):
        return DummyConn()

    setattr(module, "connect", connect)
    monkeypatch.setitem(sys.modules, "asyncpg", module)

    request = TestConnectionRequest(
        type=DatabaseType.POSTGRESQL,
        host="x",
        port=5432,
        database="db",
        username="user",
        password=SecretStr("pw"),
    )
    response = await db_routes._test_postgresql(request)
    assert response.success is True


@pytest.mark.asyncio
async def test_postgresql_failure(monkeypatch):
    module = ModuleType("asyncpg")

    async def connect(**kwargs):
        raise RuntimeError("down")

    setattr(module, "connect", connect)
    monkeypatch.setitem(sys.modules, "asyncpg", module)

    request = TestConnectionRequest(
        type=DatabaseType.POSTGRESQL,
        host="x",
        port=5432,
        database="db",
        username="user",
    )
    response = await db_routes._test_postgresql(request)
    assert response.success is False


@pytest.mark.asyncio
async def test_mongodb_missing_connection_string():
    request = TestConnectionRequest(type=DatabaseType.MONGODB, host="x", port=27017)
    response = await db_routes._test_mongodb(request)
    assert response.success is False


@pytest.mark.asyncio
async def test_mongodb_import_error(monkeypatch):
    _remove_module(monkeypatch, "motor")
    _remove_module(monkeypatch, "motor.motor_asyncio")
    _block_import(monkeypatch, "motor.motor_asyncio")
    request = TestConnectionRequest(
        type=DatabaseType.MONGODB, host="x", port=27017, connection_string="mongodb://"
    )
    response = await db_routes._test_mongodb(request)
    assert response.success is False


@pytest.mark.asyncio
async def test_mongodb_success(monkeypatch):
    module = ModuleType("motor.motor_asyncio")
    _remove_module(monkeypatch, "motor")
    _remove_module(monkeypatch, "motor.motor_asyncio")

    class DummyAdmin:
        async def command(self, cmd):
            return {"ok": 1}

    class DummyClient:
        def __init__(self, conn, serverSelectionTimeoutMS=5000):
            self.admin = DummyAdmin()

        async def server_info(self):
            return {"version": "5.0"}

        def close(self):
            self.closed = True

    setattr(module, "AsyncIOMotorClient", DummyClient)
    motor_pkg = ModuleType("motor")
    setattr(motor_pkg, "motor_asyncio", module)
    monkeypatch.setitem(sys.modules, "motor", motor_pkg)
    monkeypatch.setitem(sys.modules, "motor.motor_asyncio", module)

    request = TestConnectionRequest(
        type=DatabaseType.MONGODB, host="x", port=27017, connection_string="mongodb://"
    )
    response = await db_routes._test_mongodb(request)
    assert response.success is True


@pytest.mark.asyncio
async def test_mongodb_failure(monkeypatch):
    module = ModuleType("motor.motor_asyncio")
    _remove_module(monkeypatch, "motor")
    _remove_module(monkeypatch, "motor.motor_asyncio")

    class DummyClient:
        def __init__(self, *args, **kwargs):
            async def failing_command(cmd):
                raise RuntimeError("oops")

            self.admin = SimpleNamespace(command=failing_command)

        async def server_info(self):
            return {}

        def close(self):
            pass

    setattr(module, "AsyncIOMotorClient", DummyClient)
    motor_pkg = ModuleType("motor")
    setattr(motor_pkg, "motor_asyncio", module)
    monkeypatch.setitem(sys.modules, "motor", motor_pkg)
    monkeypatch.setitem(sys.modules, "motor.motor_asyncio", module)

    request = TestConnectionRequest(
        type=DatabaseType.MONGODB, host="x", port=27017, connection_string="mongodb://"
    )
    response = await db_routes._test_mongodb(request)
    assert response.success is False


@pytest.mark.asyncio
async def test_mysql_missing_fields():
    request = TestConnectionRequest(type=DatabaseType.MYSQL, host="x", port=3306)
    result = await db_routes._test_mysql(request)
    assert result.success is False

    request = TestConnectionRequest(
        type=DatabaseType.MYSQL, host="x", port=3306, database="db"
    )
    result = await db_routes._test_mysql(request)
    assert result.success is False


@pytest.mark.asyncio
async def test_mysql_import_error(monkeypatch):
    _remove_module(monkeypatch, "aiomysql")
    _block_import(monkeypatch, "aiomysql")
    request = TestConnectionRequest(
        type=DatabaseType.MYSQL,
        host="x",
        port=3306,
        database="db",
        username="user",
    )
    result = await db_routes._test_mysql(request)
    assert result.success is False


@pytest.mark.asyncio
async def test_mysql_success(monkeypatch):
    module = ModuleType("aiomysql")

    class DummyCursor:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def execute(self, query):
            self.query = query

        async def fetchone(self):
            return ("8.0",)

    class DummyConn:
        def __init__(self):
            self.closed = False

        def cursor(self):
            return DummyCursor()

        def close(self):
            self.closed = True

    async def connect(**kwargs):
        return DummyConn()

    setattr(module, "connect", connect)
    monkeypatch.setitem(sys.modules, "aiomysql", module)

    request = TestConnectionRequest(
        type=DatabaseType.MYSQL,
        host="x",
        port=3306,
        database="db",
        username="user",
    )
    result = await db_routes._test_mysql(request)
    assert result.success is True


@pytest.mark.asyncio
async def test_mysql_failure(monkeypatch):
    module = ModuleType("aiomysql")

    async def connect(**kwargs):
        raise RuntimeError("down")

    setattr(module, "connect", connect)
    monkeypatch.setitem(sys.modules, "aiomysql", module)

    request = TestConnectionRequest(
        type=DatabaseType.MYSQL,
        host="x",
        port=3306,
        database="db",
        username="user",
    )
    result = await db_routes._test_mysql(request)
    assert result.success is False


@pytest.mark.asyncio
async def test_redis_import_error(monkeypatch):
    _remove_module(monkeypatch, "redis")
    _remove_module(monkeypatch, "redis.asyncio")
    _block_import(monkeypatch, "redis.asyncio")
    request = TestConnectionRequest(type=DatabaseType.REDIS, host="x", port=6379)
    result = await db_routes._test_redis(request)
    assert result.success is False


@pytest.mark.asyncio
async def test_redis_success(monkeypatch):
    module = ModuleType("redis.asyncio")
    _remove_module(monkeypatch, "redis")
    _remove_module(monkeypatch, "redis.asyncio")

    class DummyRedis:
        def __init__(self, **kwargs):
            pass

        async def ping(self):
            return True

        async def info(self):
            return {"redis_version": "7"}

        async def close(self):
            self.closed = True

    setattr(module, "Redis", DummyRedis)
    redis_pkg = ModuleType("redis")
    setattr(redis_pkg, "asyncio", module)
    monkeypatch.setitem(sys.modules, "redis", redis_pkg)
    monkeypatch.setitem(sys.modules, "redis.asyncio", module)

    request = TestConnectionRequest(type=DatabaseType.REDIS, host="x", port=6379)
    result = await db_routes._test_redis(request)
    assert result.success is True


@pytest.mark.asyncio
async def test_redis_failure(monkeypatch):
    module = ModuleType("redis.asyncio")
    _remove_module(monkeypatch, "redis")
    _remove_module(monkeypatch, "redis.asyncio")

    class DummyRedis:
        def __init__(self, **kwargs):
            pass

        async def ping(self):
            raise RuntimeError("boom")

        async def info(self):
            return {}

        async def close(self):
            pass

    setattr(module, "Redis", DummyRedis)
    redis_pkg = ModuleType("redis")
    setattr(redis_pkg, "asyncio", module)
    monkeypatch.setitem(sys.modules, "redis", redis_pkg)
    monkeypatch.setitem(sys.modules, "redis.asyncio", module)

    request = TestConnectionRequest(type=DatabaseType.REDIS, host="x", port=6379)
    result = await db_routes._test_redis(request)
    assert result.success is False


@pytest.mark.asyncio
async def test_get_schema_postgresql(monkeypatch):
    connection = DatabaseConnectionModel(
        name="c", type=DatabaseType.POSTGRESQL, host="h", port=1
    )
    settings = FakeSettings(connections=[connection.model_dump()])
    store = FakeSettingsStore(settings)

    async def fake_schema(conn):
        return db_routes.SchemaResponse(tables=[{"name": "t"}])

    monkeypatch.setattr(db_routes, "_get_postgresql_schema", fake_schema)
    response = await db_routes.get_schema(connection.id, store)
    assert response.tables is not None
    assert response.tables[0]["name"] == "t"


@pytest.mark.asyncio
async def test_get_schema_connection_missing():
    store = FakeSettingsStore(FakeSettings(connections=[]))
    with pytest.raises(HTTPException) as exc:
        await db_routes.get_schema("missing", store)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_schema_missing_attribute():
    class EmptySettings:
        pass

    store = FakeSettingsStore(EmptySettings())
    with pytest.raises(HTTPException) as exc:
        await db_routes.get_schema("missing", store)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_schema_mongodb(monkeypatch):
    connection = DatabaseConnectionModel(
        name="c", type=DatabaseType.MONGODB, host="h", port=1
    )
    conn_dict = connection.model_dump()
    conn_dict["type"] = "mongodb"
    settings = FakeSettings(connections=[conn_dict])
    store = FakeSettingsStore(settings)

    async def fake_mongo_schema(conn):
        return db_routes.SchemaResponse(collections=[{"name": "users"}])

    monkeypatch.setattr(db_routes, "_get_mongodb_schema", fake_mongo_schema)
    response = await db_routes.get_schema(connection.id, store)
    assert response.collections is not None
    assert response.collections[0]["name"] == "users"


@pytest.mark.asyncio
async def test_get_schema_redis(monkeypatch):
    connection = DatabaseConnectionModel(
        name="c", type=DatabaseType.REDIS, host="h", port=1
    )
    conn_dict = connection.model_dump()
    conn_dict["type"] = "redis"
    settings = FakeSettings(connections=[conn_dict])
    store = FakeSettingsStore(settings)

    async def fake_redis_schema(conn):
        return db_routes.SchemaResponse(keys=[{"key": "a"}])

    monkeypatch.setattr(db_routes, "_get_redis_schema", fake_redis_schema)
    response = await db_routes.get_schema(connection.id, store)
    assert response.keys is not None
    assert response.keys[0]["key"] == "a"


@pytest.mark.asyncio
async def test_get_schema_unsupported(monkeypatch):
    connection = DatabaseConnectionModel(
        name="c", type=DatabaseType.MYSQL, host="h", port=1
    )
    settings = FakeSettings(connections=[{"id": connection.id, "type": "unknown"}])
    store = FakeSettingsStore(settings)
    with pytest.raises(HTTPException) as exc:
        await db_routes.get_schema(connection.id, store)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_get_sql_schema_import_error(monkeypatch):
    monkeypatch.setattr(
        db_routes,
        "_get_postgresql_schema",
        lambda conn: (_ for _ in ()).throw(ImportError("missing")),
    )
    response = await db_routes._get_sql_schema({"type": "postgresql"})
    assert response.tables == []


@pytest.mark.asyncio
async def test_get_sql_schema_mysql(monkeypatch):
    async def fake_mysql_schema(conn):
        return db_routes.SchemaResponse(tables=[{"name": "t"}])

    monkeypatch.setattr(db_routes, "_get_mysql_schema", fake_mysql_schema)
    response = await db_routes._get_sql_schema({"type": "mysql"})
    assert response.tables is not None
    assert response.tables[0]["name"] == "t"


@pytest.mark.asyncio
async def test_get_sql_schema_unsupported_type():
    with pytest.raises(ValueError):
        await db_routes._get_sql_schema({"type": "sqlite"})


@pytest.mark.asyncio
async def test_get_sql_schema_propagates_errors(monkeypatch):
    async def failing_pg(connection):
        raise RuntimeError("boom")

    monkeypatch.setattr(db_routes, "_get_postgresql_schema", failing_pg)
    with pytest.raises(RuntimeError):
        await db_routes._get_sql_schema({"type": "postgresql"})


@pytest.mark.asyncio
async def test_get_postgresql_schema_success(monkeypatch):
    module = ModuleType("asyncpg")
    monkeypatch.setitem(sys.modules, "asyncpg", module)

    class DummyConn:
        async def close(self):
            self.closed = True

    dummy_conn = DummyConn()

    async def fake_connect(connection):
        return dummy_conn

    async def fake_fetch_table_list(conn):
        return [{"table_name": "users"}]

    async def fake_build_table_schemas(conn, tables):
        return [{"name": "users"}]

    monkeypatch.setattr(db_routes, "_connect_to_postgresql", fake_connect)
    monkeypatch.setattr(db_routes, "_fetch_table_list", fake_fetch_table_list)
    monkeypatch.setattr(db_routes, "_build_table_schemas", fake_build_table_schemas)

    result = await db_routes._get_postgresql_schema(
        {
            "host": "h",
            "port": 1,
            "database": "d",
            "username": "u",
            "password": "p",
            "ssl": False,
        }
    )
    assert result.tables is not None
    assert result.tables[0]["name"] == "users"


@pytest.mark.asyncio
async def test_connect_to_postgresql(monkeypatch):
    module = ModuleType("asyncpg")

    async def connect(**kwargs):
        return "conn"

    setattr(module, "connect", connect)
    monkeypatch.setitem(sys.modules, "asyncpg", module)
    connection = {
        "host": "h",
        "port": 1,
        "database": "d",
        "username": "u",
        "password": "p",
        "ssl": False,
    }
    result = await db_routes._connect_to_postgresql(connection)
    assert result == "conn"


@pytest.mark.asyncio
async def test_get_postgresql_schema_import_error(monkeypatch):
    _remove_module(monkeypatch, "asyncpg")
    _block_import(monkeypatch, "asyncpg")
    result = await db_routes._get_postgresql_schema(
        {
            "host": "h",
            "port": 1,
            "database": "d",
            "username": "u",
            "password": "p",
            "ssl": False,
        }
    )
    assert result.tables == []


@pytest.mark.asyncio
async def test_get_mysql_schema_returns_empty():
    result = await db_routes._get_mysql_schema({"type": "mysql"})
    assert result.tables == []


def test_build_column_list():
    columns_result = [
        {
            "column_name": "id",
            "data_type": "int",
            "is_nullable": "NO",
            "column_default": None,
        },
        {
            "column_name": "user_id",
            "data_type": "int",
            "is_nullable": "YES",
            "column_default": None,
        },
    ]
    pk_columns = {"id"}
    fk_map = {"user_id": {"table": "users", "column": "id"}}
    columns = db_routes._build_column_list(columns_result, pk_columns, fk_map)
    assert columns[0]["isPrimaryKey"] is True
    assert columns[1]["isForeignKey"] is True


@pytest.mark.asyncio
async def test_fetch_table_list():
    class DummyConn:
        async def fetch(self, query):
            assert "information_schema.tables" in query
            return [{"table_name": "users"}]

    tables = await db_routes._fetch_table_list(DummyConn())
    assert tables[0]["table_name"] == "users"


@pytest.mark.asyncio
async def test_build_table_schemas(monkeypatch):
    async def fake_single(conn, table_name):
        return {"name": table_name}

    monkeypatch.setattr(db_routes, "_build_single_table_schema", fake_single)
    tables = await db_routes._build_table_schemas(None, [{"table_name": "users"}])
    assert tables == [{"name": "users"}]


@pytest.mark.asyncio
async def test_build_single_table_schema(monkeypatch):
    async def fake_fetch_table_metadata(conn, table_name):
        return (
            [
                {
                    "column_name": "id",
                    "data_type": "int",
                    "is_nullable": "NO",
                    "column_default": None,
                }
            ],
            {"id"},
            {},
            {},
        )

    async def fake_row_count(conn, table_name):
        return 5

    monkeypatch.setattr(db_routes, "_fetch_table_metadata", fake_fetch_table_metadata)
    monkeypatch.setattr(db_routes, "_get_table_row_count", fake_row_count)
    monkeypatch.setattr(
        db_routes, "_build_column_list", lambda columns, pk, fk: [{"name": "id"}]
    )
    schema = await db_routes._build_single_table_schema(None, "users")
    assert schema["rowCount"] == 5


@pytest.mark.asyncio
async def test_fetch_table_metadata(monkeypatch):
    class DummyConn:
        async def fetch(self, query, *args):
            if "information_schema.columns" in query:
                return [
                    {
                        "column_name": "id",
                        "data_type": "int",
                        "is_nullable": "NO",
                        "column_default": None,
                    },
                ]
            if "pg_index" in query and "indisprimary" in query:
                return [{"attname": "id"}]
            if "information_schema.table_constraints" in query:
                return [
                    {
                        "column_name": "user_id",
                        "foreign_table_name": "users",
                        "foreign_column_name": "id",
                    },
                ]
            return []

    async def fake_fetch_and_group(conn, table_name):
        return {"idx": {"name": "idx", "columns": ["id"], "unique": True}}

    monkeypatch.setattr(db_routes, "_fetch_and_group_indexes", fake_fetch_and_group)

    (
        columns_result,
        pk_columns,
        fk_map,
        indexes_map,
    ) = await db_routes._fetch_table_metadata(DummyConn(), "users")
    assert columns_result[0]["column_name"] == "id"
    assert "id" in pk_columns
    assert fk_map["user_id"]["table"] == "users"
    assert indexes_map["idx"]["columns"] == ["id"]


@pytest.mark.asyncio
async def test_fetch_and_group_indexes():
    class DummyConn:
        async def fetch(self, query, table_name):
            return [
                {"index_name": "idx", "column_name": "id", "is_unique": True},
                {"index_name": "idx", "column_name": "name", "is_unique": True},
            ]

    indexes = await db_routes._fetch_and_group_indexes(DummyConn(), "users")
    assert indexes["idx"]["columns"] == ["id", "name"]


@pytest.mark.asyncio
async def test_get_table_row_count(monkeypatch):
    class DummyConn:
        async def fetchval(self, query):
            return 10

    async def passthrough(coro, timeout):
        return await coro

    monkeypatch.setattr(asyncio, "wait_for", passthrough)
    count = await db_routes._get_table_row_count(DummyConn(), "users")
    assert count == 10


@pytest.mark.asyncio
async def test_get_table_row_count_timeout(monkeypatch):
    class DummyConn:
        async def fetchval(self, query):
            raise asyncio.TimeoutError

    async def passthrough(coro, timeout):
        return await coro

    monkeypatch.setattr(asyncio, "wait_for", passthrough)
    count = await db_routes._get_table_row_count(DummyConn(), "users")
    assert count is None


@pytest.mark.asyncio
async def test_get_mongodb_schema(monkeypatch):
    module = ModuleType("motor.motor_asyncio")
    _remove_module(monkeypatch, "motor")
    _remove_module(monkeypatch, "motor.motor_asyncio")

    class DummyCollection:
        def __init__(self):
            self.data = [{"_id": "1", "name": "Alice"}]

        def find(self, filter_obj):
            class Cursor:
                def __init__(self, items):
                    self.items = items

                def limit(self, value):
                    return self

                async def to_list(self, length):
                    return self.items[:length]

            return Cursor(self.data)

        async def count_documents(self, filter_obj):
            return len(self.data)

        async def find_one(self):
            return self.data[0]

    class DummyDB:
        def __init__(self):
            self.collections = {"users": DummyCollection()}

        async def list_collection_names(self):
            return list(self.collections.keys())

        def __getitem__(self, item):
            return self.collections[item]

    class DummyClient:
        def __init__(self, conn, serverSelectionTimeoutMS=10000):
            self._db = DummyDB()

        def get_database(self):
            return SimpleNamespace(name="db")

        def __getitem__(self, item):
            return self._db

        def close(self):
            self.closed = True

    setattr(module, "AsyncIOMotorClient", DummyClient)
    monkeypatch.setitem(sys.modules, "motor.motor_asyncio", module)

    connection = {"type": "mongodb", "connection_string": "mongodb://"}
    response = await db_routes._get_mongodb_schema(connection)
    assert response.collections and response.collections[0]["name"] == "users"


@pytest.mark.asyncio
async def test_get_mongodb_schema_handles_errors(monkeypatch):
    module = ModuleType("motor.motor_asyncio")
    _remove_module(monkeypatch, "motor")
    _remove_module(monkeypatch, "motor.motor_asyncio")

    class DummyCollection:
        def __init__(self):
            self.data = [{"_id": "1", "name": "Alice"}]

        async def count_documents(self, filter_obj):
            raise asyncio.TimeoutError

        async def find_one(self):
            raise RuntimeError("fail")

    class DummyDB:
        async def list_collection_names(self):
            return ["users"]

        def __getitem__(self, item):
            return DummyCollection()

    class DummyClient:
        def __init__(self, *args, **kwargs):
            self._db = DummyDB()

        def get_database(self):
            return SimpleNamespace(name="db")

        def __getitem__(self, item):
            return self._db

        def close(self):
            pass

    setattr(module, "AsyncIOMotorClient", DummyClient)
    motor_pkg = ModuleType("motor")
    setattr(motor_pkg, "motor_asyncio", module)
    monkeypatch.setitem(sys.modules, "motor", motor_pkg)
    monkeypatch.setitem(sys.modules, "motor.motor_asyncio", module)

    connection = {"type": "mongodb", "connection_string": "mongodb://"}
    response = await db_routes._get_mongodb_schema(connection)
    assert response.collections and response.collections[0]["documentCount"] is None


@pytest.mark.asyncio
async def test_get_mongodb_schema_count_documents_error(monkeypatch):
    module = ModuleType("motor.motor_asyncio")
    _remove_module(monkeypatch, "motor")
    _remove_module(monkeypatch, "motor.motor_asyncio")

    class DummyCollection:
        async def count_documents(self, filter_obj):
            raise RuntimeError("fail")

        async def find_one(self):
            return None

    class DummyDB:
        async def list_collection_names(self):
            return ["users"]

        def __getitem__(self, item):
            return DummyCollection()

    class DummyClient:
        def __init__(self, *args, **kwargs):
            self._db = DummyDB()

        def get_database(self):
            return SimpleNamespace(name="db")

        def __getitem__(self, item):
            return self._db

        def close(self):
            pass

    setattr(module, "AsyncIOMotorClient", DummyClient)
    motor_pkg = ModuleType("motor")
    setattr(motor_pkg, "motor_asyncio", module)
    monkeypatch.setitem(sys.modules, "motor", motor_pkg)
    monkeypatch.setitem(sys.modules, "motor.motor_asyncio", module)

    connection = {"type": "mongodb", "connection_string": "mongodb://"}
    response = await db_routes._get_mongodb_schema(connection)
    assert response.collections is not None
    assert response.collections[0]["documentCount"] is None


@pytest.mark.asyncio
async def test_get_mongodb_schema_missing_driver(monkeypatch):
    _remove_module(monkeypatch, "motor")
    _remove_module(monkeypatch, "motor.motor_asyncio")
    _block_import(monkeypatch, "motor.motor_asyncio")
    response = await db_routes._get_mongodb_schema({"type": "mongodb"})
    assert response.collections == []


@pytest.mark.asyncio
async def test_get_redis_schema(monkeypatch):
    module = ModuleType("redis.asyncio")
    _remove_module(monkeypatch, "redis")
    _remove_module(monkeypatch, "redis.asyncio")

    class DummyRedis:
        def __init__(self, **kwargs):
            self.keys = ["key1", "key2"]
            self.calls = 0

        async def scan(self, cursor=0, count=10):
            if self.calls == 0:
                self.calls += 1
                return 0, self.keys
            return 0, []

        async def type(self, key):
            return "string"

        async def ttl(self, key):
            return -1

        async def close(self):
            self.closed = True

    setattr(module, "Redis", DummyRedis)
    redis_pkg = ModuleType("redis")
    setattr(redis_pkg, "asyncio", module)
    monkeypatch.setitem(sys.modules, "redis", redis_pkg)
    monkeypatch.setitem(sys.modules, "redis.asyncio", module)

    connection = {"type": "redis", "host": "localhost", "port": 6379}
    response = await db_routes._get_redis_schema(connection)
    assert response.keys is not None
    assert response.keys[0]["key"] == "key1"


@pytest.mark.asyncio
async def test_get_redis_schema_limits_keys(monkeypatch):
    module = ModuleType("redis.asyncio")
    _remove_module(monkeypatch, "redis")
    _remove_module(monkeypatch, "redis.asyncio")

    class DummyRedis:
        def __init__(self, **kwargs):
            self.calls = 0

        async def scan(self, cursor=0, count=10):
            self.calls += 1
            if self.calls == 1:
                return 1, [f"key{i}" for i in range(101)]
            return 0, []

        async def type(self, key):
            return "string"

        async def ttl(self, key):
            return -1

        async def close(self):
            pass

    setattr(module, "Redis", DummyRedis)
    redis_pkg = ModuleType("redis")
    setattr(redis_pkg, "asyncio", module)
    monkeypatch.setitem(sys.modules, "redis", redis_pkg)
    monkeypatch.setitem(sys.modules, "redis.asyncio", module)

    connection = {"type": "redis", "host": "localhost", "port": 6379}
    response = await db_routes._get_redis_schema(connection)
    assert response.keys is not None
    assert len(response.keys) == 100


@pytest.mark.asyncio
async def test_get_redis_schema_missing_driver(monkeypatch):
    _remove_module(monkeypatch, "redis")
    _remove_module(monkeypatch, "redis.asyncio")
    _block_import(monkeypatch, "redis.asyncio")
    response = await db_routes._get_redis_schema(
        {"type": "redis", "host": "h", "port": 1}
    )
    assert response.keys == []


@pytest.mark.asyncio
async def test_get_connection_by_id_success():
    connection = {"id": "abc", "type": "postgresql"}
    store = FakeSettingsStore(FakeSettings(connections=[connection]))
    loaded = await db_routes._get_connection_by_id("abc", cast(SettingsStore, store))
    assert loaded["id"] == "abc"


@pytest.mark.asyncio
async def test_get_connection_by_id_missing():
    store = FakeSettingsStore(FakeSettings(connections=[]))
    with pytest.raises(HTTPException):
        await db_routes._get_connection_by_id("missing", cast(SettingsStore, store))


@pytest.mark.asyncio
async def test_get_connection_by_id_missing_attribute():
    class EmptySettings:
        pass

    store = FakeSettingsStore(EmptySettings())
    with pytest.raises(HTTPException):
        await db_routes._get_connection_by_id("missing", cast(SettingsStore, store))


def test_validate_query_request(monkeypatch):
    request = QueryRequest(query="SELECT 1", limit=10)
    db_routes._validate_query_request(request)

    long_query = QueryRequest(query="x" * 100_001)
    with pytest.raises(HTTPException):
        db_routes._validate_query_request(long_query)

    empty_query = QueryRequest(query="   ")
    with pytest.raises(HTTPException):
        db_routes._validate_query_request(empty_query)


@pytest.mark.asyncio
async def test_dispatch_query_by_type(monkeypatch):
    async def fake_sql(conn, req):
        return db_routes.QueryResult(success=True)

    monkeypatch.setattr(db_routes, "_execute_sql_query", fake_sql)
    result = await db_routes._dispatch_query_by_type(
        {"type": "postgresql"}, QueryRequest(query="q")
    )
    assert result.success is True

    async def fake_mongo(conn, req):
        return db_routes.QueryResult(success=True)

    monkeypatch.setattr(db_routes, "_execute_mongodb_query", fake_mongo)
    result_mongo = await db_routes._dispatch_query_by_type(
        {"type": "mongodb"}, QueryRequest(query="{}")
    )
    assert result_mongo.success is True

    async def fake_redis(conn, req):
        return db_routes.QueryResult(success=True)

    monkeypatch.setattr(db_routes, "_execute_redis_command", fake_redis)
    result_redis = await db_routes._dispatch_query_by_type(
        {"type": "redis"}, QueryRequest(query="PING")
    )
    assert result_redis.success is True

    with pytest.raises(HTTPException):
        await db_routes._dispatch_query_by_type(
            {"type": "unknown"}, QueryRequest(query="q")
        )


@pytest.mark.asyncio
async def test_execute_query_success(monkeypatch):
    async def fake_get_connection(connection_id, store):
        return {"id": connection_id, "type": "postgresql"}

    async def fake_dispatch(connection, request):
        return db_routes.QueryResult(success=True)

    monkeypatch.setattr(db_routes, "_get_connection_by_id", fake_get_connection)
    monkeypatch.setattr(db_routes, "_validate_query_request", lambda req: None)
    monkeypatch.setattr(db_routes, "_dispatch_query_by_type", fake_dispatch)

    result = await db_routes.execute_query(
        "abc",
        QueryRequest(query="SELECT 1"),
        cast(SettingsStore, FakeSettingsStore(None)),
    )
    assert result.success is True


@pytest.mark.asyncio
async def test_execute_query_error(monkeypatch):
    async def fake_get_connection(connection_id, store):
        return {"id": connection_id, "type": "postgresql"}

    async def failing_dispatch(connection, request):
        raise RuntimeError("boom")

    monkeypatch.setattr(db_routes, "_get_connection_by_id", fake_get_connection)
    monkeypatch.setattr(db_routes, "_validate_query_request", lambda req: None)
    monkeypatch.setattr(db_routes, "_dispatch_query_by_type", failing_dispatch)

    result = await db_routes.execute_query(
        "abc",
        QueryRequest(query="SELECT 1"),
        cast(SettingsStore, FakeSettingsStore(None)),
    )
    assert result.success is False
    assert result.error is not None
    assert "boom" in result.error


@pytest.mark.asyncio
async def test_execute_postgresql_query_import_error(monkeypatch):
    _remove_module(monkeypatch, "asyncpg")
    _block_import(monkeypatch, "asyncpg")
    connection = {
        "type": "postgresql",
        "host": "h",
        "port": 1,
        "database": "d",
        "username": "u",
        "password": "p",
        "ssl": False,
    }
    result = await db_routes._execute_postgresql_query(
        connection, QueryRequest(query="SELECT 1")
    )
    assert result.success is False


@pytest.mark.asyncio
async def test_execute_mysql_query_not_implemented():
    result = await db_routes._execute_mysql_query(
        {"type": "mysql"}, QueryRequest(query="SELECT 1")
    )
    assert result.success is False
    assert result.error is not None
    assert "not yet implemented" in result.error


@pytest.mark.asyncio
async def test_execute_sql_query_unsupported():
    result = await db_routes._execute_sql_query(
        {"type": "sqlite"}, QueryRequest(query="SELECT 1")
    )
    assert result.success is False


@pytest.mark.asyncio
async def test_execute_postgresql_query_success(monkeypatch):
    module = ModuleType("asyncpg")

    class DummyRecord(dict):
        def keys(self):
            return super().keys()

    class DummyConn:
        async def fetch(self, query):
            return [DummyRecord(id=1, name="Alice")]

        async def close(self):
            pass

    async def connect(**kwargs):
        return DummyConn()

    setattr(module, "connect", connect)
    monkeypatch.setitem(sys.modules, "asyncpg", module)

    async def fake_connect(connection):
        return DummyConn()

    monkeypatch.setattr(db_routes, "_connect_to_postgresql", fake_connect)

    connection = {
        "type": "postgresql",
        "host": "h",
        "port": 1,
        "database": "d",
        "username": "u",
        "password": "p",
        "ssl": False,
    }
    result = await db_routes._execute_postgresql_query(
        connection, QueryRequest(query="SELECT 1")
    )
    assert result.success is True
    assert result.columns == ["id", "name"]


@pytest.mark.asyncio
async def test_execute_postgresql_query_timeout(monkeypatch):
    module = ModuleType("asyncpg")

    class DummyConn:
        async def fetch(self, query):
            await asyncio.sleep(0)
            raise asyncio.TimeoutError()

        async def close(self):
            pass

    async def connect(**kwargs):
        return DummyConn()

    setattr(module, "connect", connect)
    monkeypatch.setitem(sys.modules, "asyncpg", module)

    async def fake_connect(connection):
        return DummyConn()

    monkeypatch.setattr(db_routes, "_connect_to_postgresql", fake_connect)

    connection = {
        "type": "postgresql",
        "host": "h",
        "port": 1,
        "database": "d",
        "username": "u",
        "password": "p",
        "ssl": False,
    }
    result = await db_routes._execute_postgresql_query(
        connection, QueryRequest(query="SELECT 1")
    )
    assert result.success is False


@pytest.mark.asyncio
async def test_execute_postgresql_query_general_exception(monkeypatch):
    module = ModuleType("asyncpg")

    class DummyConn:
        async def fetch(self, query):
            raise RuntimeError("boom")

        async def close(self):
            pass

    async def connect(**kwargs):
        return DummyConn()

    setattr(module, "connect", connect)
    monkeypatch.setitem(sys.modules, "asyncpg", module)

    async def fake_connect(connection):
        return DummyConn()

    monkeypatch.setattr(db_routes, "_connect_to_postgresql", fake_connect)
    connection = {
        "type": "postgresql",
        "host": "h",
        "port": 1,
        "database": "d",
        "username": "u",
        "password": "p",
        "ssl": False,
    }
    result = await db_routes._execute_postgresql_query(
        connection, QueryRequest(query="SELECT 1")
    )
    assert result.success is False
    assert result.error is not None
    assert "boom" in result.error


def test_build_query_result_from_rows():
    class DummyRecord(dict):
        def keys(self):
            return super().keys()

    rows = [DummyRecord(id=1, value=datetime.now())]
    result = db_routes._build_query_result_from_rows(rows, 10.0)
    assert result.success is True
    result_none = db_routes._build_query_result_from_rows([], 5.0)
    assert result_none.success is True


@pytest.mark.asyncio
async def test_execute_mongodb_query_import_error(monkeypatch):
    _remove_module(monkeypatch, "motor.motor_asyncio")
    result = await db_routes._execute_mongodb_query({}, QueryRequest(query="{}"))
    assert result.success is False


@pytest.mark.asyncio
async def test_execute_mongodb_query_success(monkeypatch):
    module = ModuleType("motor.motor_asyncio")
    _remove_module(monkeypatch, "motor")
    _remove_module(monkeypatch, "motor.motor_asyncio")

    class DummyCursor:
        def __init__(self, items):
            self.items = items

        def limit(self, value):
            self.limit_value = value
            return self

        async def to_list(self, length):
            return self.items[:length]

    class DummyCollection:
        def __init__(self):
            self.items = [{"_id": "1", "name": "Alice"}]

        def find(self, filter_obj):
            return DummyCursor(self.items)

    class DummyDB:
        def __init__(self):
            self.collection = DummyCollection()

        def __getitem__(self, item):
            return self.collection

    class DummyClient:
        def __init__(self, conn, serverSelectionTimeoutMS=10000):
            self.db = DummyDB()

        def get_database(self):
            return SimpleNamespace(name="db")

        def __getitem__(self, item):
            return self.db

        def close(self):
            self.closed = True

    setattr(module, "AsyncIOMotorClient", DummyClient)
    monkeypatch.setitem(sys.modules, "motor.motor_asyncio", module)

    connection = {"connection_string": "mongodb://"}
    result = await db_routes._execute_mongodb_query(
        connection, QueryRequest(query=json.dumps({"collection": "users"}))
    )
    assert result.success is True


@pytest.mark.asyncio
async def test_execute_mongodb_query_decode_error(monkeypatch):
    module = ModuleType("motor.motor_asyncio")
    _remove_module(monkeypatch, "motor")
    _remove_module(monkeypatch, "motor.motor_asyncio")

    class DummyDB:
        def __getitem__(self, item):
            return None

    class DummyClient:
        def __init__(self, *args, **kwargs):
            self._db = DummyDB()

        def get_database(self):
            return SimpleNamespace(name="db")

        def __getitem__(self, item):
            return self._db

        def close(self):
            pass

    setattr(module, "AsyncIOMotorClient", DummyClient)
    motor_pkg = ModuleType("motor")
    setattr(motor_pkg, "motor_asyncio", module)
    monkeypatch.setitem(sys.modules, "motor", motor_pkg)
    monkeypatch.setitem(sys.modules, "motor.motor_asyncio", module)
    result = await db_routes._execute_mongodb_query({}, QueryRequest(query="not-json"))
    assert result.success is False


@pytest.mark.asyncio
async def test_execute_mongodb_query_missing_collection(monkeypatch):
    module = ModuleType("motor.motor_asyncio")
    _remove_module(monkeypatch, "motor")
    _remove_module(monkeypatch, "motor.motor_asyncio")

    class DummyClient:
        def __init__(self, *args, **kwargs):
            self.db = SimpleNamespace()

        def get_database(self):
            return SimpleNamespace(name="db")

        def __getitem__(self, item):
            return SimpleNamespace(
                find=lambda *_args, **_kwargs: SimpleNamespace(
                    limit=lambda self, value: self
                )
            )

        def close(self):
            pass

    setattr(module, "AsyncIOMotorClient", DummyClient)
    motor_pkg = ModuleType("motor")
    setattr(motor_pkg, "motor_asyncio", module)
    monkeypatch.setitem(sys.modules, "motor", motor_pkg)
    monkeypatch.setitem(sys.modules, "motor.motor_asyncio", module)

    connection = {"connection_string": "mongodb://"}
    result = await db_routes._execute_mongodb_query(
        connection, QueryRequest(query=json.dumps({}))
    )
    assert result.success is False
    assert result.error is not None
    assert "collection" in result.error


@pytest.mark.asyncio
async def test_execute_mongodb_query_timeout(monkeypatch):
    module = ModuleType("motor.motor_asyncio")
    _remove_module(monkeypatch, "motor")
    _remove_module(monkeypatch, "motor.motor_asyncio")

    class DummyCursor:
        def limit(self, value):
            return self

        async def to_list(self, length):
            await asyncio.sleep(0)
            return []

    class DummyCollection:
        def find(self, filter_obj):
            return DummyCursor()

    class DummyDB:
        def __getitem__(self, item):
            return DummyCollection()

    class DummyClient:
        def __init__(self, *args, **kwargs):
            self.db = DummyDB()

        def get_database(self):
            return SimpleNamespace(name="db")

        def __getitem__(self, item):
            return self.db

        def close(self):
            pass

    setattr(module, "AsyncIOMotorClient", DummyClient)
    motor_pkg = ModuleType("motor")
    setattr(motor_pkg, "motor_asyncio", module)
    monkeypatch.setitem(sys.modules, "motor", motor_pkg)
    monkeypatch.setitem(sys.modules, "motor.motor_asyncio", module)

    async def raise_timeout(coro, timeout):
        raise asyncio.TimeoutError

    monkeypatch.setattr(asyncio, "wait_for", raise_timeout)
    connection = {"connection_string": "mongodb://"}
    result = await db_routes._execute_mongodb_query(
        connection, QueryRequest(query=json.dumps({"collection": "users"}))
    )
    assert result.success is False
    assert result.error is not None
    assert "timed out" in result.error


@pytest.mark.asyncio
async def test_execute_redis_command_import_error(monkeypatch):
    _remove_module(monkeypatch, "redis.asyncio")
    result = await db_routes._execute_redis_command({}, QueryRequest(query="PING"))
    assert result.success is False


@pytest.mark.asyncio
async def test_execute_redis_command_success(monkeypatch):
    module = ModuleType("redis.asyncio")
    _remove_module(monkeypatch, "redis")
    _remove_module(monkeypatch, "redis.asyncio")

    class DummyClient:
        async def execute_command(self, command, *args):
            return "PONG"

        async def close(self):
            pass

    async def fake_create(conn):
        return DummyClient()

    monkeypatch.setattr(db_routes, "_create_redis_client", fake_create)
    monkeypatch.setattr(db_routes, "_parse_redis_command", lambda query: ("PING", []))
    monkeypatch.setattr(
        db_routes,
        "_build_redis_result",
        lambda result, exec_time: db_routes.QueryResult(
            success=True,
            data=[{"result": result}],
            columns=["result"],
            executionTime=exec_time,
        ),
    )
    setattr(module, "Redis", lambda **kwargs: DummyClient())
    redis_pkg = ModuleType("redis")
    setattr(redis_pkg, "asyncio", module)
    monkeypatch.setitem(sys.modules, "redis", redis_pkg)
    monkeypatch.setitem(sys.modules, "redis.asyncio", module)

    result = await db_routes._execute_redis_command({}, QueryRequest(query="PING"))
    assert result.success is True


@pytest.mark.asyncio
async def test_execute_redis_command_exception(monkeypatch):
    module = ModuleType("redis.asyncio")
    _remove_module(monkeypatch, "redis")
    _remove_module(monkeypatch, "redis.asyncio")

    class DummyClient:
        async def execute_command(self, command, *args):
            raise RuntimeError("fail")

        async def close(self):
            pass

    async def fake_create(conn):
        return DummyClient()

    monkeypatch.setattr(db_routes, "_create_redis_client", fake_create)
    monkeypatch.setattr(db_routes, "_parse_redis_command", lambda query: ("PING", []))
    setattr(module, "Redis", lambda **kwargs: DummyClient())
    redis_pkg = ModuleType("redis")
    setattr(redis_pkg, "asyncio", module)
    monkeypatch.setitem(sys.modules, "redis", redis_pkg)
    monkeypatch.setitem(sys.modules, "redis.asyncio", module)

    result = await db_routes._execute_redis_command({}, QueryRequest(query="PING"))
    assert result.success is False
    assert result.error is not None
    assert "fail" in result.error


def test_parse_redis_command():
    command, args = db_routes._parse_redis_command("GET key")
    assert command == "GET" and args == ["key"]
    with pytest.raises(ValueError):
        db_routes._parse_redis_command("   ")


def test_build_redis_result():
    result_none = db_routes._build_redis_result(None, 1.0)
    assert result_none.data is not None
    assert result_none.data[0]["result"] == "nil"
    result_list = db_routes._build_redis_result([1, 2], 1.0)
    assert result_list.rowCount == 2
    result_dict = db_routes._build_redis_result({"a": 1}, 1.0)
    assert result_dict.data is not None
    assert result_dict.data[0]["key"] == "a"
    result_scalar = db_routes._build_redis_result("OK", 1.0)
    assert result_scalar.data is not None
    assert result_scalar.data[0]["result"] == "OK"
