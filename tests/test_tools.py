"""
Tests for the DuckDuckGo search tools.

These tests verify that the MCP tools for DuckDuckGo search work correctly.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

# Import the tools module containing the MCP tools
from mcp_duckduckgo.tools import duckduckgo_web_search, duckduckgo_get_details, duckduckgo_related_searches
from mcp_duckduckgo.models import SearchResponse, DetailedResult


@pytest.mark.asyncio
async def test_duckduckgo_web_search(mock_context, mock_search_function):
    """Test the duckduckgo_web_search tool."""
    # Mock the search function
    with patch('mcp_duckduckgo.tools.duckduckgo_search', mock_search_function):
        # Call the tool
        result = await duckduckgo_web_search(
            query="test query",
            count=5,
            page=1,
            site=None,
            time_period=None,
            ctx=mock_context
        )
        
        # Verify the result
        assert isinstance(result, SearchResponse)
        assert len(result.results) == 2  # Based on the sample data in conftest.py
        assert result.total_results == 2
        assert result.page == 1
        
        # Check the first result
        first_result = result.results[0]
        assert first_result.title == "Example Page 1"
        assert first_result.url == "https://example.com/page1"
        assert first_result.description == "This is a description for Example Page 1"
        # Domain is included in result dict but not as a property in SearchResult model
        # assert first_result.domain == "example.com"


@pytest.mark.asyncio
async def test_duckduckgo_web_search_with_site_filter(mock_context, mock_search_function):
    """Test the duckduckgo_web_search tool with site filter."""
    # Mock the search function to capture params
    mock_search_params = None
    
    async def capture_params(params, ctx):
        nonlocal mock_search_params
        mock_search_params = params
        return await mock_search_function(params, ctx)
    
    with patch('mcp_duckduckgo.tools.duckduckgo_search', capture_params):
        # Call the tool with site filter
        await duckduckgo_web_search(
            query="test query",
            count=5,
            page=1,
            site="example.com",
            time_period=None,
            ctx=mock_context
        )
        
        # Verify that site filter was correctly applied to the query
        assert mock_search_params is not None
        assert mock_search_params["query"] == "test query site:example.com"


@pytest.mark.asyncio
async def test_duckduckgo_web_search_with_time_filter(mock_context, mock_search_function):
    """Test the duckduckgo_web_search tool with time filter."""
    # Mock the search function to capture params
    mock_search_params = None
    
    async def capture_params(params, ctx):
        nonlocal mock_search_params
        mock_search_params = params
        return await mock_search_function(params, ctx)
    
    with patch('mcp_duckduckgo.tools.duckduckgo_search', capture_params):
        # Call the tool with time filter
        await duckduckgo_web_search(
            query="test query",
            count=5,
            page=1,
            site=None,
            time_period="week",
            ctx=mock_context
        )
        
        # Verify that time filter was correctly applied
        assert mock_search_params is not None
        assert "date:w" in mock_search_params["query"]


@pytest.mark.asyncio
async def test_duckduckgo_web_search_pagination(mock_context, mock_search_function):
    """Test the duckduckgo_web_search tool with pagination."""
    # Mock the search function to capture params
    mock_search_params = None
    
    async def capture_params(params, ctx):
        nonlocal mock_search_params
        mock_search_params = params
        return await mock_search_function(params, ctx)
    
    with patch('mcp_duckduckgo.tools.duckduckgo_search', capture_params):
        # Call the tool with pagination
        await duckduckgo_web_search(
            query="test query",
            count=5,
            page=3,  # Page 3
            site=None,
            time_period=None,
            ctx=mock_context
        )
        
        # Verify that pagination was correctly applied
        assert mock_search_params is not None
        assert mock_search_params["offset"] == 10  # (page-1) * count


@pytest.mark.asyncio
async def test_duckduckgo_web_search_error_handling(mock_context):
    """Test error handling in the duckduckgo_web_search tool."""
    # Mock the search function to raise an exception
    async def mock_error(*args, **kwargs):
        raise ValueError("Test error")
    
    # Mock the error reporting method
    mock_context.error = AsyncMock()
    
    with patch('mcp_duckduckgo.tools.duckduckgo_search', mock_error):
        # In the actual implementation, errors are caught and an empty result is returned
        # with error logging, not raising the exception
        result = await duckduckgo_web_search(
            query="test query",
            count=5,
            page=1,
            site=None,
            time_period=None,
            ctx=mock_context
        )
        
        # Verify error was reported
        assert mock_context.error.called
        # Check that we got a fallback empty result
        assert isinstance(result, SearchResponse)
        assert len(result.results) == 0


@pytest.mark.asyncio
async def test_duckduckgo_get_details(mock_context):
    """Test the duckduckgo_get_details tool."""
    # The implementation doesn't actually make HTTP requests, it just creates a
    # placeholder DetailedResult with the domain extracted from the URL
    
    # Call the tool
    url = "https://example.com/page"
    result = await duckduckgo_get_details(
        url=url,
        ctx=mock_context
    )
    
    # Verify the result
    assert isinstance(result, DetailedResult)
    assert result.url == url
    assert result.domain == "example.com"
    assert result.content_snippet == "Content not available"  # Default placeholder


@pytest.mark.asyncio
async def test_duckduckgo_related_searches(mock_context):
    """Test the duckduckgo_related_searches tool."""
    # The implementation doesn't make HTTP requests, it generates placeholder related searches
    
    # Call the tool
    query = "test query"
    count = 5
    result = await duckduckgo_related_searches(
        query=query,
        count=count,
        ctx=mock_context
    )
    
    # Verify the result
    assert isinstance(result, list)
    assert len(result) == count
    
    # Check that the related searches are based on the query
    for related_search in result:
        assert query in related_search.lower()


@pytest.mark.asyncio
async def test_duckduckgo_related_searches_count(mock_context):
    """Test the duckduckgo_related_searches tool with different counts."""
    # Test with different counts
    for count in [1, 3, 7, 10]:
        result = await duckduckgo_related_searches(
            query="test query",
            count=count,
            ctx=mock_context
        )
        
        # Verify the count
        assert len(result) == count 