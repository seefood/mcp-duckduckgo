"""
MCP prompt definitions for the DuckDuckGo search plugin.
"""

from pydantic import Field

from .server import mcp

@mcp.prompt()  # noqa: F401 # pragma: no cover
def search_assistant(topic: str = Field(..., description="The topic to search for")) -> str:  # vulture: ignore
    """
    Creates a prompt to help formulate an effective search query for the given topic.
    """
    return f"""
    I need to search for information about {topic}.
    
    Please help me formulate an effective search query that will:
    1. Be specific and focused
    2. Use relevant keywords
    3. Avoid unnecessary words
    4. Be under 400 characters
    
    Then, use the duckduckgo_web_search tool with this query to find the most relevant information.
    """ 