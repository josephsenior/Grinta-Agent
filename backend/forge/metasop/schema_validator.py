"""MetaSOP Schema Validator.

Validates MetaSOP artifacts against JSON Schema definitions to ensure data integrity
and type safety across the system.
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from jsonschema import Draft7Validator
else:  # pragma: no cover - type alias when jsonschema unavailable
    Draft7Validator = Any  # type: ignore[misc]

try:
    import jsonschema
    from jsonschema import Draft7Validator, ValidationError

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    logging.warning(
        "jsonschema not available. Schema validation disabled. "
        "Install with: pip install jsonschema"
    )

logger = logging.getLogger(__name__)


class SchemaValidator:
    """Validates MetaSOP artifacts against JSON Schema definitions."""

    def __init__(self, schemas_dir: Optional[Path] = None):
        """Initialize the schema validator.

        Args:
            schemas_dir: Directory containing schema files.
                        Defaults to templates/schemas/

        """
        self.schemas: Dict[str, Dict[str, Any]] = {}
        self.validators: Dict[str, Draft7Validator] = {}

        if not JSONSCHEMA_AVAILABLE:
            logger.warning("Schema validation disabled - jsonschema not installed")
            return

        if schemas_dir is None:
            # Default to the schemas directory in templates
            current_dir = Path(__file__).parent
            schemas_dir = current_dir / "templates" / "schemas"

        self.schemas_dir = Path(schemas_dir)

        self._load_schemas()

    def _load_schemas(self) -> None:
        """Load all schema files from the schemas directory."""
        if not self.schemas_dir.exists():
            logger.warning(f"Schemas directory not found: {self.schemas_dir}")
            return

        schema_files = {
            "pm_spec": "pm_spec.schema.json",
            "architect": "architect.schema.json",
            "engineer": "engineer.schema.json",
            "qa": "qa.schema.json",
            "designer": "designer.schema.json",
            "pm_approval": "pm_approval.schema.json",
        }

        for role, filename in schema_files.items():
            schema_path = self.schemas_dir / filename
            if schema_path.exists():
                try:
                    with open(schema_path, "r", encoding="utf-8") as f:
                        schema = json.load(f)
                    self.schemas[role] = schema
                    self.validators[role] = Draft7Validator(schema)
                    logger.debug(f"Loaded schema for {role} from {schema_path}")
                except Exception as e:
                    logger.error(f"Failed to load schema {schema_path}: {e}")
            else:
                logger.warning(f"Schema file not found: {schema_path}")

    def validate(
        self, artifact: Dict[str, Any], role: str, raise_on_error: bool = False
    ) -> Tuple[bool, List[str], List[str]]:
        """Validate an artifact against its schema.

        Args:
            artifact: The artifact data to validate
            role: The role type (pm_spec, architect, engineer, qa, designer)
            raise_on_error: Whether to raise ValidationError on failure

        Returns:
            Tuple of (is_valid, errors, warnings)

        """
        if not JSONSCHEMA_AVAILABLE:
            return True, [], ["Schema validation disabled - jsonschema not installed"]

        # Normalize role name
        role_normalized = role.lower().replace(" ", "_").replace("-", "_")
        if role_normalized == "product_manager":
            role_normalized = "pm_spec"
        elif role_normalized == "ui_designer":
            role_normalized = "designer"

        if role_normalized not in self.validators:
            warning = f"No schema found for role: {role}"
            logger.warning(warning)
            return True, [], [warning]

        validator = self.validators[role_normalized]
        errors: List[str] = []
        warnings: List[str] = []

        try:
            # Validate the artifact
            validator.validate(artifact)
            logger.debug(f"Artifact validation passed for {role}")
            return True, [], []

        except ValidationError as e:
            error_msg = self._format_validation_error(e)
            errors.append(error_msg)
            logger.error(f"Artifact validation failed for {role}: {error_msg}")

            if raise_on_error:
                raise

            return False, errors, warnings

        except Exception as e:
            error_msg = f"Unexpected validation error: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
            return False, errors, warnings

    def _format_validation_error(self, error: ValidationError) -> str:
        """Format a validation error into a human-readable message."""
        path = " -> ".join(str(p) for p in error.absolute_path)
        if path:
            return f"Validation error at '{path}': {error.message}"
        return f"Validation error: {error.message}"

    def get_all_errors(self, artifact: Dict[str, Any], role: str) -> List[str]:
        """Get all validation errors for an artifact (not just the first one).

        Args:
            artifact: The artifact data to validate
            role: The role type

        Returns:
            List of all validation error messages

        """
        if not JSONSCHEMA_AVAILABLE:
            return []

        # Normalize role name
        role_normalized = role.lower().replace(" ", "_").replace("-", "_")
        if role_normalized == "product_manager":
            role_normalized = "pm_spec"
        elif role_normalized == "ui_designer":
            role_normalized = "designer"

        if role_normalized not in self.validators:
            return []

        validator = self.validators[role_normalized]
        errors: List[str] = []

        for error in validator.iter_errors(artifact):
            errors.append(self._format_validation_error(error))

        return errors

    def _add_error_based_suggestions(
        self, errors: List[str], suggestions: List[str]
    ) -> None:
        """Add suggestions based on validation errors.

        Args:
            errors: List of validation errors
            suggestions: List to append suggestions to

        """
        error_suggestion_map = {
            "required": "Ensure all required fields are present in the artifact",
            "type": "Check that field types match the schema (string, number, array, etc.)",
            "minlength": "Provide more detailed descriptions to meet minimum length requirements",
            "pattern": "Ensure string values match the expected format",
        }

        for error in errors:
            error_lower = error.lower()
            for keyword, suggestion in error_suggestion_map.items():
                if keyword in error_lower:
                    suggestions.append(suggestion)
                    break

    def _add_pm_suggestions(
        self, artifact: Dict[str, Any], suggestions: List[str]
    ) -> None:
        """Add Product Manager specific suggestions.

        Args:
            artifact: The artifact data
            suggestions: List to append suggestions to

        """
        if "user_stories" in artifact and isinstance(artifact["user_stories"], list):
            if len(artifact["user_stories"]) < 3:
                suggestions.append(
                    "Consider adding more user stories for comprehensive coverage"
                )

    def _add_architect_api_suggestions(
        self, artifact: Dict[str, Any], suggestions: List[str]
    ) -> None:
        """Add Architect API design suggestions.

        Args:
            artifact: The artifact data
            suggestions: List to append suggestions to

        """
        if "apis" in artifact and isinstance(artifact["apis"], list):
            if len(artifact["apis"]) < 2:
                suggestions.append(
                    "Consider designing more API endpoints for better functionality"
                )

    def _validate_table_columns(
        self,
        table: Dict[str, Any],
        errors: List[str],
        warnings: List[str],
        suggestions: List[str],
    ) -> bool:
        """Validate database table has proper column structure.

        Args:
            table: Table definition
            errors: List to append errors to
            warnings: List to append warnings to
            suggestions: List to append suggestions to

        Returns:
            True if table is valid, False otherwise

        """
        table_name = table.get("name", "Unknown")
        columns = table.get("columns", [])

        # Check for empty columns
        if not columns or not isinstance(columns, list) or len(columns) == 0:
            error_msg = (
                f"Database table '{table_name}' has no columns. "
                "Every table MUST have at least one column (usually 'id' as primary key)."
            )
            errors.append(error_msg)
            suggestions.append(
                f"Add columns to table '{table_name}'. Example: "
                '[{"name": "id", "type": "UUID", "constraints": ["PRIMARY KEY"]}, '
                '{"name": "created_at", "type": "TIMESTAMP", "constraints": ["DEFAULT CURRENT_TIMESTAMP"]}]'
            )
            return False

        # Check for primary key
        has_primary_key = any(
            "PRIMARY KEY" in str(col.get("constraints", [])).upper()
            for col in columns
            if isinstance(col, dict)
        )
        if not has_primary_key:
            warnings.append(
                f"Table '{table_name}' has no primary key column. "
                "Best practice is to have an 'id' column with PRIMARY KEY constraint."
            )
            suggestions.append(
                f"Add a primary key to '{table_name}': "
                '{"name": "id", "type": "UUID", "constraints": ["PRIMARY KEY", "DEFAULT gen_random_uuid()"]}'
            )

        return True

    def _validate_database_schema(
        self,
        artifact: Dict[str, Any],
        errors: List[str],
        warnings: List[str],
        suggestions: List[str],
    ) -> bool:
        """Validate database schema has proper table structure.

        Args:
            artifact: The artifact data
            errors: List to append errors to
            warnings: List to append warnings to
            suggestions: List to append suggestions to

        Returns:
            True if all tables are valid, False otherwise

        """
        if "database_schema" not in artifact:
            return True

        database_schema = artifact["database_schema"]
        if not isinstance(database_schema, dict):
            return True

        tables = database_schema.get("tables", [])
        if not isinstance(tables, list):
            return True

        all_valid = True
        for table in tables:
            if isinstance(table, dict):
                if not self._validate_table_columns(
                    table, errors, warnings, suggestions
                ):
                    all_valid = False

        return all_valid

    def validate_with_suggestions(
        self, artifact: Dict[str, Any], role: str
    ) -> Tuple[bool, List[str], List[str], List[str]]:
        """Validate artifact and provide suggestions for improvement.

        Args:
            artifact: The artifact data to validate
            role: The role type

        Returns:
            Tuple of (is_valid, errors, warnings, suggestions)

        """
        is_valid, errors, warnings = self.validate(artifact, role)
        suggestions: List[str] = []

        # Add suggestions based on validation errors
        if not is_valid:
            self._add_error_based_suggestions(errors, suggestions)

        # Add role-specific suggestions
        if role in ["pm_spec", "Product Manager"]:
            self._add_pm_suggestions(artifact, suggestions)

        elif role in ["architect", "Architect"]:
            self._add_architect_api_suggestions(artifact, suggestions)

            # Validate database schema (critical check)
            schema_valid = self._validate_database_schema(
                artifact, errors, warnings, suggestions
            )
            if not schema_valid:
                is_valid = False

        return is_valid, errors, warnings, list(set(suggestions))


# Global validator instance
_validator_instance: Optional[SchemaValidator] = None


def get_validator() -> SchemaValidator:
    """Get the global schema validator instance (singleton pattern)."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = SchemaValidator()
    return _validator_instance


