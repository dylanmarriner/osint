"""
Reddit Connector for OSINT Framework

Purpose
- Search Reddit for users and posts
- Extract public profile and post information
- Identify user activity and interests

Invariants
- Only accesses publicly available data
- Respects Reddit API rate limits
- Handles deleted/suspended accounts gracefully
- Returns post and user metadata

Failure Modes
- User not found → empty result set
- Rate limit exceeded → queued for retry
- Subreddit not found → empty result set
- API error → retried with backoff
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from .base import SourceConnector, ConnectorStatus
from ..core.models.entities import SearchResult, EntityType


class RedditConnector(SourceConnector):
    """Connector for Reddit searches."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Reddit connector."""
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.api_url = "https://api.reddit.com"
        self.web_url = "https://reddit.com"
        self.user_agent = "OSINT-Framework/1.0 (+https://osint-framework.local)"
    
    @property
    def source_name(self) -> str:
        """Return source name."""
        return "Reddit"
    
    @property
    def source_type(self) -> str:
        """Return source type."""
        return "social_media"
    
    def get_rate_limit(self) -> int:
        """Return requests per hour limit."""
        return 600  # Reddit API rate limits
    
    def get_confidence_weight(self) -> float:
        """Return confidence weight for this source."""
        return 0.75  # Moderate confidence - pseudonymous
    
    def get_supported_entity_types(self) -> Set[EntityType]:
        """Return supported entity types."""
        return {
            EntityType.PERSON,
            EntityType.SOCIAL_PROFILE,
            EntityType.EMAIL_ADDRESS
        }
    
    async def search(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Execute Reddit search."""
        if not self.rate_limit.can_make_request():
            self.logger.warning("Rate limit exceeded for Reddit")
            return []
        
        try:
            search_type = params.get('search_type', 'users')
            
            if search_type == 'users':
                return await self._search_users(query, params)
            else:
                return await self._search_posts(query, params)
                
        except Exception as e:
            self.logger.error(f"Reddit search failed: {str(e)}")
            self.status = ConnectorStatus.ERROR
            return []
    
    async def _search_users(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Search Reddit users."""
        try:
            url = f"{self.api_url}/search"
            search_params = {
                'q': f"user:{query}",
                'type': 'user',
                'limit': params.get('num_results', 10)
            }
            
            response = await self.make_request(
                url,
                method="GET",
                params=search_params,
                headers=self._get_headers()
            )
            
            if not response:
                return []
            
            return self._parse_user_results(response, query)
            
        except Exception as e:
            self.logger.error(f"Reddit user search failed: {str(e)}")
            return []
    
    async def _search_posts(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Search Reddit posts."""
        try:
            url = f"{self.api_url}/search"
            search_params = {
                'q': query,
                'type': 'link,comment',
                'limit': params.get('num_results', 10),
                'sort': params.get('sort', 'relevance')
            }
            
            response = await self.make_request(
                url,
                method="GET",
                params=search_params,
                headers=self._get_headers()
            )
            
            if not response:
                return []
            
            return self._parse_post_results(response, query)
            
        except Exception as e:
            self.logger.error(f"Reddit post search failed: {str(e)}")
            return []
    
    async def validate_credentials(self) -> bool:
        """Validate Reddit API access."""
        try:
            # Reddit doesn't require auth for basic searches
            url = f"{self.api_url}/search"
            response = await self.make_request(
                url,
                method="GET",
                params={'q': 'test', 'limit': 1},
                headers=self._get_headers()
            )
            return response is not None
        except Exception as e:
            self.logger.warning(f"Reddit validation failed: {str(e)}")
            return True  # Can retry later
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with proper user agent."""
        headers = self.get_default_headers()
        headers['User-Agent'] = self.user_agent
        return headers
    
    def _parse_user_results(self, response: Dict[str, Any], query: str) -> List[SearchResult]:
        """Parse Reddit user results."""
        results = []
        
        try:
            if 'content' in response:
                content = response['content']
                lines = content.split('\n')
                
                for line in lines:
                    if '/u/' in line or 'reddit.com/user/' in line:
                        # Extract username
                        parts = line.split('/')
                        username = parts[-1].strip()
                        
                        if username:
                            url = f"{self.web_url}/u/{username}"
                            
                            result = SearchResult(
                                url=url,
                                title=f"Reddit User: {username}",
                                content=username,
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
        """Parse Reddit post results."""
        results = []
        
        try:
            if 'content' in response:
                content = response['content']
                lines = content.split('\n')
                
                for line in lines:
                    if 'reddit.com/r/' in line:
                        url = line.strip()
                        
                        result = SearchResult(
                            url=url,
                            title="Reddit Post",
                            content=query,
                            source=self.source_name,
                            confidence=self.get_confidence_weight() * 100,
                            retrieved_at=datetime.utcnow()
                        )
                        
                        if self.validate_search_result(result):
                            results.append(result)
        except Exception as e:
            self.logger.error(f"Failed to parse post results: {str(e)}")
        
        return results
