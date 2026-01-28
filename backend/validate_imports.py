"""Validate all imports before starting the server.

This script attempts to import all modules used by the server to catch
missing dependencies or modules before runtime.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

errors = []
warnings = []


def try_import(module_name: str, description: str = "") -> bool:
    """Try to import a module and report errors."""
    try:
        __import__(module_name)
        return True
    except ImportError as e:
        errors.append(f"[ERROR] {module_name}: {e}")
        if description:
            errors[-1] += f" ({description})"
        return False
    except Exception as e:
        warnings.append(f"[WARNING] {module_name}: {e}")
        if description:
            warnings[-1] += f" ({description})"
        return False


def main():
    """Validate all server imports."""
    print("Validating server imports...\n")
    
    # Core imports
    print("Checking core modules...")
    try_import("forge.server.app", "Main FastAPI app")
    try_import("forge.server.listen", "Server entry point")
    
    # Route imports (from app.py)
    print("\nChecking route modules...")
    routes_to_check = [
        ("forge.server.routes.conversation", "Conversation routes"),
        ("forge.server.routes.features", "Features routes"),
        ("forge.server.routes.feedback", "Feedback routes"),
        ("forge.server.routes.files", "File routes"),
        ("forge.server.routes.git", "Git routes"),
        ("forge.server.routes.global_export", "Export routes"),
        ("forge.server.routes.knowledge_base", "Knowledge base routes"),
        ("forge.server.routes.manage_conversations", "Manage conversations routes"),
        ("forge.server.routes.memory", "Memory routes"),
        ("forge.server.routes.monitoring", "Monitoring routes"),
        ("forge.server.routes.public", "Public API routes"),
        ("forge.server.routes.secrets", "Secrets routes"),
        ("forge.server.routes.settings", "Settings routes"),
        ("forge.server.routes.templates", "Templates routes"),
        ("forge.server.routes.trajectory", "Trajectory routes"),
        ("forge.server.routes.dashboard", "Dashboard routes"),
        ("forge.server.routes.profile", "Profile routes"),
        ("forge.server.routes.notifications", "Notifications routes"),
        ("forge.server.routes.search", "Search routes"),
        ("forge.server.routes.activity", "Activity routes"),
        ("forge.server.routes.mcp", "MCP routes"),
        ("forge.server.routes.auth", "Auth routes"),
        ("forge.server.routes.user_management", "User management routes"),
        ("forge.server.routes.billing", "Billing routes"),
    ]
    
    for module_name, description in routes_to_check:
        try_import(module_name, description)
    
    # Print results
    print("\n" + "=" * 70)
    if warnings:
        print(f"\n[WARNING] {len(warnings)} warning(s):")
        for warning in warnings:
            print(f"  {warning}")
    
    if errors:
        print(f"\n[ERROR] {len(errors)} error(s) found:")
        for error in errors:
            print(f"  {error}")
        print("\n[TIP] Fix these errors before starting the server.")
        return 1
    else:
        print("\n[SUCCESS] All imports validated successfully!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
