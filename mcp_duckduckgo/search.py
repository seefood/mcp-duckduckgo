"""
Proper DuckDuckGo search implementation for MCP.
"""

import logging
import urllib.parse
from dataclasses import dataclass
from typing import List

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    description: str
    domain: str = ""


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


async def search_duckduckgo_instant(
    query: str, http_client: httpx.AsyncClient
) -> List[SearchResult]:
    """Search using DuckDuckGo Instant Answer API."""
    try:
        # Use DuckDuckGo's Instant Answer API
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }

        response = await http_client.get(url, params=params, timeout=10)  # type: ignore[arg-type]
        response.raise_for_status()

        data = response.json()
        results = []

        # Get the abstract/summary
        if data.get("Abstract"):
            results.append(
                SearchResult(
                    title=data.get("Heading", query),
                    url=data.get("AbstractURL", ""),
                    description=data.get("Abstract", ""),
                )
            )

        # Get related topics
        for topic in data.get("RelatedTopics", []):
            if isinstance(topic, dict) and topic.get("Text") and topic.get("FirstURL"):
                results.append(
                    SearchResult(
                        title=topic.get("Text", ""),
                        url=topic.get("FirstURL", ""),
                        description=topic.get("Text", ""),
                    )
                )

        return results

    except Exception as e:
        logger.error(f"DuckDuckGo instant search failed: {e}")
        return []


async def search_duckduckgo_html(
    query: str, http_client: httpx.AsyncClient, count: int = 10
) -> List[SearchResult]:
    """Search using DuckDuckGo HTML interface as fallback."""
    try:
        # Use DuckDuckGo's HTML interface
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        response = await http_client.get(
            url, params=params, headers=headers, timeout=15
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        results = []

        # DuckDuckGo result selectors (multiple attempts for robustness)
        result_selectors = [
            "div.result",
            'div[class*="result"]',
            ".result",
            ".web-result",
            ".result_body",
        ]

        result_divs: list = []
        for selector in result_selectors:
            result_divs = soup.select(selector)
            if result_divs:
                logger.info(
                    f"Found {len(result_divs)} results with selector: {selector}"
                )
                break

        if not result_divs:
            logger.warning("No result divs found, trying fallback method")
            # Fallback: look for links that might be search results
            all_links = soup.find_all("a", href=True)
            for link in all_links[:count]:
                href = link.get("href", "")
                text = link.get_text().strip()
                if href and text and not href.startswith("#"):
                    results.append(
                        SearchResult(
                            title=text,
                            url=href,
                            description="",
                            domain=extract_domain(href),
                        )
                    )
            return results[:count]

        for i, div in enumerate(result_divs[:count]):
            try:
                # Multiple title/link selectors
                title_selectors = [
                    "a.result__a",
                    'a[class*="result"]',
                    ".result__title a",
                    "h3 a",
                    "a",
                ]

                title_link = None
                for selector in title_selectors:
                    title_link = div.select_one(selector)
                    if title_link:
                        break

                if not title_link:
                    continue

                title = title_link.get_text().strip()
                url = title_link.get("href", "")

                # Extract snippet/description
                snippet_selectors = [
                    "a.result__snippet",
                    ".result__snippet",
                    ".result__body",
                    ".snippet",
                    "p",
                ]

                description = ""
                for selector in snippet_selectors:
                    snippet_elem = div.select_one(selector)
                    if snippet_elem:
                        description = snippet_elem.get_text().strip()
                        break

                # Clean up URL (remove DuckDuckGo redirect)
                if url.startswith("/l/?uddg="):
                    try:
                        querystr = urllib.parse.parse_qs(
                            urllib.parse.urlparse(url).query
                        )
                        if "uddg" in querystr:
                            url = querystr["uddg"][0]
                    except Exception:
                        pass

                # Skip if no valid URL or title
                if not url or not title:
                    continue

                results.append(
                    SearchResult(
                        title=title,
                        url=url,
                        description=description,
                        domain=extract_domain(url),
                    )
                )

            except Exception as e:
                logger.warning(f"Failed to parse result {i}: {e}")
                continue

        logger.info(f"Successfully parsed {len(results)} HTML results")
        return results

    except Exception as e:
        logger.error(f"DuckDuckGo HTML search failed: {e}")
        return []


async def search_web(
    query: str, http_client: httpx.AsyncClient, count: int = 10
) -> List[SearchResult]:
    """Main search function that tries multiple methods."""
    logger.info(f"Searching for: '{query}' (max {count} results)")

    # Try instant answers first
    instant_results = await search_duckduckgo_instant(query, http_client)
    logger.info(f"Instant answers found {len(instant_results)} results")

    # Always try HTML search for more comprehensive results
    html_results = await search_duckduckgo_html(query, http_client, count)
    logger.info(f"HTML search found {len(html_results)} results")

    # Combine and deduplicate
    all_results = instant_results + html_results

    # Remove duplicates based on URL
    seen_urls = set()
    unique_results = []
    for result in all_results:
        if result.url and result.url not in seen_urls and result.url.startswith("http"):
            seen_urls.add(result.url)
            unique_results.append(result)
            if len(unique_results) >= count:
                break

    logger.info(f"Returning {len(unique_results)} unique valid results")
    return unique_results
