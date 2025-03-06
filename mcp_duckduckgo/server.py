"""
Server setup and lifespan management for the DuckDuckGo search plugin.
"""

import logging
from typing import Dict, Any, AsyncIterator
from contextlib import asynccontextmanager

import httpx
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_duckduckgo.server")

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    """Manage application lifecycle with proper resource initialization and cleanup."""
    try:
        # Initialize resources on startup
        logger.info("Initializing DuckDuckGo search server")
        http_client = httpx.AsyncClient(
            timeout=10.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            }
        )
        yield {"http_client": http_client}
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down DuckDuckGo search server")
        await http_client.aclose()

# Initialize FastMCP server with lifespan
mcp = FastMCP(
    "DuckDuckGo Search", 
    version="0.1.0",
    port=3000, 
    transport={
        "type": "sse",
        "endpoint": "/sse"
    },
    lifespan=app_lifespan
) 