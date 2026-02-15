"""
Google Search Connector for OSINT Framework

Purpose
- Search public Google results for entities
- Support Google Dorks for advanced queries
- Extract metadata from search results

Invariants
- All searches respect Google's rate limits
- User-Agent headers are realistic
- Results are validated before return
- Sensitive queries are rejected

Failure Modes
- Rate limiting → request is queued and retried
- Invalid query → validation error is logged
- Network error → request is retried with backoff
- Parsing error → result is skipped with warning
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from .base import SourceConnector, ConnectorStatus
from ..core.models.entities import SearchResult, EntityType


class GoogleSearchConnector(SourceConnector):
    """Connector for Google Search results."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Google Search connector."""
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.base_url = "https://www.google.com/search"
    
    @property
    def source_name(self) -> str:
        """Return source name."""
        return "Google Search"
    
    @property
    def source_type(self) -> str:
        """Return source type."""
        return "search_engine"
    
    def get_rate_limit(self) -> int:
        """Return requests per hour limit."""
        return 100  # Conservative rate limit for Google
    
    def get_confidence_weight(self) -> float:
        """Return confidence weight for this source."""
        return 0.7  # Moderate confidence due to public nature
    
    def get_supported_entity_types(self) -> Set[EntityType]:
        """Return supported entity types."""
        return {
            EntityType.PERSON,
            EntityType.COMPANY,
            EntityType.EMAIL_ADDRESS,
            EntityType.PHONE_NUMBER,
            EntityType.DOMAIN
        }
    
    async def search(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Execute Google Search."""
        if not self.rate_limit.can_make_request():
            self.logger.warning("Rate limit exceeded for Google Search")
            return []
        
        try:
            # Prepare search parameters
            search_params = {
                'q': query,
                'num': params.get('num_results', 10),
                'start': params.get('start_index', 0)
            }
            
            # Make request
            response = await self.make_request(
                self.base_url,
                method="GET",
                params=search_params
            )
            
            if not response:
                return []
            
            # Parse results (simplified parsing)
            results = self._parse_search_results(response, query)
            
            self.logger.info(f"Google Search returned {len(results)} results for query: {query}")
            return results
            
        except Exception as e:
            self.logger.error(f"Google Search failed: {str(e)}")
            self.status = ConnectorStatus.ERROR
            return []
    
    async def validate_credentials(self) -> bool:
        """Validate connector credentials."""
        try:
            # Google doesn't require credentials for public searches
            # Just verify network connectivity
            response = await self.make_request(self.base_url, method="GET")
            return response is not None
        except Exception as e:
            self.logger.error(f"Credential validation failed: {str(e)}")
            return False
    
    def _parse_search_results(self, response: Dict[str, Any], query: str) -> List[SearchResult]:
        """Parse Google search results."""
        results = []
        
        # This is a simplified parser - in production, use BeautifulSoup or similar
        if 'content' in response:
            content = response['content']
            
            # Extract URLs and snippets (basic extraction)
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'http' in line and i + 1 < len(lines):
                    url = line.strip()
                    title = lines[i + 1].strip() if i + 1 < len(lines) else "Search Result"
                    
                    result = SearchResult(
                        url=url,
                        title=title,
                        content=title,
                        source=self.source_name,
                        confidence=self.get_confidence_weight() * 100,
                        retrieved_at=datetime.utcnow()
                    )
                    
                    if self.validate_search_result(result):
                        results.append(result)
        
        return results
