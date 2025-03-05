"""
DuckDuckGo search plugin for Model Context Protocol.
This module implements a web search function using the DuckDuckGo API.
"""

import os
import logging
from typing import List, Optional, Dict, Any, AsyncIterator
from contextlib import asynccontextmanager

import httpx
from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_duckduckgo")

# Load environment variables
load_dotenv()

# Define lifespan for proper resource management
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

# Get environment variables
DEFAULT_COUNT = int(os.getenv("MCP_DUCKDUCKGO_DEFAULT_COUNT", "10"))
MAX_COUNT = int(os.getenv("MCP_DUCKDUCKGO_MAX_COUNT", "20"))

# Define the DuckDuckGo search function parameter schema
class DuckDuckGoSearchParams(BaseModel):
    """Parameters for DuckDuckGo search function."""
    
    query: str = Field(
        ...,
        description="Search query (max 400 chars, 50 words)",
        max_length=400,
    )
    count: int = Field(
        default=10,
        description="Number of results (1-20, default 10)",
        ge=1,
        le=20,
    )
    offset: int = Field(
        default=0,
        description="Pagination offset (default 0)",
        ge=0,
    )

class SearchResult(BaseModel):
    """A single search result."""
    
    title: str
    url: str
    description: str
    published_date: Optional[str] = None

class SearchResponse(BaseModel):
    """Response from DuckDuckGo search."""
    
    results: List[SearchResult]
    total_results: int

