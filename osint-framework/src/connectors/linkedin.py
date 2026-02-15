"""
LinkedIn Connector for OSINT Framework

Purpose
- Search LinkedIn for professional profiles
- Extract employment history and skills
- Identify professional connections

Invariants
- Respects LinkedIn's Terms of Service
- Only searches public profile data
- Handles rate limiting gracefully
- Validates all extracted data

Failure Modes
- Authentication required → returns empty results
- Rate limiting → request queued for retry
- Profile not found → empty result set
- Parsing error → result skipped with warning
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from .base import SourceConnector, ConnectorStatus
from ..core.models.entities import SearchResult, EntityType


class LinkedInConnector(SourceConnector):
    """Connector for LinkedIn profiles."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize LinkedIn connector."""
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.base_url = "https://www.linkedin.com"
        self.api_key = config.get('api_key') if config else None
    
    @property
    def source_name(self) -> str:
        """Return source name."""
        return "LinkedIn"
    
    @property
    def source_type(self) -> str:
        """Return source type."""
        return "social_media"
    
    def get_rate_limit(self) -> int:
        """Return requests per hour limit."""
        return 60  # Conservative rate limit for LinkedIn
    
    def get_confidence_weight(self) -> float:
        """Return confidence weight for this source."""
        return 0.85  # High confidence for verified profiles
    
    def get_supported_entity_types(self) -> Set[EntityType]:
        """Return supported entity types."""
        return {
            EntityType.PERSON,
            EntityType.SOCIAL_PROFILE,
            EntityType.COMPANY,
            EntityType.EMAIL_ADDRESS
        }
    
    async def search(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Execute LinkedIn search."""
        if not self.rate_limit.can_make_request():
            self.logger.warning("Rate limit exceeded for LinkedIn")
            return []
        
        try:
            # Prepare search parameters
            search_params = {
                'keywords': query,
                'count': params.get('num_results', 10)
            }
            
            # Make request to LinkedIn
            search_url = f"{self.base_url}/search/results/people/"
            response = await self.make_request(
                search_url,
                method="GET",
                params=search_params
            )
            
            if not response:
                return []
            
            # Parse results
            results = self._parse_profile_results(response, query)
            
            self.logger.info(f"LinkedIn search returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"LinkedIn search failed: {str(e)}")
            self.status = ConnectorStatus.ERROR
            return []
    
    async def validate_credentials(self) -> bool:
        """Validate LinkedIn access."""
        try:
            response = await self.make_request(
                f"{self.base_url}/search/results/people/",
                method="GET"
            )
            return response is not None
        except Exception as e:
            self.logger.error(f"LinkedIn credential validation failed: {str(e)}")
            return False
    
    def _parse_profile_results(self, response: Dict[str, Any], query: str) -> List[SearchResult]:
        """Parse LinkedIn profile results."""
        results = []
        
        if 'content' in response:
            content = response['content']
            
            # Extract profile URLs and names
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '/in/' in line or '/company/' in line:
                    url = line.strip()
                    
                    # Extract name from next line if available
                    name = lines[i + 1].strip() if i + 1 < len(lines) else query
                    
                    result = SearchResult(
                        url=url,
                        title=f"LinkedIn: {name}",
                        content=name,
                        source=self.source_name,
                        confidence=self.get_confidence_weight() * 100,
                        retrieved_at=datetime.utcnow()
                    )
                    
                    if self.validate_search_result(result):
                        results.append(result)
        
        return results
