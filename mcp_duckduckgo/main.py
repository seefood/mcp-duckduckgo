"""
DuckDuckGo search plugin for Model Context Protocol.
This module implements a web search function using the DuckDuckGo API.
"""

import argparse
import logging
import importlib
import os
import sys
from typing import Any

# Configure logging
logger = logging.getLogger("mcp_duckduckgo")

def configure_logging():
    """Configure logging based on environment."""
    # Check if we're running in stdio mode (MCP tool) or server mode
    if sys.stdin.isatty() and sys.stdout.isatty():
        # Running in terminal - configure verbose logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        # Running as MCP tool (stdio) - disable logging to avoid interfering with protocol
        logging.basicConfig(level=logging.CRITICAL)

def initialize_mcp() -> Any:
    """Initialize MCP server and register components."""
    # Import server module and create server instance
    server_module = importlib.import_module(".server", package="mcp_duckduckgo")
    mcp = server_module.create_mcp_server()

    # Import all MCP components to register them
    importlib.import_module(".tools", package="mcp_duckduckgo")
    importlib.import_module(".resources", package="mcp_duckduckgo")
    importlib.import_module(".prompts", package="mcp_duckduckgo")

    return mcp

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DuckDuckGo search plugin for Model Context Protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port number for the MCP server (default: 3000)"
    )
    return parser.parse_args()

def main():
    """Run the MCP server."""
    # Configure logging first
    configure_logging()
    
    try:
        # Parse command line arguments
        args = parse_args()

        # Initialize MCP server
        mcp = initialize_mcp()

        # Check if we're running in server mode or stdio mode
        if sys.stdin.isatty() and sys.stdout.isatty():
            # Server mode - use port configuration
            if args.port != 3000:
                os.environ["MCP_PORT"] = str(args.port)
            logger.info("Starting DuckDuckGo Search MCP server on port %s", args.port)
            logger.info("Available endpoints:")
            logger.info("- Tool: duckduckgo_web_search")
            logger.info("- Tools: duckduckgo_get_details")
            logger.info("- Tool: duckduckgo_related_searches")
            logger.info("- Resource: docs://search")
            logger.info("- Resource: search://{query}")
            logger.info("- Prompt: search_assistant")
        # In stdio mode, FastMCP will automatically detect and handle protocol

        # Run the MCP server
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error("Error starting server: %s", e, exc_info=True)
        raise

if __name__ == "__main__":
    main()
