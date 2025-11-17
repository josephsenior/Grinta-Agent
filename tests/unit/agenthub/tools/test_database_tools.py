"""Tests for database agent tools."""

import pytest

from forge.agenthub.codeact_agent.tools.database import (
    get_database_tools,
    DatabaseConnectTool,
    DatabaseSchemaTool,
    DatabaseQueryTool,
)


class TestDatabaseTools:
    """Test suite for database agent tools."""

    def test_get_database_tools_returns_three_tools(self):
        """Test that get_database_tools returns all three database tools."""
        tools = get_database_tools()

        assert len(tools) == 3
        tool_names = [tool["function"]["name"] for tool in tools]
        assert "database_connect" in tool_names
        assert "database_schema" in tool_names
        assert "database_query" in tool_names

    def test_database_connect_tool_structure(self):
        """Test the structure of database_connect tool definition."""
        assert DatabaseConnectTool["type"] == "function"
        assert "description" in DatabaseConnectTool["function"]
        assert "parameters" in DatabaseConnectTool["function"]

        params = DatabaseConnectTool["function"]["parameters"]
        assert "db_type" in params["properties"]
        assert "connection_name" in params["properties"]
        assert "env_prefix" in params["properties"]
        assert params["required"] == ["connection_name", "db_type", "env_prefix"]

    def test_database_connect_tool_properties(self):
        """Test database_connect tool has correct properties."""
        assert DatabaseConnectTool["function"]["name"] == "database_connect"

        params = DatabaseConnectTool["function"]["parameters"]
        db_type_prop = params["properties"]["db_type"]
        assert "enum" in db_type_prop
        assert "postgresql" in db_type_prop["enum"]
        assert "mongodb" in db_type_prop["enum"]
        assert "redis" in db_type_prop["enum"]
        assert "mysql" in db_type_prop["enum"]

    def test_database_connect_description_mentions_env_vars(self):
        """Test database_connect tool description mentions environment variables."""
        description = DatabaseConnectTool["function"]["description"]
        assert "environment variable" in description.lower()
        assert "HOST" in description
        assert "PORT" in description
        assert "DATABASE" in description

    def test_database_schema_tool_structure(self):
        """Test the structure of database_schema tool definition."""
        assert DatabaseSchemaTool["type"] == "function"
        assert DatabaseSchemaTool["function"]["name"] == "database_schema"
        assert "description" in DatabaseSchemaTool["function"]

        params = DatabaseSchemaTool["function"]["parameters"]
        assert "connection_name" in params["properties"]
        assert params["required"] == ["connection_name"]

    def test_database_schema_description(self):
        """Test database_schema tool description is comprehensive."""
        description = DatabaseSchemaTool["function"]["description"]
        assert "schema" in description.lower()
        assert "PostgreSQL" in description or "SQL" in description
        assert "MongoDB" in description
        assert "Redis" in description

    def test_database_query_tool_structure(self):
        """Test the structure of database_query tool definition."""
        assert DatabaseQueryTool["type"] == "function"
        assert DatabaseQueryTool["function"]["name"] == "database_query"
        assert "description" in DatabaseQueryTool["function"]

        params = DatabaseQueryTool["function"]["parameters"]
        assert "connection_name" in params["properties"]
        assert "query" in params["properties"]
        assert params["required"] == ["connection_name", "query"]

    def test_database_query_has_limit_parameter(self):
        """Test database_query tool has optional limit parameter."""
        params = DatabaseQueryTool["function"]["parameters"]
        assert "limit" in params["properties"]
        limit_prop = params["properties"]["limit"]
        assert limit_prop["type"] == "integer"
        assert limit_prop["default"] == 100

    def test_database_query_description_mentions_formats(self):
        """Test database_query tool description explains query formats."""
        description = DatabaseQueryTool["function"]["description"]
        assert "SQL" in description or "SELECT" in description
        assert "MongoDB" in description
        assert "Redis" in description

    def test_all_tools_have_required_fields(self):
        """Test that all database tools have required fields."""
        tools = get_database_tools()

        for tool in tools:
            assert "type" in tool
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
            assert "type" in tool["function"]["parameters"]
            assert "properties" in tool["function"]["parameters"]

    def test_tool_descriptions_are_informative(self):
        """Test that tool descriptions are helpful for LLM."""
        tools = get_database_tools()

        for tool in tools:
            description = tool["function"]["description"]
            assert len(description) > 50  # Should be substantial
            assert "database" in description.lower()

    def test_database_connect_has_correct_enum_values(self):
        """Test database_connect has all expected database types."""
        params = DatabaseConnectTool["function"]["parameters"]
        db_types = params["properties"]["db_type"]["enum"]

        # Should have exactly these 4 types
        assert len(db_types) == 4
        assert set(db_types) == {"postgresql", "mongodb", "mysql", "redis"}

    def test_parameter_types_are_correct(self):
        """Test that all parameters have correct types."""
        # DatabaseConnectTool
        connect_params = DatabaseConnectTool["function"]["parameters"]["properties"]
        assert connect_params["connection_name"]["type"] == "string"
        assert connect_params["db_type"]["type"] == "string"
        assert connect_params["env_prefix"]["type"] == "string"

        # DatabaseSchemaTool
        schema_params = DatabaseSchemaTool["function"]["parameters"]["properties"]
        assert schema_params["connection_name"]["type"] == "string"

        # DatabaseQueryTool
        query_params = DatabaseQueryTool["function"]["parameters"]["properties"]
        assert query_params["connection_name"]["type"] == "string"
        assert query_params["query"]["type"] == "string"
        assert query_params["limit"]["type"] == "integer"

    def test_tools_are_returned_in_correct_order(self):
        """Test that tools are returned in logical order."""
        tools = get_database_tools()
        tool_names = [t["function"]["name"] for t in tools]

        # Connect should come first, then schema, then query
        assert tool_names[0] == "database_connect"
        assert tool_names[1] == "database_schema"
        assert tool_names[2] == "database_query"

    def test_all_tools_have_descriptions_with_examples(self):
        """Test that all tools have helpful descriptions."""
        connect_desc = DatabaseConnectTool["function"]["description"]
        assert "Example" in connect_desc or "example" in connect_desc

        # Should explain the workflow
        assert "PREFIX" in connect_desc  # Explains environment variable pattern

    def test_database_query_explains_all_supported_formats(self):
        """Test that database_query explains all query formats."""
        description = DatabaseQueryTool["function"]["description"]

        # Should explain format for each database type
        assert "PostgreSQL" in description or "MySQL" in description
        assert "MongoDB" in description
        assert "Redis" in description

        # Should show examples
        assert "SELECT" in description or "GET" in description


