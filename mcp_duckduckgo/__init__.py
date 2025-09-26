"""DuckDuckGo search plugin for Model Context Protocol."""

__version__ = "0.1.1"

from .models import SearchResult, SearchResponse
from .search import duckduckgo_search
from .server import mcp
from .tools import duckduckgo_web_search

__all__ = [
    "SearchResult",
    "SearchResponse",
    "duckduckgo_search",
    "duckduckgo_web_search",
    "mcp",
]
