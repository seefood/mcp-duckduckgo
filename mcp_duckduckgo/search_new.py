"""
Proper DuckDuckGo search implementation for MCP.
"""
import logging
import httpx
import json
import urllib.parse
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from dataclasses import dataclass

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
    except:
        return ""

async def search_duckduckgo_instant(query: str, http_client: httpx.AsyncClient) -> List[SearchResult]:
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

        response = await http_client.get(url, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        results = []

        # Get the abstract/summary
        if data.get("Abstract"):
            results.append(SearchResult(
                title=data.get("Heading", query),
                url=data.get("AbstractURL", ""),
                description=data.get("Abstract", "")
            ))

        # Get related topics
        for topic in data.get("RelatedTopics", []):
            if isinstance(topic, dict) and topic.get("Text") and topic.get("FirstURL"):
                results.append(SearchResult(
                    title=topic.get("Text", ""),
                    url=topic.get("FirstURL", ""),
                    description=topic.get("Text", "")
                ))

        return results

    except Exception as e:
        logger.error(f"DuckDuckGo instant search failed: {e}")
        return []

async def search_duckduckgo_html(query: str, http_client: httpx.AsyncClient, count: int = 10) -> List[SearchResult]:
    """Search using DuckDuckGo HTML interface as fallback."""
    try:
        # Use DuckDuckGo's HTML interface
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml, application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        response = await http_client.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []

        # Find DuckDuckGo search result blocks
        result_divs = soup.find_all('div', class_='result')

        for i, div in enumerate(result_divs[:count]):
            try:
                # Extract title and URL
                title_link = div.find('a', class_='result__a')
                if not title_link:
                    continue

                title = title_link.get_text().strip()
                url = title_link.get('href', '')

                # Extract snippet/description
                snippet_div = div.find('a', class_='result__snippet')
                description = snippet_div.get_text().strip() if snippet_div else ""

                # Clean up URL (remove DuckDuckGo redirect)
                if url.startswith('/l/?uddg='):
                    # This is a DuckDuckGo redirect, extract the actual URL
                    import urllib.parse as urlparse
                    querystr = urlparse.parse_qs(urlparse.urlparse(url).query)
                    if 'uddg' in querystr:
                        url = querystr['uddg'][0]

                results.append(SearchResult(
                    title=title,
                    url=url,
                    description=description,
                    domain=extract_domain(url)
                ))

            except Exception as e:
                logger.warning(f"Failed to parse result {i}: {e}")
                continue

        return results

    except Exception as e:
        logger.error(f"DuckDuckGo HTML search failed: {e}")
        return []

async def search_web(query: str, http_client: httpx.AsyncClient, count: int = 10) -> List[SearchResult]:
    """Main search function that tries multiple methods."""
    logger.info(f"Searching for: '{query}' (max {count} results)")

    # Try instant answers first
    results = await search_duckduckgo_instant(query, http_client)

    # If not enough results, try HTML search
    if len(results) < count:
        html_results = await search_duckduckgo_html(query, http_client, count - len(results))
        results.extend(html_results)

    # Remove duplicates based on URL
    seen_urls = set()
    unique_results = []
    for result in results:
        if result.url not in seen_urls and result.url:
            seen_urls.add(result.url)
            unique_results.append(result)
            if len(unique_results) >= count:
                break

    logger.info(f"Found {len(unique_results)} unique results")
    return unique_results[:count]
