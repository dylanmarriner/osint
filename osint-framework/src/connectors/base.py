"""
Base connector interface and registry for OSINT sources.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import logging
from enum import Enum

from ..core.models.entities import SearchResult, EntityType


class ConnectorStatus(Enum):
    """Connector operational status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


@dataclass
class RateLimitInfo:
    """Rate limiting information for a connector."""
    requests_per_hour: int
    requests_per_minute: int
    current_requests: int = 0
    reset_time: Optional[datetime] = None
    backoff_until: Optional[datetime] = None

    def can_make_request(self) -> bool:
        """Check if a request can be made."""
        now = datetime.utcnow()
        
        # Check if we're in backoff
        if self.backoff_until and now < self.backoff_until:
            return False
        
        # Check if we've hit hourly limit
        if self.reset_time and now >= self.reset_time:
            self.current_requests = 0
            self.reset_time = now + timedelta(hours=1)
        
        return self.current_requests < self.requests_per_hour

    def record_request(self):
        """Record a request being made."""
        self.current_requests += 1
        if self.reset_time is None:
            self.reset_time = datetime.utcnow() + timedelta(hours=1)

    def set_backoff(self, seconds: int):
        """Set backoff period."""
        self.backoff_until = datetime.utcnow() + timedelta(seconds=seconds)


