"""
Data models for the DuckDuckGo search plugin.
"""

from typing import List, Optional
from pydantic import BaseModel

class SearchResult(BaseModel):
    """A single search result."""
    
    title: str
    url: str
    description: str
    published_date: Optional[str] = None  # Optional field, may be used in some results # noqa: F841 # pragma: no cover # vulture: ignore

class SearchResponse(BaseModel):
    """Response from DuckDuckGo search."""
    
    results: List[SearchResult]
    total_results: int
    page: int = 1  # Current page number
    total_pages: int = 1  # Total number of pages
    has_next: bool = False  # Whether there are more pages
    has_previous: bool = False  # Whether there are previous pages

class DetailedResult(BaseModel):
    """Detailed information about a search result."""
    
    title: str
    url: str
    description: str
    published_date: Optional[str] = None
    content_snippet: Optional[str] = None  # A snippet of the content
    domain: Optional[str] = None  # The domain of the result
    is_official: Optional[bool] = None  # Whether this is an official source 