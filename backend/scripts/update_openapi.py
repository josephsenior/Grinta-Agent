"""Update Forge OpenAPI documentation.

Generates the OpenAPI specification from the FastAPI application and writes it
to docs/openapi.json.

Usage:
    python scripts/update_openapi.py

Behavior:
- Uses forge.server.app.app.openapi() to build the spec.
- Preserves existing "servers" from docs/openapi.json if present; otherwise
  writes sensible defaults.
- Sets info.version to forge.__version__.
# - Excludes operational/UI-only convenience endpoints:
#   - /server_info
#   - /api/conversations/{conversation_id}/web-hosts
# - Creates a backup docs/openapi.json.backup before overwriting.

Output:
- Prints OpenAPI and API versions, endpoint count, servers count, and sample endpoints.
"""

import json
import logging
import os
import sys
import warnings
from pathlib import Path

logging.getLogger().setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")
os.environ["FORGE_LOG_LEVEL"] = "CRITICAL"
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
try:
    from forge import __version__
    from forge.server.app import app
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.exception("Error importing Forge modules: %s", e)
    logger.error(
        "Make sure you're running this script from the project root and dependencies are installed."
    )
    sys.exit(1)


def _sanitize_description(text: str) -> str:
    """Remove internal, code-centric, or redundant sections from endpoint descriptions.

    - Strip fenced code blocks
    - Remove Args/Returns/Raises/Example/Examples/Notes sections
    - Remove inline curl examples
    - Avoid provider-implementation specifics like Bedrock
    """
    import re

    if not text:
        return text
    text = re.sub("```[\\s\\S]*?```", "", text, flags=re.MULTILINE)
    for header in ["Args?:", "Returns?:", "Raises?:", "Example[s]?:", "Notes?:"]:
        text = re.sub(f"(?ms)^\\s*{header}.*?(?:\\n\\s*\\n|\\Z)", "", text)
    text = re.sub("(?im)^.*\\bcurl\\b.*$", "", text)
    text = re.sub("\\bBedrock\\b", "", text)
    text = re.sub("\\n{3,}", "\n\n", text).strip()
    return text


def _sanitize_spec(spec: dict) -> dict:
    """Sanitize descriptions and summaries to be public-API friendly."""
    path_summary_overrides = {
        "/api/options/models": "List Supported Models",
        "/api/options/agents": "List Agents",
        "/api/options/security-analyzers": "List Security Analyzers",
        "/api/conversations/{conversation_id}/list-files": "List Workspace Files",
        "/api/conversations/{conversation_id}/select-file": "Get File Content",
        "/api/conversations/{conversation_id}/zip-directory": "Download Workspace Archive",
    }
    path_description_overrides = {
        "/api/options/models": "List model identifiers available on this server based on configured providers.",
        "/api/options/agents": "List available agent types supported by this server.",
        "/api/options/security-analyzers": "List supported security analyzers.",
        "/api/conversations/{conversation_id}/list-files": "List workspace files visible to the conversation runtime. Applies .gitignore and internal ignore rules.",
        "/api/conversations/{conversation_id}/select-file": "Return the content of the given file from the conversation workspace.",
        "/api/conversations/{conversation_id}/zip-directory": "Return a ZIP archive of the current conversation workspace.",
    }
    for path, methods in list(spec.get("paths", {}).items()):
        for method, meta in list(methods.items()):
            if not isinstance(meta, dict):
                continue
            if path in path_summary_overrides:
                meta["summary"] = path_summary_overrides[path]
            if path in path_description_overrides:
                meta["description"] = path_description_overrides[path]
            elif "description" in meta and isinstance(meta["description"], str):
                meta["description"] = _sanitize_description(meta["description"])
    return spec


def generate_openapi_spec():
    """Generate the OpenAPI specification from the FastAPI app."""
    spec = app.openapi()
    if "paths" in spec:
        excluded_endpoints = [
            "/api/conversations/{conversation_id}/exp-config",
            "/server_info",
            "/api/conversations/{conversation_id}/vscode-url",
            "/api/conversations/{conversation_id}/web-hosts",
        ]
        for endpoint in excluded_endpoints:
            if endpoint in spec["paths"]:
                del spec["paths"][endpoint]
                logging.getLogger(__name__).info("Excluded endpoint: %s", endpoint)
    spec = _sanitize_spec(spec)
    return spec


def load_current_spec(spec_path):
    """Load the current OpenAPI specification if it exists."""
    if spec_path.exists():
        with open(spec_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def update_openapi_spec(spec_path, backup=True):
    """Update the OpenAPI specification file."""
    new_spec = generate_openapi_spec()
    current_spec = load_current_spec(spec_path)
    if "servers" in current_spec:
        new_spec["servers"] = current_spec["servers"]
    else:
        new_spec["servers"] = [
            {"url": "https://api.forge.dev", "description": "Production server"},
            {"url": "http://localhost:3000", "description": "Local server"},
        ]
    new_spec["info"]["version"] = __version__
    if backup and spec_path.exists():
        backup_path = spec_path.with_suffix(".json.backup")
        spec_path.rename(backup_path)
        logging.getLogger(__name__).info("Backed up current spec to %s", backup_path)
    with open(spec_path, "w", encoding="utf-8") as f:
        json.dump(new_spec, f, indent=2)
    return new_spec


def main():
    """Main function."""
    spec_path = project_root / "docs" / "openapi.json"
    logger = logging.getLogger(__name__)
    logger.info("Updating OpenAPI specification...")
    logger.info("Target file: %s", spec_path)
    try:
        new_spec = update_openapi_spec(spec_path)
        logger.info("✅ Successfully updated OpenAPI specification!")
        logger.info("   OpenAPI version: %s", new_spec.get("openapi", "N/A"))
        logger.info(
            "   API version: %s", new_spec.get("info", {}).get("version", "N/A")
        )
        logger.info("   Total endpoints: %d", len(new_spec.get("paths", {})))
        logger.info("   Servers: %d", len(new_spec.get("servers", [])))
        if paths := list(new_spec.get("paths", {}).keys()):
            logger.info("   Sample endpoints:")
            for path in sorted(paths)[:5]:
                methods = list(new_spec["paths"][path].keys())
                logger.info("     %s: %s", path, methods)
            if len(paths) > 5:
                logger.info("     ... and %d more", len(paths) - 5)
    except Exception as e:
        logger.exception("❌ Error updating OpenAPI specification: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