class SourceConnector(ABC):
    """Base interface for all OSINT source connectors."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize connector with configuration."""
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.status = ConnectorStatus.ACTIVE
        self.rate_limit = RateLimitInfo(
            requests_per_hour=self.get_rate_limit(),
            requests_per_minute=self.get_rate_limit() // 60
        )
        self._session = None

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable source name."""
        pass

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Source type identifier."""
        pass

    @abstractmethod
    def get_rate_limit(self) -> int:
        """Requests per hour limit."""
        pass

    @abstractmethod
    async def search(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Execute search against source."""
        pass

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate API credentials if required."""
        pass

    @abstractmethod
    def get_confidence_weight(self) -> float:
        """Base confidence weight for this source."""
        pass

    @abstractmethod
    def get_supported_entity_types(self) -> Set[EntityType]:
        """Get types of entities this connector can discover."""
        pass

    async def initialize(self):
        """Initialize connector resources."""
        if not self._session:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)

    async def cleanup(self):
        """Cleanup connector resources."""
        if self._session:
            await self._session.close()
            self._session = None

    async def make_request(self, url: str, method: str = "GET", **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request with rate limiting and error handling."""
        if not self.rate_limit.can_make_request():
            self.logger.warning(f"Rate limit exceeded for {self.source_name}")
            self.status = ConnectorStatus.RATE_LIMITED
            return None

        await self.initialize()
        
        try:
            headers = self.get_default_headers()
            headers.update(kwargs.pop('headers', {}))
            
            async with self._session.request(method, url, headers=headers, **kwargs) as response:
                self.rate_limit.record_request()
                
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.rate_limit.set_backoff(retry_after)
                    self.status = ConnectorStatus.RATE_LIMITED
                    self.logger.warning(f"Rate limited for {self.source_name}, backing off for {retry_after}s")
                    return None
                
                if response.status >= 400:
                    self.logger.error(f"HTTP {response.status} from {self.source_name}: {url}")
                    self.status = ConnectorStatus.ERROR
                    return None
                
                self.status = ConnectorStatus.ACTIVE
                content_type = response.headers.get('content-type', '')
                
                if 'application/json' in content_type:
                    return await response.json()
                else:
                    return {'content': await response.text(), 'status': response.status}

        except Exception as e:
            self.logger.error(f"Request failed for {self.source_name}: {str(e)}")
            self.status = ConnectorStatus.ERROR
            return None

    def get_default_headers(self) -> Dict[str, str]:
        """Get default HTTP headers."""
        return {
            'User-Agent': 'Mozilla/5.0 (compatible; OSINT-Framework/1.0)',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def validate_search_result(self, result: SearchResult) -> bool:
        """Validate a search result meets minimum criteria."""
        if not result.url or not result.title:
            return False
        if result.confidence < 0 or result.confidence > 100:
            return False
        if len(result.content.strip()) == 0:
            return False
        return True

    def get_status(self) -> Dict[str, Any]:
        """Get connector status information."""
        return {
            'source_name': self.source_name,
            'source_type': self.source_type,
            'status': self.status.value,
            'rate_limit': {
                'requests_per_hour': self.rate_limit.requests_per_hour,
                'current_requests': self.rate_limit.current_requests,
                'reset_time': self.rate_limit.reset_time.isoformat() if self.rate_limit.reset_time else None,
                'backoff_until': self.rate_limit.backoff_until.isoformat() if self.rate_limit.backoff_until else None
            }
        }


class ConnectorRegistry:
    """Registry for managing OSINT source connectors."""

    def __init__(self):
        self._connectors: Dict[str, SourceConnector] = {}
        self._connector_configs: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)

    def register(self, connector: SourceConnector, config: Optional[Dict[str, Any]] = None):
        """Register a connector."""
        if connector.source_name in self._connectors:
            self.logger.warning(f"Connector {connector.source_name} already registered, overwriting")
        
        self._connectors[connector.source_name] = connector
        self._connector_configs[connector.source_name] = config or {}
        self.logger.info(f"Registered connector: {connector.source_name}")

    def unregister(self, source_name: str):
        """Unregister a connector."""
        if source_name in self._connectors:
            connector = self._connectors.pop(source_name)
            asyncio.create_task(connector.cleanup())
            self._connector_configs.pop(source_name, None)
            self.logger.info(f"Unregistered connector: {source_name}")

    def get_connector(self, source_name: str) -> Optional[SourceConnector]:
        """Get a connector by name."""
        return self._connectors.get(source_name)

    def list_connectors(self) -> List[str]:
        """List all registered connector names."""
        return list(self._connectors.keys())

    def get_connectors_by_type(self, entity_type: EntityType) -> List[SourceConnector]:
        """Get connectors that support a specific entity type."""
        matching_connectors = []
        for connector in self._connectors.values():
            if entity_type in connector.get_supported_entity_types():
                matching_connectors.append(connector)
        return matching_connectors

    async def initialize_all(self):
        """Initialize all registered connectors."""
        for connector in self._connectors.values():
            try:
                await connector.initialize()
                if await connector.validate_credentials():
                    self.logger.info(f"Initialized connector: {connector.source_name}")
                else:
                    self.logger.warning(f"Failed credential validation for: {connector.source_name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize connector {connector.source_name}: {str(e)}")

    async def cleanup_all(self):
        """Cleanup all registered connectors."""
        tasks = []
        for connector in self._connectors.values():
            tasks.append(connector.cleanup())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def search_all_connectors(self, query: str, params: Dict[str, Any], 
                                  entity_types: Optional[List[EntityType]] = None) -> Dict[str, List[SearchResult]]:
        """Search across all relevant connectors."""
        results = {}
        
        # Determine which connectors to use
        connectors_to_search = []
        if entity_types:
            for entity_type in entity_types:
                connectors_to_search.extend(self.get_connectors_by_type(entity_type))
            # Remove duplicates
            connectors_to_search = list(set(connectors_to_search))
        else:
            connectors_to_search = list(self._connectors.values())

        # Search in parallel
        tasks = []
        for connector in connectors_to_search:
            if connector.status == ConnectorStatus.ACTIVE:
                task = self._search_connector_safe(connector, query, params)
                tasks.append((connector.source_name, task))

        if tasks:
            connector_results = await asyncio.gather(
                *[task for _, task in tasks], 
                return_exceptions=True
            )
            
            for (source_name, _), result in zip(tasks, connector_results):
                if isinstance(result, Exception):
                    self.logger.error(f"Search failed for {source_name}: {str(result)}")
                    results[source_name] = []
                else:
                    results[source_name] = result

        return results

    async def _search_connector_safe(self, connector: SourceConnector, query: str, 
                                   params: Dict[str, Any]) -> List[SearchResult]:
        """Safely search a connector with error handling."""
        try:
            results = await connector.search(query, params)
            # Validate results
            valid_results = []
            for result in results:
                if connector.validate_search_result(result):
                    valid_results.append(result)
                else:
                    connector.logger.warning(f"Invalid search result from {connector.source_name}: {result.url}")
            
            connector.logger.info(f"Found {len(valid_results)} valid results from {connector.source_name}")
            return valid_results
            
        except Exception as e:
            connector.logger.error(f"Search failed for {connector.source_name}: {str(e)}")
            connector.status = ConnectorStatus.ERROR
            return []

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all connectors."""
        return {
            name: connector.get_status()
            for name, connector in self._connectors.items()
        }

    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on all connectors."""
        health_status = {}
        
        for name, connector in self._connectors.items():
            try:
                is_healthy = await connector.validate_credentials()
                health_status[name] = is_healthy
                
                if not is_healthy:
                    connector.status = ConnectorStatus.ERROR
                    connector.logger.warning(f"Health check failed for {name}")
                else:
                    connector.status = ConnectorStatus.ACTIVE
                    
            except Exception as e:
                health_status[name] = False
                connector.status = ConnectorStatus.ERROR
                connector.logger.error(f"Health check error for {name}: {str(e)}")
        
        return health_status


# Global registry instance
_registry = ConnectorRegistry()


def get_registry() -> ConnectorRegistry:
    """Get the global connector registry."""
    return _registry


def register_connector(connector_class, config: Optional[Dict[str, Any]] = None):
    """Decorator to register a connector class."""
    def decorator(cls):
        instance = cls(config)
        _registry.register(instance, config)
        return cls
    return decorator


# Utility functions
def calculate_search_confidence(base_confidence: float, source_weight: float, 
                               result_relevance: float) -> float:
    """Calculate overall confidence for a search result."""
    return min(100.0, base_confidence * source_weight * result_relevance)


def extract_domain_from_url(url: str) -> Optional[str]:
    """Extract domain from URL."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return None


def is_url_accessible(url: str, timeout: int = 5) -> bool:
    """Check if URL is accessible."""
    import httpx
    
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.head(url)
            return response.status_code < 400
    except Exception:
        return False