def validate_artifact(
    artifact: Dict[str, Any], role: str, raise_on_error: bool = False
) -> Tuple[bool, List[str], List[str]]:
    """Convenience function to validate an artifact.

    Args:
        artifact: The artifact data to validate
        role: The role type
        raise_on_error: Whether to raise ValidationError on failure

    Returns:
        Tuple of (is_valid, errors, warnings)

    """
    validator = get_validator()
    return validator.validate(artifact, role, raise_on_error)


def validate_artifact_with_suggestions(
    artifact: Dict[str, Any], role: str
) -> Tuple[bool, List[str], List[str], List[str]]:
    """Convenience function to validate an artifact with suggestions.

    Args:
        artifact: The artifact data to validate
        role: The role type

    Returns:
        Tuple of (is_valid, errors, warnings, suggestions)

    """
    validator = get_validator()
    return validator.validate_with_suggestions(artifact, role)


# Example usage
if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Example artifact
    pm_artifact = {
        "user_stories": [
            {
                "id": "US-001",
                "title": "User Login",
                "story": "As a user I want to login so that I can access my account",
                "priority": "high",
            }
        ],
        "acceptance_criteria": [
            "User can enter email and password",
            "Invalid credentials show error message",
        ],
    }

    # Validate
    is_valid, errors, warnings = validate_artifact(pm_artifact, "Product Manager")

    if is_valid:
        print("✅ Artifact is valid!")
    else:
        print("❌ Artifact validation failed:")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print("⚠️  Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
