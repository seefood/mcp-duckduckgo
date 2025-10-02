"""
Working MCP tools implementation for DuckDuckGo search.
"""

import logging
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from .search import COMMON_HEADERS, DEFAULT_TIMEOUT, extract_domain, search_web

logger = logging.getLogger(__name__)

# Tool Configuration
AUTOCOMPLETE_TIMEOUT = 10
PAGE_FETCH_TIMEOUT = 15
CONTENT_PREVIEW_LENGTH = 500
MAX_PREVIEW_PARAGRAPHS = 5

# Allowed URL schemes for security
ALLOWED_URL_SCHEMES = {"http", "https"}

# Content selectors for page extraction
CONTENT_SELECTORS = [
    "main article",
    "article",
    '[role="main"]',
    ".content",
    ".article-content",
    ".post-content",
    "#content",
    "#article",
    ".entry-content",
]


def validate_url(url: str) -> bool:
    """
    Validate URL scheme for security.

    Args:
        url: URL to validate

    Returns:
        True if URL scheme is allowed, False otherwise
    """
    try:
        parsed = urlparse(url)
        return parsed.scheme in ALLOWED_URL_SCHEMES
    except Exception:
        return False


def get_http_client_from_context(ctx: Context) -> tuple[httpx.AsyncClient, bool]:
    """
    Get HTTP client from context or create a new one.

    Args:
        ctx: MCP context object

    Returns:
        Tuple of (http_client, should_close) where should_close indicates
        whether the client should be closed after use
    """
    if (
        hasattr(ctx, "lifespan_context")
        and ctx.lifespan_context
        and "http_client" in ctx.lifespan_context
    ):
        logger.info("Using HTTP client from lifespan context")
        return ctx.lifespan_context["http_client"], False
    else:
        logger.info("Creating new HTTP client")
        return httpx.AsyncClient(timeout=DEFAULT_TIMEOUT), True


async def get_autocomplete_suggestions(
    query: str, http_client: httpx.AsyncClient
) -> List[str]:
    """
    Get search suggestions from DuckDuckGo autocomplete API.

    Args:
        query: Search query to get suggestions for
        http_client: HTTP client to use for the request

    Returns:
        List of suggestion strings
    """
    try:
        url = "https://duckduckgo.com/ac/"
        params = {"q": query, "type": "list"}

        response = await http_client.get(
            url, params=params, timeout=AUTOCOMPLETE_TIMEOUT
        )
        response.raise_for_status()

        data = response.json()
        # Response format: ["query", ["suggestion1", "suggestion2", ...]]
        suggestions = data[1] if len(data) > 1 and isinstance(data[1], list) else []

        logger.info("Found %d autocomplete suggestions", len(suggestions))
        return suggestions

    except (httpx.RequestError, httpx.HTTPError, ValueError) as e:
        logger.error("Failed to get autocomplete suggestions: %s", e)
        return []


