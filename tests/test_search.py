"""
Tests for the DuckDuckGo search functionality.
"""

import pytest
import httpx
from bs4 import BeautifulSoup
from unittest.mock import AsyncMock, patch, MagicMock

from mcp_duckduckgo.search import duckduckgo_search, extract_domain


class TestExtractDomain:
    """Tests for the extract_domain function."""

    def test_extract_domain_valid_url(self):
        """Test that extract_domain works with valid URLs."""
        url = "https://example.com/page?query=test"
        domain = extract_domain(url)
        assert domain == "example.com"

    def test_extract_domain_with_subdomain(self):
        """Test extract_domain with subdomains."""
        url = "https://blog.example.com/article"
        domain = extract_domain(url)
        assert domain == "blog.example.com"

    def test_extract_domain_invalid_url(self):
        """Test extract_domain with invalid URLs."""
        url = "not a url"
        domain = extract_domain(url)
        assert domain == ""

    def test_extract_domain_empty_string(self):
        """Test extract_domain with empty string."""
        url = ""
        domain = extract_domain(url)
        assert domain == ""


class TestDuckDuckGoSearch:
    """Tests for the duckduckgo_search function."""

    @pytest.mark.asyncio
    async def test_basic_search(self, mock_context, mock_http_client, sample_search_params):
        """Test a basic search with mocked response."""
        # Set up the mock client in the context
        mock_context.lifespan_context['http_client'] = mock_http_client

        # Run the search function
        result = await duckduckgo_search(sample_search_params, mock_context)

        # Verify the result structure
        assert 'results' in result
        assert 'total_results' in result
        assert isinstance(result['results'], list)
        assert isinstance(result['total_results'], int)

        # Verify that the HTTP client was called correctly
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert call_args[0][0] == "https://lite.duckduckgo.com/lite/"
        assert 'data' in call_args[1]
        assert call_args[1]['data']['q'] == sample_search_params['query']

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, mock_context, mock_http_client):
        """Test search with pagination parameters."""
        # Set up the mock client in the context
        mock_context.lifespan_context['http_client'] = mock_http_client

        # Set up the search parameters with pagination
        search_params = {
            "query": "test query",
            "count": 5,
            "offset": 10,
            "page": 3
        }

        # Run the search function
        await duckduckgo_search(search_params, mock_context)

        # Verify that the HTTP client was called with the right offset
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert call_args[1]['data']['s'] == 10  # Check the offset was passed

    @pytest.mark.asyncio
    async def test_search_without_context_client(self, mock_context):
        """Test search without a client in the context."""
        # Set up context without http_client
        mock_context.lifespan_context = {}

        # Set up a mock for httpx.AsyncClient to be used in the function
        mock_client = AsyncMock()
        mock_client.post.return_value = MagicMock(
            text="""
            <html>
            <body>
                <table>
                    <tr class="result-link">
                        <td>
                            <a href="https://example.com/page1">Example Page 1</a>
                        </td>
                    </tr>
                    <tr class="result-snippet">
                        <td>This is a description for Example Page 1</td>
                    </tr>
                </table>
            </body>
            </html>
            """,
            status_code=200,
            raise_for_status=MagicMock()
        )

        # Mock the AsyncClient constructor
        with patch('httpx.AsyncClient', return_value=mock_client):
            # Run the search function
            search_params = {"query": "test query"}
            result = await duckduckgo_search(search_params, mock_context)

            # Verify the client was created and used
            mock_client.post.assert_called_once()
            mock_client.aclose.assert_called_once()  # Check client was closed

            # Verify results
            assert 'results' in result
            assert len(result['results']) > 0

    @pytest.mark.asyncio
    async def test_search_with_no_results(self, mock_context, mock_http_client):
        """Test search with no results."""
        # Set up the mock client to return a response with no results
        empty_html = "<html><body><table></table></body></html>"
        mock_http_client.post.return_value = MagicMock(
            text=empty_html,
            status_code=200,
            raise_for_status=MagicMock()
        )
        mock_context.lifespan_context['http_client'] = mock_http_client

        # Run the search function
        search_params = {"query": "nonexistent query"}
        result = await duckduckgo_search(search_params, mock_context)

        # Verify empty results
        assert 'results' in result
        assert len(result['results']) == 0

    @pytest.mark.asyncio
    async def test_search_with_http_error(self, mock_context, mock_http_client):
        """Test search with HTTP error."""
        # Set up the mock client to raise an HTTP error
        mock_http_client.post.return_value = MagicMock(
            status_code=404,
            raise_for_status=MagicMock(side_effect=httpx.HTTPStatusError(
                message="404 Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404)
            ))
        )
        mock_context.lifespan_context['http_client'] = mock_http_client

        # Run the search function and expect an exception
        search_params = {"query": "test query"}
        with pytest.raises(ValueError) as excinfo:
            await duckduckgo_search(search_params, mock_context)
        
        assert "HTTP error" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_search_with_request_error(self, mock_context, mock_http_client):
        """Test search with request error."""
        # Set up the mock client to raise a request error
        mock_http_client.post.side_effect = httpx.RequestError("Connection error", request=MagicMock())
        mock_context.lifespan_context['http_client'] = mock_http_client

        # Run the search function and expect an exception
        search_params = {"query": "test query"}
        with pytest.raises(ValueError) as excinfo:
            await duckduckgo_search(search_params, mock_context)
        
        assert "Request error" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_search_with_fallback_parsing(self, mock_context, mock_http_client):
        """Test search with fallback HTML parsing approach."""
        # HTML without the expected structure but with links
        fallback_html = """
        <html>
        <body>
            <div>
                <a href="https://example.com/fallback">Fallback Result</a>
                <p>This is a fallback description</p>
            </div>
        </body>
        </html>
        """
        mock_http_client.post.return_value = MagicMock(
            text=fallback_html,
            status_code=200,
            raise_for_status=MagicMock()
        )
        mock_context.lifespan_context['http_client'] = mock_http_client

        # Run the search function
        search_params = {"query": "test query"}
        result = await duckduckgo_search(search_params, mock_context)

        # Verify results using fallback mechanism
        assert 'results' in result
        assert len(result['results']) > 0
        # The fallback should have found the link
        found_url = False
        for item in result['results']:
            if item['url'] == 'https://example.com/fallback':
                found_url = True
                break
        assert found_url, "Fallback parsing didn't find the expected URL"

    @pytest.mark.asyncio
    async def test_missing_query_parameter(self, mock_context):
        """Test that an error is raised when query parameter is missing."""
        # Run the search function without a query
        search_params = {}
        with pytest.raises(ValueError) as excinfo:
            await duckduckgo_search(search_params, mock_context)
        
        assert "Query parameter is required" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_progress_reporting(self, mock_context, mock_http_client, sample_search_params):
        """Test that progress is reported correctly."""
        # Set up the context with report_progress method
        mock_context.report_progress = AsyncMock()
        mock_context.lifespan_context['http_client'] = mock_http_client

        # Run the search function
        await duckduckgo_search(sample_search_params, mock_context)

        # Verify that report_progress was called at least once
        assert mock_context.report_progress.called

    @pytest.mark.asyncio
    async def test_info_reporting(self, mock_context, mock_http_client, sample_search_params):
        """Test that info is reported correctly."""
        # Set up the context with info method
        mock_context.info = AsyncMock()
        mock_context.lifespan_context['http_client'] = mock_http_client

        # Run the search function
        await duckduckgo_search(sample_search_params, mock_context)

        # Verify that info was called at least once
        assert mock_context.info.called 