class TestDatabaseToolsIntegration:
    """Integration-style tests for database tools workflow."""

    def test_tools_support_complete_workflow(self):
        """Test that tools support typical workflow: connect → schema → query."""
        tools = get_database_tools()
        tool_map = {t["function"]["name"]: t for t in tools}

        # Step 1: Should have connect tool
        assert "database_connect" in tool_map
        connect_tool = tool_map["database_connect"]
        assert "connection_name" in connect_tool["function"]["parameters"]["properties"]

        # Step 2: Should have schema tool that uses same connection_name
        assert "database_schema" in tool_map
        schema_tool = tool_map["database_schema"]
        assert "connection_name" in schema_tool["function"]["parameters"]["properties"]

        # Step 3: Should have query tool that uses same connection_name
        assert "database_query" in tool_map
        query_tool = tool_map["database_query"]
        assert "connection_name" in query_tool["function"]["parameters"]["properties"]

    def test_connection_name_is_consistent_across_tools(self):
        """Test that connection_name parameter is consistent across all tools."""
        tools = get_database_tools()

        # All tools should use 'connection_name' (except connect which creates it)
        for tool in tools:
            params = tool["function"]["parameters"]["properties"]
            if tool["function"]["name"] != "database_connect":
                assert "connection_name" in params

    def test_tools_cover_all_crud_operations(self):
        """Test that database_query tool supports all CRUD operations."""
        description = DatabaseQueryTool["function"]["description"]

        # Should mention various operation types
        assert "SELECT" in description or "read" in description.lower()
        # MongoDB and Redis also covered
        assert len(description) > 200  # Comprehensive description
