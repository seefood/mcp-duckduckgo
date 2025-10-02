"""
MCP tool definitions for the DuckDuckGo search plugin.
This version fixes tool registration by accepting an mcp instance.
"""
import logging
import traceback
from typing import List, Dict, Any, Optional
import urllib.parse
from pydantic import Field
from mcp.server.fastmcp import Context
import httpx
from bs4 import BeautifulSoup

from .models import SearchResponse, SearchResult, DetailedResult
from .search import duckduckgo_search, extract_domain

# Configure logging
logger = logging.getLogger("mcp_duckduckgo.tools")

def register_tools(mcp_instance):
    """Register all tools with the given MCP instance."""
    
    @mcp_instance.tool()
    async def duckduckgo_web_search(
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
            description="Page number for pagination (default 1)",
            ge=1,
        ),
        site: Optional[str] = Field(
            default=None,
            description="Limit results to a specific site (e.g., 'example.com')",
        ),
        time_period: Optional[str] = Field(
            default=None,
            description="Filter results by time period: 'hour', 'day', 'week', 'month', 'year'",
        ),
        ctx: Context = Field(default_factory=Context),
    ) -> SearchResponse:
        """
        Perform a web search using DuckDuckGo.

        This function searches the web using DuckDuckGo's public search interface
        and returns structured results with metadata.
        """
        logger.info("Executing DuckDuckGo web search")
        logger.info("Query: %s, Count: %s, Page: %s", query, count, page)

        try:
            if site:
                logger.info("Site filter: %s", site)
            if time_period:
                logger.info("Time period filter: %s", time_period)

            # Perform the search
            results = await duckduckgo_search(
                query=query,
                count=count,
                page=page,
                site=site,
                time_period=time_period,
                http_client=ctx.http_client,
            )

            logger.info("Search completed. Found %d results", len(results.results))
            return results

        except Exception as e:
            logger.error("Search failed: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            raise

    @mcp_instance.tool()
    async def duckduckgo_get_details(
        url: str = Field(
            ...,
            description="URL to get detailed information about",
        ),
        ctx: Context = Field(default_factory=Context),
    ) -> DetailedResult:
        """
        Get detailed information about a specific URL from DuckDuckGo search results.
        """
        logger.info("Getting details for URL: %s", url)

        try:
            # Use the same HTTP client with proper headers
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                })
                response.raise_for_status()
                html = response.text

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # Extract title
            title = soup.find('title')
            title_text = title.get_text().strip() if title else url

            # Extract description from meta tags
            description = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '').strip()
            elif not description:
                # Fallback: try to get first paragraph
                first_p = soup.find('p')
                if first_p:
                    description = first_p.get_text()[:200] + "..." if len(first_p.get_text()) > 200 else first_p.get_text()

            # Extract domain
            domain = extract_domain(url)

            # Create result
            result = DetailedResult(
                url=url,
                title=title_text,
                description=description,
                domain=domain,
                content_type="text/html",
            )

            logger.info("Successfully extracted details for %s", url)
            return result

        except Exception as e:
            logger.error("Failed to get details for %s: %s", url, str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            raise

    @mcp_instance.tool()
    async def duckduckgo_related_searches(
        query: str = Field(
            ...,
            description="Original search query to find related searches for",
            max_length=400,
        ),
        count: int = Field(
            default=5,
            description="Number of related searches to return (1-10, default 5)",
            ge=1,
            le=10,
        ),
        ctx: Context = Field(default_factory=Context),
    ) -> List[str]:
        """
        Get related search suggestions based on the original query.
        """
        logger.info("Getting related searches for: %s", query)

        try:
            # This is a simplified implementation
            # In a real implementation, you might scrape related searches from DuckDuckGo
            # or use their search suggestions API
            
            # For now, return some example related searches based on common patterns
            related_searches = []
            
            # Add variations of the query
            query_words = query.lower().split()
            if len(query_words) > 1:
                related_searches.extend([
                    f"{' '.join(query_words[:-1])} alternatives",
                    f"{' '.join(query_words[:-1])} guide",
                    f"{' '.join(query_words[:-1])} tutorial",
                ])
            
            # Add some generic related terms
            related_searches.extend([
                f"{query} news",
                f"{query} benefits", 
                f"{query} problems",
            ])
            
            # Limit to requested count and remove duplicates
            result = list(dict.fromkeys(related_searches))[:count]
            
            logger.info("Generated %d related searches", len(result))
            return result

        except Exception as e:
            logger.error("Failed to get related searches: %s", str(e))
            logger.error("Traceback: %s", traceback.format_exc())
            raise
