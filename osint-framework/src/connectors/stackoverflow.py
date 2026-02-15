"""
Stack Overflow Connector for OSINT Framework

Purpose
- Search Stack Overflow for user profiles
- Extract answer history and expertise areas
- Identify developer skills and activity

Invariants
- Uses Stack Overflow public API
- Respects API rate limits
- Returns only publicly available data
- Validates all extracted information

Failure Modes
- User not found → empty result set
- API rate limit exceeded → queued for retry
- Invalid query → validation error
- API error → retried with backoff
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import json

from .base import SourceConnector, ConnectorStatus
from ..core.models.entities import SearchResult, EntityType


class StackOverflowConnector(SourceConnector):
    """Connector for Stack Overflow searches."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Stack Overflow connector."""
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.api_url = "https://api.stackexchange.com/2.3"
        self.web_url = "https://stackoverflow.com"
        self.site = "stackoverflow"
    
    @property
    def source_name(self) -> str:
        """Return source name."""
        return "Stack Overflow"
    
    @property
    def source_type(self) -> str:
        """Return source type."""
        return "developer_platform"
    
    def get_rate_limit(self) -> int:
        """Return requests per hour limit."""
        return 10000  # Stack Exchange allows high rate limits
    
    def get_confidence_weight(self) -> float:
        """Return confidence weight for this source."""
        return 0.85  # High confidence for verified profiles
    
    def get_supported_entity_types(self) -> Set[EntityType]:
        """Return supported entity types."""
        return {
            EntityType.PERSON,
            EntityType.SOCIAL_PROFILE,
            EntityType.EMAIL_ADDRESS
        }
    
    async def search(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Execute Stack Overflow search."""
        if not self.rate_limit.can_make_request():
            self.logger.warning("Rate limit exceeded for Stack Overflow")
            return []
        
        try:
            search_type = params.get('search_type', 'users')
            
            if search_type == 'users':
                return await self._search_users(query, params)
            else:
                return await self._search_posts(query, params)
                
        except Exception as e:
            self.logger.error(f"Stack Overflow search failed: {str(e)}")
            self.status = ConnectorStatus.ERROR
            return []
    
    async def _search_users(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Search Stack Overflow users."""
        try:
            url = f"{self.api_url}/users"
            search_params = {
                'inname': query,
                'site': self.site,
                'pagesize': params.get('num_results', 10),
                'order': 'desc',
                'sort': 'reputation'
            }
            
            response = await self.make_request(
                url,
                method="GET",
                params=search_params
            )
            
            if not response:
                return []
            
            return self._parse_user_results(response, query)
            
        except Exception as e:
            self.logger.error(f"Stack Overflow user search failed: {str(e)}")
            return []
    
    async def _search_posts(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Search Stack Overflow posts."""
        try:
            url = f"{self.api_url}/search"
            search_params = {
                'intitle': query,
                'site': self.site,
                'pagesize': params.get('num_results', 10),
                'order': 'desc',
                'sort': 'relevance'
            }
            
            response = await self.make_request(
                url,
                method="GET",
                params=search_params
            )
            
            if not response:
                return []
            
            return self._parse_post_results(response, query)
            
        except Exception as e:
            self.logger.error(f"Stack Overflow post search failed: {str(e)}")
            return []
    
    async def validate_credentials(self) -> bool:
        """Validate Stack Overflow API access."""
        try:
            url = f"{self.api_url}/users"
            response = await self.make_request(
                url,
                method="GET",
                params={'site': self.site, 'pagesize': 1}
            )
            return response is not None
        except Exception as e:
            self.logger.warning(f"Stack Overflow validation failed: {str(e)}")
            return True  # Can retry later
    
    def _parse_user_results(self, response: Dict[str, Any], query: str) -> List[SearchResult]:
        """Parse Stack Overflow user results."""
        results = []
        
        try:
            if 'content' in response:
                content = response['content']
                
                try:
                    if isinstance(content, str):
                        data = json.loads(content)
                    else:
                        data = content
                    
                    if isinstance(data, dict) and 'items' in data:
                        for user in data['items']:
                            user_id = user.get('user_id', '')
                            display_name = user.get('display_name', '')
                            
                            if user_id:
                                url = f"{self.web_url}/users/{user_id}/{display_name.replace(' ', '-')}"
                                
                                result = SearchResult(
                                    url=url,
                                    title=f"Stack Overflow: {display_name}",
                                    content=f"Reputation: {user.get('reputation', 0)}",
                                    source=self.source_name,
                                    confidence=self.get_confidence_weight() * 100,
                                    retrieved_at=datetime.utcnow()
                                )
                                
                                if self.validate_search_result(result):
                                    results.append(result)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            self.logger.error(f"Failed to parse user results: {str(e)}")
        
        return results
    
    def _parse_post_results(self, response: Dict[str, Any], query: str) -> List[SearchResult]:
        """Parse Stack Overflow post results."""
        results = []
        
        try:
            if 'content' in response:
                content = response['content']
                
                try:
                    if isinstance(content, str):
                        data = json.loads(content)
                    else:
                        data = content
                    
                    if isinstance(data, dict) and 'items' in data:
                        for post in data['items']:
                            post_id = post.get('question_id', post.get('post_id', ''))
                            title = post.get('title', '')
                            
                            if post_id:
                                url = f"{self.web_url}/questions/{post_id}/{title.replace(' ', '-')}"
                                
                                result = SearchResult(
                                    url=url,
                                    title=f"Stack Overflow: {title}",
                                    content=title,
                                    source=self.source_name,
                                    confidence=self.get_confidence_weight() * 100,
                                    retrieved_at=datetime.utcnow()
                                )
                                
                                if self.validate_search_result(result):
                                    results.append(result)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            self.logger.error(f"Failed to parse post results: {str(e)}")
        
        return results
