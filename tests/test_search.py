"""Unit tests for search functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from mcp_duckduckgo.search import (
    SearchResult,
    extract_domain,
    search_duckduckgo_instant,
    search_web,
)


class TestExtractDomain:
    """Tests for extract_domain function."""

    def test_extract_simple_domain(self):
        """Test extracting domain from simple URL."""
        assert extract_domain("https://example.com/path") == "example.com"

    def test_extract_domain_with_subdomain(self):
        """Test extracting domain with subdomain."""
        assert extract_domain("https://www.example.com/path") == "www.example.com"

    def test_extract_domain_with_port(self):
        """Test extracting domain with port."""
        assert extract_domain("https://example.com:8080/path") == "example.com:8080"

    def test_extract_domain_lowercase(self):
        """Test that domain is converted to lowercase."""
        assert extract_domain("https://EXAMPLE.COM/path") == "example.com"

    def test_malformed_url_returns_empty(self):
        """Test that malformed URLs return empty string."""
        assert extract_domain("not a url") == ""

    def test_empty_url_returns_empty(self):
        """Test that empty URL returns empty string."""
        assert extract_domain("") == ""


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_create_search_result(self):
        """Test creating SearchResult."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            description="Test description",
            domain="example.com",
        )

        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.description == "Test description"
        assert result.domain == "example.com"

    def test_search_result_default_domain(self):
        """Test SearchResult with default domain."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            description="Test description",
        )

        assert result.domain == ""


class TestSearchDuckduckgoInstant:
    """Tests for search_duckduckgo_instant function."""

    @pytest.mark.asyncio
    async def test_successful_instant_search(self):
        """Test successful instant answer API search."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Abstract": "Python is a programming language",
            "AbstractURL": "https://www.python.org",
            "Heading": "Python",
            "RelatedTopics": [
                {
                    "Text": "Python Tutorial",
                    "FirstURL": "https://www.python.org/tutorial",
                }
            ],
        }
        mock_client.get.return_value = mock_response

        results = await search_duckduckgo_instant("python", mock_client)

        assert len(results) == 2
        assert results[0].title == "Python"
        assert results[0].url == "https://www.python.org"
        assert results[1].title == "Python Tutorial"

    @pytest.mark.asyncio
    async def test_instant_search_no_results(self):
        """Test instant search with no results."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_client.get.return_value = mock_response

        results = await search_duckduckgo_instant("python", mock_client)

        assert results == []

    @pytest.mark.asyncio
    async def test_instant_search_http_error(self):
        """Test instant search with HTTP error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("Connection error")

        results = await search_duckduckgo_instant("python", mock_client)

        assert results == []


class TestSearchWeb:
    """Tests for main search_web function."""

    @pytest.mark.asyncio
    async def test_combines_instant_and_html_results(self):
        """Test that search_web combines instant and HTML results."""
        with (
            patch("mcp_duckduckgo.search.search_duckduckgo_instant") as mock_instant,
            patch("mcp_duckduckgo.search.search_duckduckgo_html") as mock_html,
        ):
            mock_instant.return_value = [
                SearchResult(
                    title="Result 1",
                    url="https://example.com/1",
                    description="Description 1",
                )
            ]
            mock_html.return_value = [
                SearchResult(
                    title="Result 2",
                    url="https://example.com/2",
                    description="Description 2",
                )
            ]

            mock_client = AsyncMock()
            results = await search_web("test", mock_client, 10)

            assert len(results) == 2
            assert results[0].url == "https://example.com/1"
            assert results[1].url == "https://example.com/2"

    @pytest.mark.asyncio
    async def test_deduplicates_results(self):
        """Test that search_web deduplicates results by URL."""
        with (
            patch("mcp_duckduckgo.search.search_duckduckgo_instant") as mock_instant,
            patch("mcp_duckduckgo.search.search_duckduckgo_html") as mock_html,
        ):
            duplicate_url = "https://example.com/1"
            mock_instant.return_value = [
                SearchResult(title="Result 1", url=duplicate_url, description="Desc 1")
            ]
            mock_html.return_value = [
                SearchResult(
                    title="Result 1 Again", url=duplicate_url, description="Desc 2"
                )
            ]

            mock_client = AsyncMock()
            results = await search_web("test", mock_client, 10)

            assert len(results) == 1
            assert results[0].url == duplicate_url

    @pytest.mark.asyncio
    async def test_filters_invalid_urls(self):
        """Test that search_web filters out invalid URLs."""
        with (
            patch("mcp_duckduckgo.search.search_duckduckgo_instant") as mock_instant,
            patch("mcp_duckduckgo.search.search_duckduckgo_html") as mock_html,
        ):
            mock_instant.return_value = []
            mock_html.return_value = [
                SearchResult(
                    title="Valid", url="https://example.com", description="Desc"
                ),
                SearchResult(
                    title="Invalid", url="javascript:alert(1)", description="Desc"
                ),
                SearchResult(title="Empty", url="", description="Desc"),
            ]

            mock_client = AsyncMock()
            results = await search_web("test", mock_client, 10)

            assert len(results) == 1
            assert results[0].url == "https://example.com"

    @pytest.mark.asyncio
    async def test_respects_count_limit(self):
        """Test that search_web respects the count limit."""
        with (
            patch("mcp_duckduckgo.search.search_duckduckgo_instant") as mock_instant,
            patch("mcp_duckduckgo.search.search_duckduckgo_html") as mock_html,
        ):
            # Return more results than requested
            mock_instant.return_value = []
            mock_html.return_value = [
                SearchResult(
                    title=f"Result {i}",
                    url=f"https://example.com/{i}",
                    description=f"Description {i}",
                )
                for i in range(20)
            ]

            mock_client = AsyncMock()
            results = await search_web("test", mock_client, count=5)

            assert len(results) == 5
