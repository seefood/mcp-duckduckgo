"""
Working MCP tools implementation for DuckDuckGo search.
"""
import logging
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field
import httpx
from bs4 import BeautifulSoup
import urllib.parse

from .search_new import search_web, SearchResult, extract_domain

logger = logging.getLogger(__name__)

def register_search_tools(mcp_server: FastMCP):
    """Register all search tools with the MCP server."""

    @mcp_server.tool()
    async def web_search(
        query: str = Field(..., description="Search query", max_length=400),
        max_results: int = Field(10, description="Maximum number of results to return (1-20)", ge=1, le=20),
        ctx: Context = Field(default_factory=Context),
    ) -> Dict[str, Any]:
        """
        Search the web using DuckDuckGo.

        Returns a list of search results with titles, URLs, descriptions, and domains.
        """
        logger.info(f"Searching for: '{query}' (max {max_results} results)")

        try:
            # Get HTTP client from context
            http_client = None
            close_client = False

            # Try to get HTTP client from lifespan context
            if hasattr(ctx, 'lifespan_context') and ctx.lifespan_context and 'http_client' in ctx.lifespan_context:
                logger.info("Using HTTP client from lifespan context")
                http_client = ctx.lifespan_context["http_client"]
            else:
                # Create a new HTTP client
                logger.info("Creating new HTTP client")
                http_client = httpx.AsyncClient(timeout=10.0)
                close_client = True

            try:
                # Perform the search
                results = await search_web(query, http_client, max_results)

                # Convert to dict format
                search_results = [
                    {
                        "title": result.title,
                        "url": result.url,
                        "description": result.description,
                        "domain": result.domain
                    }
                    for result in results
                ]

                return {
                    "query": query,
                    "results": search_results,
                    "total_results": len(search_results),
                    "status": "success"
                }

            finally:
                if close_client:
                    await http_client.aclose()

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "status": "error",
                "error": str(e)
            }

    @mcp_server.tool()
    async def get_page_content(
        url: str = Field(..., description="URL to fetch content from"),
        ctx: Context = Field(default_factory=Context),
    ) -> Dict[str, Any]:
        """
        Fetch and extract content from a web page.

        Returns the page title, description, and main content.
        """
        logger.info(f"Fetching content from: {url}")

        try:
            # Get HTTP client from context
            http_client = getattr(ctx, 'http_client', None)
            if not http_client:
                http_client = httpx.AsyncClient(timeout=15.0)
                close_client = True
            else:
                close_client = False

            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }

                response = await http_client.get(url, headers=headers, timeout=15)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract title
                title = ""
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text().strip()

                # Extract description from meta tags
                description = ""
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    description = meta_desc.get('content', '').strip()

                # Extract main content (try common content selectors)
                content_text = ""
                content_selectors = [
                    'main article', 'article', '[role="main"]',
                    '.content', '.article-content', '.post-content',
                    '#content', '#article', '.entry-content'
                ]

                for selector in content_selectors:
                    main_content = soup.select_one(selector)
                    if main_content:
                        content_text = main_content.get_text().strip()
                        break

                # If no content found, get all paragraphs
                if not content_text:
                    paragraphs = soup.find_all('p')[:5]  # First 5 paragraphs
                    content_text = '\n\n'.join(p.get_text().strip() for p in paragraphs)


                # Clean up content (first 500 chars for preview)
                content_preview = content_text[:500] + "..." if len(content_text) > 500 else content_text

                return {
                    "url": url,
                    "title": title,
                    "description": description,
                    "content": content_text,
                    "content_preview": content_preview,
                    "domain": extract_domain(url),
                    "status": "success"
                }

            finally:
                if close_client:
                    await http_client.aclose()

        except Exception as e:
            logger.error(f"Failed to fetch content from {url}: {e}")
            return {
                "url": url,
                "title": "",
                "description": "",
                "content": "",
                "content_preview": f"Error: {str(e)}",
                "domain": extract_domain(url),
                "status": "error",
                "error": str(e)
            }

    @mcp_server.tool()
    async def suggest_related_searches(
        query: str = Field(..., description="Original search query"),
        ctx: Context = Field(default_factory=Context),
    ) -> Dict[str, Any]:
        """
        Suggest related search queries based on the original query.
        """
        logger.info(f"Getting related searches for: '{query}'")

        # Simple related search suggestions
        query_words = query.lower().split()
        related = []

        if len(query_words) >= 2:
            # Add variations
            base_query = ' '.join(query_words[:-1])
            last_word = query_words[-1]

            variations = [
                f"{base_query} definition",
                f"{base_query} examples",
                f"{base_query} benefits",
                f"{base_query} problems",
                f"{base_query} alternatives",
                f"{base_query} guide",
                f"{base_query} tutorial",
                f"{base_query} latest news",
                f"{base_query} reviews",
                f"{base_query} best practices"
            ]

            related.extend(variations)

        # Add general variations
        general_variations = [
            f"{query} meaning",
            f"{query} vs",
            f"How to {query}",
            f"What is {query}",
            f"{query} alternatives",
            f"{query} guide"
        ]

        related.extend(general_variations)

        # Remove duplicates and limit
        unique_related = []
        seen = set()
        for item in related:
            if item.lower() not in seen and item.lower() != query.lower():
                unique_related.append(item)
                seen.add(item.lower())
                if len(unique_related) >= 10:
                    break

        return {
            "original_query": query,
            "related_searches": unique_related,
            "count": len(unique_related),
            "status": "success"
        }
