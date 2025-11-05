"""Test warning suppression functionality in CLI mode."""

import warnings
from io import StringIO
from unittest.mock import patch
from openhands.cli.suppress_warnings import suppress_cli_warnings


class TestWarningSuppressionCLI:
    """Test cases for CLI warning suppression."""

    def test_suppress_pydantic_warnings(self):
        """Test that Pydantic serialization warnings are suppressed."""
        suppress_cli_warnings()
        captured_output = StringIO()
        with patch("sys.stderr", captured_output):
            warnings.warn(
                "Pydantic serializer warnings: PydanticSerializationUnexpectedValue", UserWarning, stacklevel=2
            )
        output = captured_output.getvalue()
        assert "Pydantic serializer warnings" not in output

    def test_suppress_deprecated_method_warnings(self):
        """Test that deprecated method warnings are suppressed."""
        suppress_cli_warnings()
        captured_output = StringIO()
        with patch("sys.stderr", captured_output):
            warnings.warn(
                "Call to deprecated method get_events. (Use search_events instead)", DeprecationWarning, stacklevel=2
            )
        output = captured_output.getvalue()
        assert "deprecated method" not in output

    def test_suppress_expected_fields_warnings(self):
        """Test that expected fields warnings are suppressed."""
        suppress_cli_warnings()
        captured_output = StringIO()
        with patch("sys.stderr", captured_output):
            warnings.warn("Expected 9 fields but got 5: Expected `Message`", UserWarning, stacklevel=2)
        output = captured_output.getvalue()
        assert "Expected 9 fields" not in output

    def test_regular_warnings_not_suppressed(self):
        """Test that regular warnings are NOT suppressed."""
        suppress_cli_warnings()
        captured_output = StringIO()
        with patch("sys.stderr", captured_output):
            warnings.warn("This is a regular warning that should appear", UserWarning, stacklevel=2)
        output = captured_output.getvalue()
        assert "regular warning" in output

    def test_module_import_applies_suppression(self):
        """Test that importing the module automatically applies suppression."""
        warnings.resetwarnings()
        import importlib
        import openhands.cli.suppress_warnings

        importlib.reload(openhands.cli.suppress_warnings)
        captured_output = StringIO()
        with patch("sys.stderr", captured_output):
            warnings.warn("Pydantic serializer warnings: test", UserWarning, stacklevel=2)
        output = captured_output.getvalue()
        assert "Pydantic serializer warnings" not in output

    def test_warning_filters_are_applied(self):
        """Test that warning filters are properly applied."""
        warnings.resetwarnings()
        suppress_cli_warnings()
        filters = warnings.filters
        filter_messages = [f[1] for f in filters if f[1] is not None]
        assert any(("Pydantic serializer warnings" in str(msg) for msg in filter_messages))
        assert any(("deprecated method" in str(msg) for msg in filter_messages))
