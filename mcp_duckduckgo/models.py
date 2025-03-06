"""
Data models for the DuckDuckGo search plugin.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field

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

class LinkedContent(BaseModel):
    """Content from a linked page discovered through spidering."""
    
    url: str
    title: str
    content_snippet: Optional[str] = None
    relation: str = "linked"  # Relationship to original page (e.g., "linked", "child", "parent")

class DetailedResult(BaseModel):
    """Detailed information about a search result."""
    
    title: str
    url: str
    description: str
    published_date: Optional[str] = None
    content_snippet: Optional[str] = None  # A snippet of the content
    domain: Optional[str] = None  # The domain of the result
    is_official: Optional[bool] = None  # Whether this is an official source
    
    # Enhanced metadata
    author: Optional[str] = None  # Author of the content
    keywords: Optional[List[str]] = None  # Keywords or tags
    main_image: Optional[str] = None  # URL of the main image
    
    # Social metadata
    social_links: Optional[Dict[str, str]] = None  # Links to social profiles
    
    # Spidering results
    related_links: Optional[List[str]] = None  # URLs of related links found on the page
    linked_content: Optional[List[LinkedContent]] = None  # Content from linked pages
    
    # Content structure
    headings: Optional[List[str]] = None  # Main headings on the page 