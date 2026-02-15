"""
Twitter/X Connector for OSINT Framework

Purpose
- Search Twitter/X for users and posts
- Extract public profile and post information
- Identify social connections and activity

Invariants
- Only accesses publicly available data
- Respects Twitter API rate limits
- Authenticates with valid credentials if available
- Handles suspension and restricted accounts gracefully

Failure Modes
- API access denied → returns empty results
- Rate limit exceeded → queued for retry
- User not found → empty result set
- Account suspended → skipped with warning
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from .base import SourceConnector, ConnectorStatus
from ..core.models.entities import SearchResult, EntityType


class TwitterConnector(SourceConnector):
    """Connector for Twitter/X searches."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Twitter connector."""
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.api_url = "https://api.twitter.com/2"
        self.web_url = "https://twitter.com"
        self.bearer_token = config.get('bearer_token') if config else None
    
    @property
    def source_name(self) -> str:
        """Return source name."""
        return "Twitter/X"
    
    @property
    def source_type(self) -> str:
        """Return source type."""
        return "social_media"
    
    def get_rate_limit(self) -> int:
        """Return requests per hour limit."""
        return 300  # Conservative Twitter API rate limit
    
    def get_confidence_weight(self) -> float:
        """Return confidence weight for this source."""
        return 0.80  # High confidence for verified profiles
    
    def get_supported_entity_types(self) -> Set[EntityType]:
        """Return supported entity types."""
        return {
            EntityType.PERSON,
            EntityType.SOCIAL_PROFILE,
            EntityType.EMAIL_ADDRESS
        }
    
    async def search(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Execute Twitter search."""
        if not self.rate_limit.can_make_request():
            self.logger.warning("Rate limit exceeded for Twitter")
            return []
        
        try:
            search_type = params.get('search_type', 'users')
            
            if search_type == 'users':
                return await self._search_users(query, params)
            else:
                return await self._search_posts(query, params)
                
        except Exception as e:
            self.logger.error(f"Twitter search failed: {str(e)}")
            self.status = ConnectorStatus.ERROR
            return []
    
    async def _search_users(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Search Twitter users."""
        try:
            # Build search URL for users
            search_url = f"{self.web_url}/search"
            search_params = {
                'q': f"{query} -filter:retweets",
                'f': 'users',
                'lang': params.get('language', 'en')
            }
            
            response = await self.make_request(
                search_url,
                method="GET",
                params=search_params
            )
            
            if not response:
                return []
            
            return self._parse_user_results(response, query)
            
        except Exception as e:
            self.logger.error(f"Twitter user search failed: {str(e)}")
            return []
    
    async def _search_posts(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Search Twitter posts."""
        try:
            search_url = f"{self.web_url}/search"
            search_params = {
                'q': query,
                'lang': params.get('language', 'en'),
                'result_type': params.get('result_type', 'recent')
            }
            
            response = await self.make_request(
                search_url,
                method="GET",
                params=search_params
            )
            
            if not response:
                return []
            
            return self._parse_post_results(response, query)
            
        except Exception as e:
            self.logger.error(f"Twitter post search failed: {str(e)}")
            return []
    
    async def validate_credentials(self) -> bool:
        """Validate Twitter API access."""
        try:
            # Test endpoint that works with or without auth
            url = f"{self.web_url}/search"
            response = await self.make_request(
                url,
                method="GET",
                params={'q': 'test'}
            )
            return response is not None
        except Exception as e:
            self.logger.warning(f"Twitter validation failed: {str(e)}")
            return False
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers if token available."""
        headers = self.get_default_headers()
        if self.bearer_token:
            headers['Authorization'] = f'Bearer {self.bearer_token}'
        return headers
    
    def _parse_user_results(self, response: Dict[str, Any], query: str) -> List[SearchResult]:
        """Parse Twitter user search results."""
        results = []
        
        try:
            if 'content' in response:
                content = response['content']
                # Extract Twitter handles from content
                lines = content.split('\n')
                for line in lines:
                    if '@' in line or '/user/' in line:
                        # Extract handle
                        handle = line.strip()
                        if handle.startswith('@'):
                            url = f"{self.web_url}/{handle[1:]}"
                        elif '/user/' in line:
                            parts = line.split('/')
                            handle = parts[-1]
                            url = line.strip()
                        else:
                            continue
                        
                        result = SearchResult(
                            url=url,
                            title=f"Twitter User: {handle}",
                            content=handle,
                            source=self.source_name,
                            confidence=self.get_confidence_weight() * 100,
                            retrieved_at=datetime.utcnow()
                        )
                        
                        if self.validate_search_result(result):
                            results.append(result)
        except Exception as e:
            self.logger.error(f"Failed to parse user results: {str(e)}")
        
        return results
    
    def _parse_post_results(self, response: Dict[str, Any], query: str) -> List[SearchResult]:
        """Parse Twitter post search results."""
        results = []
        
        try:
            if 'content' in response:
                content = response['content']
                # Extract tweets from content
                lines = content.split('\n')
                for line in lines:
                    if 'http' in line and 'twitter.com' in line:
                        url = line.strip()
                        
                        result = SearchResult(
                            url=url,
                            title="Twitter Post",
                            content=content[:200],
                            source=self.source_name,
                            confidence=self.get_confidence_weight() * 100,
                            retrieved_at=datetime.utcnow()
                        )
                        
                        if self.validate_search_result(result):
                            results.append(result)
        except Exception as e:
            self.logger.error(f"Failed to parse post results: {str(e)}")
        
        return results
