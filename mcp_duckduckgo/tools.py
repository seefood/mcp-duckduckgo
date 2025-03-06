"""
MCP tool definitions for the DuckDuckGo search plugin.
"""

import logging
import traceback
from typing import List, Dict, Any, Optional
import urllib.parse
from pydantic import Field
from mcp.server.fastmcp import Context

from .models import SearchResponse, SearchResult, DetailedResult
from .search import duckduckgo_search, extract_domain
from .server import mcp

# Configure logging
logger = logging.getLogger("mcp_duckduckgo.tools")

@mcp.tool()  # noqa: F401 # pragma: no cover
async def duckduckgo_web_search(  # vulture: ignore
    query: str = Field(
        ...,
        description="Search query (max 400 chars, 50 words)",
        max_length=400,
    ),
    count: int = Field(
        default=10,
        description="Number of results per page (1-20, default 10)",
        ge=1,
        le=20,
    ),
    page: int = Field(
        default=1,
        description="Page number (default 1)",
        ge=1,
    ),
    site: Optional[str] = Field(
        default=None,
        description="Limit results to a specific site (e.g., 'site:example.com')",
    ),
    time_period: Optional[str] = Field(
        default=None,
        description="Time period for results ('day', 'week', 'month', 'year')",
    ),
    ctx: Context = None,  # Context is automatically injected by MCP
) -> SearchResponse:
    """
    Perform a web search using the DuckDuckGo search engine.
    
    This tool searches the web using DuckDuckGo and returns relevant results.
    It's ideal for finding current information, news, articles, and general web content.
    
    Args:
        query: The search query (max 400 chars, 50 words)
        count: Number of results per page (1-20, default 10)
        page: Page number for pagination (default 1)
        site: Limit results to a specific site (e.g., 'site:example.com')
        time_period: Filter results by time period ('day', 'week', 'month', 'year')
        ctx: MCP context object (automatically injected)
        
    Returns:
        A SearchResponse object containing search results and pagination metadata
    
    Example:
        duckduckgo_web_search(query="latest AI developments", count=5, page=1)
    """
    try:
        logger.info(f"duckduckgo_web_search called with query: {query}, count: {count}, page: {page}")
        
        # Enhance query with site limitation if provided
        if site:
            if not "site:" in query:
                query = f"{query} site:{site}"
        
        # Enhance query with time period if provided
        if time_period:
            # Map time_period to DuckDuckGo format
            time_map = {
                "day": "d",
                "week": "w",
                "month": "m",
                "year": "y"
            }
            if time_period.lower() in time_map:
                query = f"{query} date:{time_map[time_period.lower()]}"
                
        # Log the context to help with debugging
        if ctx:
            logger.info(f"Context available: {ctx}")
        else:
            logger.error("Context is None!")
            # Create a minimal context if none is provided
            from pydantic import BaseModel
            class MinimalContext(BaseModel):
                pass
            ctx = MinimalContext()
        
        # Calculate offset from page number
        offset = (page - 1) * count
        
        result = await duckduckgo_search({
            "query": query,
            "count": count,
            "offset": offset,
            "page": page
        }, ctx)
        
        logger.info(f"duckduckgo_search returned: {result}")
        
        # Convert the result to a SearchResponse object
        search_results = []
        for item in result["results"]:
            try:
                search_result = SearchResult(
                    title=item["title"],
                    url=item["url"],
                    description=item["description"],
                    published_date=item.get("published_date")
                )
                search_results.append(search_result)
            except Exception as e:
                logger.error(f"Error creating SearchResult: {e}, item: {item}")
                if hasattr(ctx, 'error'):
                    await ctx.error(f"Error creating SearchResult: {e}, item: {item}")
        
        # Calculate pagination metadata
        total_results = result["total_results"]
        total_pages = (total_results + count - 1) // count if total_results > 0 else 1
        has_next = page < total_pages
        has_previous = page > 1
        
        response = SearchResponse(
            results=search_results,
            total_results=total_results,
            page=page,
            total_pages=total_pages,
            has_next=has_next,
            has_previous=has_previous
        )
        
        logger.info(f"Returning SearchResponse: {response}")
        return response
    except Exception as e:
        error_msg = f"Error in duckduckgo_web_search: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        if hasattr(ctx, 'error'):
            await ctx.error(error_msg)
        
        # Return an empty response instead of raising an exception
        # This way, the tool will return something even if there's an error
        return SearchResponse(
            results=[],
            total_results=0,
            page=page,
            total_pages=1,
            has_next=False,
            has_previous=False
        )

