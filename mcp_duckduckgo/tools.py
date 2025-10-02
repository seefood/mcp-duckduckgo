"""
Working MCP tools implementation for DuckDuckGo search.
"""

import logging
from typing import Any, Dict, List

import httpx
from bs4 import BeautifulSoup
from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from .search import extract_domain, search_web

logger = logging.getLogger(__name__)


async def get_real_related_searches(
    query: str, http_client: httpx.AsyncClient
) -> List[str]:
    """Get actual related searches from DuckDuckGo HTML."""
    try:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        response = await http_client.get(
            url, params=params, headers=headers, timeout=15
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Look for DuckDuckGo's related searches section
        related_selectors = [
            ".module--related",  # DuckDuckGo related module
            ".related-sites",  # Alternative related sites selector
            ".search-filters",  # Search filter suggestions
            "a[data-result-id]",  # Result links that might be suggestions
        ]

        suggestions = []
        for selector in related_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text().strip()
                if text and len(text) > 3 and text.lower() != query.lower():
                    suggestions.append(text)
                    if len(suggestions) >= 10:
                        break

            if suggestions:
                break

        # If no specific related section found, try to extract from result snippets
        if not suggestions:
            result_snippets = soup.select(".result__snippet")
            for snippet in result_snippets[:5]:
                text = snippet.get_text().strip()
                # Extract potential search terms from snippets
                words = text.split()
                if len(words) >= 3:
                    # Create variations using words from snippet
                    for i in range(len(words) - 2):
                        suggestion = " ".join(words[i : i + 3])
                        if suggestion.lower() != query.lower() and len(suggestion) > 5:
                            suggestions.append(suggestion)
                            if len(suggestions) >= 10:
                                break

        logger.info("Found %d related searches from HTML", len(suggestions))
        return list(set(suggestions))[:10]  # Remove duplicates and limit

    except (httpx.RequestError, httpx.HTTPError, ValueError) as e:
        logger.error("Failed to scrape related searches: %s", e)
        return []


def generate_contextual_suggestions(query: str) -> List[str]:
    """Generate contextual suggestions based on query analysis."""
    query_lower = query.lower()

    # News/current events topics
    if any(
        word in query_lower
        for word in ["news", "latest", "today", "current", "break", "update"]
    ):
        base_concepts = (
            query_lower.replace("news", "")
            .replace("today", "")
            .replace("latest", "")
            .replace("current", "")
            .strip()
        )
        return [
            f"{base_concepts} international news",
            f"{base_concepts} breaking news",
            f"{base_concepts} live updates",
            f"{base_concepts} background",
            f"{base_concepts} timeline",
            f"{base_concepts} analysis",
            f"what happened to {base_concepts}",
            f"{base_concepts} developments",
            f"{base_concepts} latest developments",
            f"{base_concepts} recent news",
        ]

    # Technology topics
    if any(
        word in query_lower for word in ["ai", "technology", "software", "programming"]
    ):
        return [
            f"{query_lower} tutorial",
            f"{query_lower} documentation",
            f"{query_lower} best practices",
            f"{query_lower} comparison",
            f"{query_lower} alternatives",
            f"{query_lower} examples",
            f"{query_lower} implementation",
            f"{query_lower} guide",
            f"how to {query_lower}",
            f"{query_lower} vs",
        ]

    # General scientific/academic topics
    if any(word in query_lower for word in ["research", "study", "analysis", "theory"]):
        return [
            f"{query_lower} methodology",
            f"{query_lower} findings",
            f"{query_lower} implications",
            f"{query_lower} limitations",
            f"{query_lower} applications",
            f"{query_lower} future research",
            f"{query_lower} literature review",
            f"{query_lower} data",
            f"{query_lower} conclusions",
            f"{query_lower} summary",
        ]

    # General contextual suggestions
    return [
        f"{query_lower} meaning",
        f"{query_lower} definition",
        f"{query_lower} examples",
        f"{query_lower} benefits",
        f"{query_lower} problems",
        f"{query_lower} alternatives",
        f"{query_lower} guide",
        f"how to {query_lower}",
        f"what is {query_lower}",
        f"{query_lower} vs",
    ]


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

        Returns a list of search results with titles, URLs, descriptions, and domains.
        """
        logger.info("Searching for: '%s' (max %d results)", query, max_results)

        try:
            # Get HTTP client from context
            http_client = None
            close_client = False

            # Try to get HTTP client from lifespan context
            if (
                hasattr(ctx, "lifespan_context")
                and ctx.lifespan_context
                and "http_client" in ctx.lifespan_context
            ):
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
                        "domain": result.domain,
                    }
                    for result in results
                ]

                return {
                    "query": query,
                    "results": search_results,
                    "total_results": len(search_results),
                    "status": "success",
                }

            finally:
                if close_client:
                    await http_client.aclose()

        except (httpx.RequestError, httpx.HTTPError, ValueError) as e:
            logger.error("Search failed: %s", e)
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "status": "error",
                "error": str(e),
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
        logger.info("Fetching content from: %s", url)

        try:
            # Get HTTP client from context
            http_client = getattr(ctx, "http_client", None)
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
                content_selectors = [
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

                for selector in content_selectors:
                    main_content = soup.select_one(selector)
                    if main_content:
                        content_text = main_content.get_text().strip()
                        break

                # If no content found, get all paragraphs
                if not content_text:
                    paragraphs = soup.find_all("p")[:5]  # First 5 paragraphs
                    content_text = "\n\n".join(p.get_text().strip() for p in paragraphs)

                # Clean up content (first 500 chars for preview)
                content_preview = (
                    content_text[:500] + "..."
                    if len(content_text) > 500
                    else content_text
                )

                return {
                    "url": url,
                    "title": title,
                    "description": description,
                    "content": content_text,
                    "content_preview": content_preview,
                    "domain": extract_domain(url),
                    "status": "success",
                }

            finally:
                if close_client:
                    await http_client.aclose()

        except Exception as e:
            logger.error("Failed to fetch content from %s: %s", url, e)
            return {
                "url": url,
                "title": "",
                "description": "",
                "content": "",
                "content_preview": f"Error: {str(e)}",
                "domain": extract_domain(url),
                "status": "error",
                "error": str(e),
            }

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
        Suggest related search queries based on the original query.
        """
        logger.info(
            "Getting related searches for: '%s' (max %d suggestions)",
            query,
            max_suggestions,
        )

        try:
            # Get HTTP client from context
            http_client = None
            close_client = False

            if (
                hasattr(ctx, "lifespan_context")
                and ctx.lifespan_context
                and "http_client" in ctx.lifespan_context
            ):
                logger.info("Using HTTP client from lifespan context")
                http_client = ctx.lifespan_context["http_client"]
            else:
                logger.info("Creating new HTTP client")
                http_client = httpx.AsyncClient(timeout=10.0)
                close_client = True

            try:
                # Try to get actual related searches from DuckDuckGo HTML
                suggestions = await get_real_related_searches(query, http_client)
                if suggestions:
                    return {
                        "original_query": query,
                        "related_searches": suggestions[:max_suggestions],
                        "count": len(suggestions[:max_suggestions]),
                        "status": "success",
                    }
            finally:
                if close_client and http_client:
                    await http_client.aclose()

        except Exception as e:
            logger.error("Failed to get real related searches: %s", e)

        # Fallback: Generate contextual suggestions based on topic analysis
        contextual_suggestions = generate_contextual_suggestions(query)

        return {
            "original_query": query,
            "related_searches": contextual_suggestions[:max_suggestions],
            "count": len(contextual_suggestions[:max_suggestions]),
            "status": "contextual",  # Indicate these are contextual not scraped
        }
