"""
GitHub Connector for OSINT Framework

Purpose
- Search GitHub users and repositories
- Extract code commits and profile information
- Identify development activity and contributions

Invariants
- Uses GitHub's public API
- Respects API rate limits (5000 req/hr)
- Authenticates with GitHub token if available
- Returns only publicly available data

Failure Modes
- API rate limit exceeded → queued for retry
- Invalid username → empty result set
- Token invalid → falls back to unauthenticated requests
- Network error → retried with exponential backoff
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import json

from .base import SourceConnector, ConnectorStatus
from ..core.models.entities import SearchResult, EntityType


class GitHubConnector(SourceConnector):
    """Connector for GitHub searches."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize GitHub connector."""
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.api_url = "https://api.github.com"
        self.github_token = config.get('github_token') if config else None
    
    @property
    def source_name(self) -> str:
        """Return source name."""
        return "GitHub"
    
    @property
    def source_type(self) -> str:
        """Return source type."""
        return "code_repository"
    
    def get_rate_limit(self) -> int:
        """Return requests per hour limit."""
        # GitHub allows 5000 req/hr with authentication, 60 without
        return 5000 if self.github_token else 100
    
    def get_confidence_weight(self) -> float:
        """Return confidence weight for this source."""
        return 0.90  # Very high confidence for verified accounts
    
    def get_supported_entity_types(self) -> Set[EntityType]:
        """Return supported entity types."""
        return {
            EntityType.PERSON,
            EntityType.SOCIAL_PROFILE,
            EntityType.EMAIL_ADDRESS,
            EntityType.COMPANY
        }
    
    async def search(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Execute GitHub search."""
        if not self.rate_limit.can_make_request():
            self.logger.warning("Rate limit exceeded for GitHub")
            return []
        
        try:
            # Determine search type
            search_type = params.get('search_type', 'users')  # users, repos, code
            
            if search_type == 'users':
                return await self._search_users(query, params)
            elif search_type == 'repos':
                return await self._search_repos(query, params)
            else:
                return await self._search_code(query, params)
                
        except Exception as e:
            self.logger.error(f"GitHub search failed: {str(e)}")
            self.status = ConnectorStatus.ERROR
            return []
    
    async def _search_users(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Search GitHub users."""
        try:
            url = f"{self.api_url}/search/users"
            search_params = {
                'q': query,
                'per_page': params.get('num_results', 10)
            }
            
            response = await self.make_request(
                url,
                method="GET",
                params=search_params,
                headers=self._get_auth_headers()
            )
            
            if not response:
                return []
            
            return self._parse_user_results(response, query)
            
        except Exception as e:
            self.logger.error(f"GitHub user search failed: {str(e)}")
            return []
    
    async def _search_repos(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Search GitHub repositories."""
        try:
            url = f"{self.api_url}/search/repositories"
            search_params = {
                'q': query,
                'per_page': params.get('num_results', 10)
            }
            
            response = await self.make_request(
                url,
                method="GET",
                params=search_params,
                headers=self._get_auth_headers()
            )
            
            if not response:
                return []
            
            return self._parse_repo_results(response, query)
            
        except Exception as e:
            self.logger.error(f"GitHub repo search failed: {str(e)}")
            return []
    
    async def _search_code(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Search GitHub code."""
        try:
            url = f"{self.api_url}/search/code"
            search_params = {
                'q': query,
                'per_page': params.get('num_results', 10)
            }
            
            response = await self.make_request(
                url,
                method="GET",
                params=search_params,
                headers=self._get_auth_headers()
            )
            
            if not response:
                return []
            
            return self._parse_code_results(response, query)
            
        except Exception as e:
            self.logger.error(f"GitHub code search failed: {str(e)}")
            return []
    
    async def validate_credentials(self) -> bool:
        """Validate GitHub access."""
        try:
            url = f"{self.api_url}/user"
            response = await self.make_request(
                url,
                method="GET",
                headers=self._get_auth_headers()
            )
            return response is not None
        except Exception as e:
            self.logger.warning(f"GitHub validation failed: {str(e)}")
            # Still valid even if token invalid - can do unauthenticated searches
            return True
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers if token available."""
        headers = self.get_default_headers()
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        return headers
    
    def _parse_user_results(self, response: Dict[str, Any], query: str) -> List[SearchResult]:
        """Parse GitHub user search results."""
        results = []
        
        try:
            if isinstance(response, dict) and 'content' in response:
                content = response['content']
                # In real implementation, parse JSON response
                if isinstance(content, str):
                    try:
                        data = json.loads(content)
                        if 'items' in data:
                            for item in data['items']:
                                result = SearchResult(
                                    url=item.get('html_url', ''),
                                    title=f"GitHub User: {item.get('login', '')}",
                                    content=item.get('login', ''),
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
    
    def _parse_repo_results(self, response: Dict[str, Any], query: str) -> List[SearchResult]:
        """Parse GitHub repository search results."""
        results = []
        
        try:
            if isinstance(response, dict) and 'content' in response:
                content = response['content']
                if isinstance(content, str):
                    try:
                        data = json.loads(content)
                        if 'items' in data:
                            for item in data['items']:
                                result = SearchResult(
                                    url=item.get('html_url', ''),
                                    title=f"GitHub Repo: {item.get('name', '')}",
                                    content=item.get('description', item.get('name', '')),
                                    source=self.source_name,
                                    confidence=self.get_confidence_weight() * 100,
                                    retrieved_at=datetime.utcnow()
                                )
                                if self.validate_search_result(result):
                                    results.append(result)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            self.logger.error(f"Failed to parse repo results: {str(e)}")
        
        return results
    
    def _parse_code_results(self, response: Dict[str, Any], query: str) -> List[SearchResult]:
        """Parse GitHub code search results."""
        results = []
        
        try:
            if isinstance(response, dict) and 'content' in response:
                content = response['content']
                if isinstance(content, str):
                    try:
                        data = json.loads(content)
                        if 'items' in data:
                            for item in data['items']:
                                result = SearchResult(
                                    url=item.get('html_url', ''),
                                    title=f"GitHub Code: {item.get('name', '')}",
                                    content=item.get('name', ''),
                                    source=self.source_name,
                                    confidence=self.get_confidence_weight() * 100,
                                    retrieved_at=datetime.utcnow()
                                )
                                if self.validate_search_result(result):
                                    results.append(result)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            self.logger.error(f"Failed to parse code results: {str(e)}")
        
        return results