@mcp.tool()  # noqa: F401 # pragma: no cover
async def duckduckgo_get_details(  # vulture: ignore
    url: str = Field(
        ...,
        description="URL of the result to get details for",
    ),
    ctx: Context = None,  # Context is automatically injected by MCP
) -> DetailedResult:
    """
    Get detailed information about a search result.
    
    This tool retrieves additional details about a search result,
    such as the domain, a content snippet, and whether it's an
    official source.
    
    Args:
        url: The URL of the result to get details for
        ctx: MCP context object (automatically injected)
        
    Returns:
        A DetailedResult object with additional information
        
    Example:
        duckduckgo_get_details(url="https://example.com/article")
    """
    try:
        logger.info(f"duckduckgo_get_details called with URL: {url}")
        
        # Log the context to help with debugging
        if ctx:
            logger.info(f"Context available: {ctx}")
        else:
            logger.error("Context is None!")
            # Create a minimal context if none is provided
            from pydantic import BaseModel
            class MinimalContext(BaseModel):
                pass
            ctx = MinimalContext()
            
        # Extract the domain from the URL
        domain = extract_domain(url)
        
        # Create a basic detailed result
        # In a real implementation, you would fetch the page content
        # and extract more details
        detailed_result = DetailedResult(
            title="",  # In a real implementation, this would be extracted from the page
            url=url,
            description="",  # In a real implementation, this would be extracted from the page
            published_date=None,
            content_snippet="Content not available",  # Placeholder
            domain=domain,
            is_official=False  # Default, in a real implementation this would be determined
        )
        
        # In a real implementation, you would fetch the page content
        # and extract more details using httpx and BeautifulSoup
        
        logger.info(f"Returning DetailedResult: {detailed_result}")
        return detailed_result
    except Exception as e:
        error_msg = f"Error in duckduckgo_get_details: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        if hasattr(ctx, 'error'):
            await ctx.error(error_msg)
        
        # Return a minimal result instead of raising an exception
        return DetailedResult(
            title="Error",
            url=url,
            description=f"Error retrieving details: {str(e)}",
            content_snippet=None,
            domain=extract_domain(url) if url else None,
            is_official=False
        )

@mcp.tool()  # noqa: F401 # pragma: no cover
async def duckduckgo_related_searches(  # vulture: ignore
    query: str = Field(
        ...,
        description="Original search query",
        max_length=400,
    ),
    count: int = Field(
        default=5,
        description="Number of related searches to return (1-10, default 5)",
        ge=1,
        le=10,
    ),
    ctx: Context = None,  # Context is automatically injected by MCP
) -> List[str]:
    """
    Get related search queries for a given query.
    
    This tool suggests alternative search queries related to
    the original query, which can help explore a topic more broadly.
    
    Args:
        query: The original search query
        count: Number of related searches to return (1-10, default 5)
        ctx: MCP context object (automatically injected)
        
    Returns:
        A list of related search queries
        
    Example:
        duckduckgo_related_searches(query="artificial intelligence", count=5)
    """
    try:
        logger.info(f"duckduckgo_related_searches called with query: {query}, count: {count}")
        
        # Log the context to help with debugging
        if ctx:
            logger.info(f"Context available: {ctx}")
        else:
            logger.error("Context is None!")
            # Create a minimal context if none is provided
            from pydantic import BaseModel
            class MinimalContext(BaseModel):
                pass
            ctx = MinimalContext()
            
        # In a real implementation, you would fetch related searches
        # from DuckDuckGo or generate them algorithmically
        
        # For demonstration purposes, generate some placeholder related searches
        words = query.split()
        related_searches = [
            f"{query} latest news",
            f"{query} examples",
            f"best {query}",
            f"{query} tutorial",
            f"{query} definition",
            f"how does {query} work",
            f"{query} vs {words[0] if words else 'alternative'}",
            f"future of {query}",
            f"{query} applications",
            f"{query} history"
        ][:count]
        
        logger.info(f"Returning related searches: {related_searches}")
        return related_searches
    except Exception as e:
        error_msg = f"Error in duckduckgo_related_searches: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        if hasattr(ctx, 'error'):
            await ctx.error(error_msg)
        
        # Return an empty list instead of raising an exception
        return []