async def duckduckgo_search(params: Dict[str, Any], ctx: Context) -> Dict[str, Any]:
    """
    Perform a web search using DuckDuckGo API.
    
    Args:
        params: Dictionary containing search parameters
        ctx: MCP context object providing access to lifespan resources
        
    Returns:
        Dictionary with search results
    """
    query = params.get("query")
    count = params.get("count", 10)
    offset = params.get("offset", 0)
    
    if not query:
        logger.error("Query parameter is required")
        raise ValueError("Query parameter is required")
    
    logger.info(f"Searching DuckDuckGo for: {query}")
    
    # We'll use the DuckDuckGo Lite API endpoint which doesn't require an API key
    # This is for demonstration purposes. For production, consider using a proper search API
    url = "https://lite.duckduckgo.com/lite/"
    
    # Get the HTTP client from the lifespan context
    http_client = ctx.lifespan_context["http_client"]
    
    try:
        # Log the search operation
        ctx.info(f"Searching for: {query}")
        
        response = await http_client.post(
            url,
            data={
                "q": query,
                "kl": "wt-wt",  # No region localization
            },
            timeout=10.0,
        )
        response.raise_for_status()
        
        # Parse the HTML response to extract search results
        # Note: This is a simplified implementation and might break if DuckDuckGo changes their HTML structure
        # For a production service, consider using a more robust solution
        
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        
        # Find all result rows in the HTML
        result_rows = soup.find_all("tr", class_="result-link")
        result_snippets = soup.find_all("tr", class_="result-snippet")
        
        total_results = len(result_rows)
        
        # Report progress to the client
        await ctx.report_progress(0, total_results)
        
        # Extract only the requested number of results starting from the offset
        for i in range(min(count, len(result_rows))):
            if offset + i >= len(result_rows):
                break
                
            title_elem = result_rows[offset + i].find("a")
            if not title_elem:
                continue
                
            title = title_elem.text.strip()
            url = title_elem.get("href", "")
            
            description = ""
            if offset + i < len(result_snippets):
                description = result_snippets[offset + i].text.strip()
            
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    description=description,
                    published_date=None,
                )
            )
            
            # Update progress
            await ctx.report_progress(i + 1, total_results)
        
        return {
            "results": [result.model_dump() for result in results],
            "total_results": total_results,
        }
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {e}")
        ctx.error(f"HTTP error: {str(e)}")
        raise ValueError(f"HTTP error: {str(e)}")
    except httpx.RequestError as e:
        logger.error(f"Request error occurred: {e}")
        ctx.error(f"Request error: {str(e)}")
        raise ValueError(f"Request error: {str(e)}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        ctx.error(f"Unexpected error: {str(e)}")
        raise ValueError(f"Unexpected error: {str(e)}")

@mcp.tool()
async def duckduckgo_web_search(
    query: str = Field(
        ...,
        description="Search query (max 400 chars, 50 words)",
        max_length=400,
    ),
    count: int = Field(
        default=10,
        description="Number of results (1-20, default 10)",
        ge=1,
        le=20,
    ),
    offset: int = Field(
        default=0,
        description="Offset for pagination (default 0)",
        ge=0,
    ),
    ctx: Context = None,  # Context is automatically injected by MCP
) -> SearchResponse:
    """
    Perform a web search using the DuckDuckGo search engine.
    
    This tool searches the web using DuckDuckGo and returns relevant results.
    It's ideal for finding current information, news, articles, and general web content.
    
    Args:
        query: The search query (max 400 chars, 50 words)
        count: Number of results to return (1-20, default 10)
        offset: Pagination offset for retrieving additional results (default 0)
        ctx: MCP context object (automatically injected)
        
    Returns:
        A SearchResponse object containing search results and total count
    
    Example:
        duckduckgo_web_search(query="latest AI developments", count=5)
    """
    result = await duckduckgo_search({
        "query": query,
        "count": count,
        "offset": offset
    }, ctx)
    
    # Convert the result to a SearchResponse object
    return SearchResponse(
        results=[SearchResult(**r) for r in result["results"]],
        total_results=result["total_results"]
    )

@mcp.resource("docs://search")
def get_search_docs() -> str:
    """
    Provides documentation about the DuckDuckGo search functionality.
    """
    return """
    # DuckDuckGo Search API
    
    This MCP server provides a web search capability using DuckDuckGo.
    
    ## Usage
    
    Use the `duckduckgo_web_search` tool to search the web:
    
    ```python
    result = await duckduckgo_web_search(
        query="your search query",
        count=10,  # Number of results (1-20)
        offset=0   # For pagination
    )
    ```
    
    ## Response Format
    
    The search returns a structured response with:
    
    - `results`: List of search results, each containing:
      - `title`: The title of the result
      - `url`: The URL of the result
      - `description`: A snippet or description of the result
      - `published_date`: Publication date if available
    - `total_results`: Total number of results found
    
    ## Limitations
    
    - Maximum query length is 400 characters or 50 words
    - Results are limited to 20 per request
    - This is a simplified implementation using DuckDuckGo Lite
    """

@mcp.prompt()
def search_assistant(topic: str = Field(..., description="The topic to search for")) -> str:
    """
    Creates a prompt to help formulate an effective search query for the given topic.
    """
    return f"""
    I need to search for information about {topic}.
    
    Please help me formulate an effective search query that will:
    1. Be specific and focused
    2. Use relevant keywords
    3. Avoid unnecessary words
    4. Be under 400 characters
    
    Then, use the duckduckgo_web_search tool with this query to find the most relevant information.
    """

@mcp.resource("search://{query}")
async def get_search_results(query: str, ctx: Context) -> str:
    """
    Provides search results for a specific query as a resource.
    
    Args:
        query: The search query
        ctx: MCP context object
        
    Returns:
        Formatted search results as text
    """
    # Limit to 5 results for resources to keep the response concise
    result = await duckduckgo_search({
        "query": query,
        "count": 5,
        "offset": 0
    }, ctx)
    
    # Format the results as markdown
    formatted_results = f"# Search Results for: {query}\n\n"
    
    for i, item in enumerate(result["results"], 1):
        formatted_results += f"## {i}. {item['title']}\n"
        formatted_results += f"URL: {item['url']}\n\n"
        formatted_results += f"{item['description']}\n\n"
        if item.get('published_date'):
            formatted_results += f"Published: {item['published_date']}\n\n"
        formatted_results += "---\n\n"
    
    formatted_results += f"\nTotal results found: {result['total_results']}"
    
    return formatted_results

def main():
    """Run the MCP server."""
    try:
        logger.info("Starting DuckDuckGo Search MCP server on port 3000")
        logger.info("Available endpoints:")
        logger.info("- Tool: duckduckgo_web_search")
        logger.info("- Resource: docs://search")
        logger.info("- Resource: search://{query}")
        logger.info("- Prompt: search_assistant")
        
        # Run the MCP server
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
