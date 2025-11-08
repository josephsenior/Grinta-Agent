"""Command-line entrypoint for launching the Forge server with Uvicorn."""

import os
import warnings

import uvicorn


def main() -> None:
    """Start the Forge server with optimized configuration.

    This function initializes and runs the uvicorn server with performance
    optimizations for development and production environments.
    """
    warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub\\.utils")
    port = int(os.environ.get("port") or "3000")
    
    # Suppress Uvicorn's default startup message and show custom one
    import logging
    import sys
    
    # Print custom startup message before uvicorn starts
    sys.stderr.write(f"\n\033[32mINFO\033[0m:     Uvicorn running on http://localhost:{port} (Press CTRL+C to quit)\n")
    sys.stderr.flush()
    
    # Configure logging to suppress uvicorn's startup message
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(levelprefix)s %(message)s",
                "use_colors": True,
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "WARNING"},  # Suppress INFO startup message
            "uvicorn.error": {"level": "WARNING"},
        },
    }
    uvicorn.run(
        "forge.server.listen:app",
        host="0.0.0.0",  # nosec B104 - Safe: web server intentionally accessible on all interfaces
        port=port,
        log_config=log_config,
        log_level="debug" if os.environ.get("DEBUG") else "info",
        # Performance optimizations
        workers=1,  # Single worker for development
        loop="asyncio",
        http="httptools",  # Faster HTTP parser
        access_log=False,  # Disable access logs in production
    )


if __name__ == "__main__":
    main()
