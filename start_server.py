#!/usr/bin/env python3
"""Start the Forge backend server with correct Python path."""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Set environment variables
os.environ.setdefault("PORT", "3000")
os.environ.setdefault("SERVE_FRONTEND", "true")

# Now import and run uvicorn
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "3000"))
    print(f"🚀 Starting Forge server on http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop the server.\n")
    
    uvicorn.run(
        "backend.server.listen:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        reload=True,
        reload_excludes=["./workspace"],
    )
