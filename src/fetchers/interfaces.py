"""Optional fetcher interfaces (Interface Segregation Principle).

BaseFetcher only has what ALL fetchers need. Sources with extra needs
combine it with one of these interfaces, e.g.:

    class TwitterFetcher(BaseFetcher, AuthenticatedFetcher):
        async def authenticate(self) -> bool: ...
        async def fetch_articles(self) -> List[Article]: ...
        def get_source_name(self) -> str: ...
"""

from abc import ABC, abstractmethod
from typing import List

from src.models.article import Article


class AuthenticatedFetcher(ABC):
    """Interface for fetchers that require authentication."""
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the source.
        
        Returns:
            True if authentication successful
        """
        pass


class PaginatedFetcher(ABC):
    """Interface for fetchers that support pagination."""
    
    @abstractmethod
    async def fetch_page(self, page: int) -> List[Article]:
        """
        Fetch specific page of results.
        
        Args:
            page: Page number (1-indexed)
            
        Returns:
            Articles from that page
        """
        pass
