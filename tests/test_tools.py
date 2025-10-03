"""Unit tests for MCP tools."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from mcp_duckduckgo.tools import (
    get_autocomplete_suggestions,
    get_http_client_from_context,
    validate_url,
)


class TestValidateUrl:
    """Tests for validate_url function."""

    def test_valid_http_url(self):
        """Test that http URLs are valid."""
        assert validate_url("http://example.com") is True

    def test_valid_https_url(self):
        """Test that https URLs are valid."""
        assert validate_url("https://example.com") is True

    def test_invalid_file_url(self):
        """Test that file:// URLs are rejected."""
        assert validate_url("file:///etc/passwd") is False

    def test_invalid_javascript_url(self):
        """Test that javascript: URLs are rejected."""
        assert validate_url("javascript:alert(1)") is False

    def test_invalid_data_url(self):
        """Test that data: URLs are rejected."""
        assert validate_url("data:text/html,<script>alert(1)</script>") is False

    def test_invalid_ftp_url(self):
        """Test that ftp:// URLs are rejected."""
        assert validate_url("ftp://example.com") is False

    def test_malformed_url(self):
        """Test that malformed URLs are rejected."""
        assert validate_url("not a url") is False

    def test_empty_url(self):
        """Test that empty URLs are rejected."""
        assert validate_url("") is False


class TestGetHttpClientFromContext:
    """Tests for get_http_client_from_context function."""

    def test_gets_client_from_lifespan_context(self):
        """Test retrieving HTTP client from lifespan context."""
        mock_client = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.lifespan_context = {"http_client": mock_client}

        client, should_close = get_http_client_from_context(mock_ctx)

        assert client == mock_client
        assert should_close is False

    def test_creates_new_client_when_missing(self):
        """Test creating new HTTP client when not in context."""
        mock_ctx = MagicMock()
        mock_ctx.lifespan_context = {}

        client, should_close = get_http_client_from_context(mock_ctx)

        assert isinstance(client, httpx.AsyncClient)
        assert should_close is True

    def test_creates_new_client_when_no_lifespan_context(self):
        """Test creating new HTTP client when lifespan_context doesn't exist."""
        mock_ctx = MagicMock(spec=[])  # No lifespan_context attribute

        client, should_close = get_http_client_from_context(mock_ctx)

        assert isinstance(client, httpx.AsyncClient)
        assert should_close is True


class TestGetAutocompleteSuggestions:
    """Tests for get_autocomplete_suggestions function."""

    @pytest.mark.asyncio
    async def test_successful_autocomplete(self):
        """Test successful autocomplete API call."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            "python",
            ["python", "python programming", "python tutorial"],
        ]
        mock_client.get.return_value = mock_response

        result = await get_autocomplete_suggestions("python", mock_client)

        assert result == ["python", "python programming", "python tutorial"]
        mock_client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_suggestions(self):
        """Test handling of empty suggestions."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = ["python", []]
        mock_client.get.return_value = mock_response

        result = await get_autocomplete_suggestions("python", mock_client)

        assert result == []

    @pytest.mark.asyncio
    async def test_malformed_response(self):
        """Test handling of malformed API response."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = ["python"]  # Missing suggestions array
        mock_client.get.return_value = mock_response

        result = await get_autocomplete_suggestions("python", mock_client)

        assert result == []

    @pytest.mark.asyncio
    async def test_http_error(self):
        """Test handling of HTTP errors."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.HTTPError("Connection error")

        result = await get_autocomplete_suggestions("python", mock_client)

        assert result == []

    @pytest.mark.asyncio
    async def test_request_error(self):
        """Test handling of request errors."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.RequestError("Timeout")

        result = await get_autocomplete_suggestions("python", mock_client)

        assert result == []

    @pytest.mark.asyncio
    async def test_json_decode_error(self):
        """Test handling of JSON decode errors."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_client.get.return_value = mock_response

        result = await get_autocomplete_suggestions("python", mock_client)

        assert result == []