def register_search_tools(mcp_server: FastMCP) -> None:
    """Register all search tools with the MCP server."""

    @mcp_server.tool()
    async def web_search(
        query: str = Field(..., description="Search query", max_length=400),
        max_results: int = Field(
            10, description="Maximum number of results to return (1-20)", ge=1, le=20
        ),
        ctx: Context = Field(default_factory=Context),
    ) -> Dict[str, Any]:
        """
        Search the web using DuckDuckGo.

        Args:
            query: Search query string (max 400 chars)
            max_results: Maximum number of results to return (1-20)
            ctx: MCP context object

        Returns:
            Dictionary containing search results with titles, URLs, descriptions, and domains
        """
        logger.info("Searching for: '%s' (max %d results)", query, max_results)

        http_client, close_client = get_http_client_from_context(ctx)

        try:
            # Perform the search
            results = await search_web(query, http_client, max_results)

            # Convert to dict format
            search_results = [
                {
                    "title": result.title,
                    "url": result.url,
                    "description": result.description,
                    "domain": result.domain,
                }
                for result in results
            ]

            return {
                "query": query,
                "results": search_results,
                "total_results": len(search_results),
            }

        except (httpx.RequestError, httpx.HTTPError, ValueError) as e:
            logger.error("Search failed: %s", e)
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "error": str(e),
            }
        finally:
            if close_client:
                await http_client.aclose()

    @mcp_server.tool()
    async def get_page_content(
        url: str = Field(..., description="URL to fetch content from"),
        ctx: Context = Field(default_factory=Context),
    ) -> Dict[str, Any]:
        """
        Fetch and extract content from a web page.

        Args:
            url: URL of the page to fetch (must be http or https)
            ctx: MCP context object

        Returns:
            Dictionary containing page title, description, content, and metadata
        """
        logger.info("Fetching content from: %s", url)

        # Validate URL scheme for security
        if not validate_url(url):
            return {
                "url": url,
                "title": "",
                "description": "",
                "content": "",
                "content_preview": "",
                "domain": extract_domain(url),
                "error": "Invalid URL scheme. Only http and https are allowed.",
            }

        http_client, close_client = get_http_client_from_context(ctx)

        try:
            response = await http_client.get(
                url, headers=COMMON_HEADERS, timeout=PAGE_FETCH_TIMEOUT
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract title
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text().strip()

            # Extract description from meta tags
            description = ""
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                description = meta_desc.get("content", "").strip()  # type: ignore[union-attr]

            # Extract main content (try common content selectors)
            content_text = ""
            for selector in CONTENT_SELECTORS:
                main_content = soup.select_one(selector)
                if main_content:
                    content_text = main_content.get_text().strip()
                    break

            # If no content found, get all paragraphs
            if not content_text:
                paragraphs = soup.find_all("p")[:MAX_PREVIEW_PARAGRAPHS]
                content_text = "\n\n".join(p.get_text().strip() for p in paragraphs)

            # Clean up content (first N chars for preview)
            content_preview = (
                content_text[:CONTENT_PREVIEW_LENGTH] + "..."
                if len(content_text) > CONTENT_PREVIEW_LENGTH
                else content_text
            )

            return {
                "url": url,
                "title": title,
                "description": description,
                "content": content_text,
                "content_preview": content_preview,
                "domain": extract_domain(url),
            }

        except (httpx.RequestError, httpx.HTTPError) as e:
            logger.error("Failed to fetch content from %s: %s", url, e)
            return {
                "url": url,
                "title": "",
                "description": "",
                "content": "",
                "content_preview": "",
                "domain": extract_domain(url),
                "error": str(e),
            }
        finally:
            if close_client:
                await http_client.aclose()

    @mcp_server.tool()
    async def suggest_related_searches(
        query: str = Field(..., description="Original search query"),
        max_suggestions: int = Field(
            5,
            ge=1,
            le=10,
            description="Maximum number of related suggestions to return",
        ),
        ctx: Context = Field(default_factory=Context),
    ) -> Dict[str, Any]:
        """
        Get search suggestions from DuckDuckGo autocomplete API.

        Args:
            query: Original search query
            max_suggestions: Maximum number of suggestions to return (1-10)
            ctx: MCP context object

        Returns:
            Dictionary containing related search suggestions based on what people actually search for
        """
        logger.info(
            "Getting autocomplete suggestions for: '%s' (max %d suggestions)",
            query,
            max_suggestions,
        )

        http_client, close_client = get_http_client_from_context(ctx)

        try:
            # Get autocomplete suggestions from DuckDuckGo
            suggestions = await get_autocomplete_suggestions(query, http_client)

            return {
                "original_query": query,
                "related_searches": suggestions[:max_suggestions],
                "count": len(suggestions[:max_suggestions]),
            }

        except (httpx.RequestError, httpx.HTTPError, ValueError) as e:
            logger.error("Failed to get autocomplete suggestions: %s", e)
            return {
                "original_query": query,
                "related_searches": [],
                "count": 0,
                "error": str(e),
            }
        finally:
            if close_client:
                await http_client.aclose()
