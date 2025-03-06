"""Tests for the main module."""

import pytest
from fastapi.testclient import TestClient

from mcp_duckduckgo.main import create_app


@pytest.fixture
def client():
    """Create a test client for the application."""
    app = create_app()
    return TestClient(app)


def test_mcp_discover(client):
    """Test that the MCP discover endpoint returns the expected JSON."""
    response = client.get("/.well-known/mcp")
    assert response.status_code == 200
    data = response.json()
    
    # Check that the response contains expected fields
    assert "name" in data
    assert data["name"] == "mcp-duckduckgo"
    assert "version" in data
    assert "functions" in data
    
    # Check that the DuckDuckGo search function is present
    functions = {function["name"]: function for function in data["functions"]}
    assert "duckduckgo_web_search" in functions
    
    # Check function parameters
    search_function = functions["duckduckgo_web_search"]
    assert "parameters" in search_function
    
    parameters = search_function["parameters"]
    assert "properties" in parameters
    assert "query" in parameters["properties"]
    assert "required" in parameters
    assert "query" in parameters["required"]


def test_mcp_execute(client, monkeypatch):
    """Test that the MCP execute endpoint works correctly."""
    # Mock the duckduckgo_search function to avoid making real API calls
    
    async def mock_duckduckgo_search(_):
        """Mock implementation of duckduckgo_search."""
        return {
            "results": [
                {
                    "title": "Test Result",
                    "url": "https://example.com",
                    "description": "This is a test result",
                    "published_date": None
                }
            ],
            "total_results": 1
        }
    
    monkeypatch.setattr("mcp_duckduckgo.main.duckduckgo_search", mock_duckduckgo_search)
    
    # Test the execute endpoint
    response = client.post(
        "/mcp/execute",
        json={
            "function": "duckduckgo_web_search",
            "parameters": {
                "query": "test query"
            }
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["title"] == "Test Result"
    assert "total_results" in data
