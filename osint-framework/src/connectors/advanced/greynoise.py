"""
GreyNoise Connector for OSINT Framework

Searches GreyNoise Internet Intelligence database for:
- Internet traffic classification and threat intelligence
- Malicious vs. benign IP determination
- Exploit and attack activity detection
- Threat actor identification
- Honeypot detection

API: https://www.greynoise.io/
"""

import asyncio
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
import aiohttp
import structlog

from ..base import SourceConnector, SearchResult, EntityType


class GreyNoiseConnector(SourceConnector):
    """
    Connector for GreyNoise Internet Intelligence.
    Provides threat intelligence and IP reputation data.
    """

    BASE_URL = "https://api.greynoise.io/v3"
    RATE_LIMIT_PER_HOUR = 150  # Enterprise rate limit
    CONFIDENCE_WEIGHT = 0.95
    TIMEOUT_SECONDS = 20

    def __init__(self, api_key: Optional[str] = None):
        """Initialize GreyNoise connector."""
        super().__init__()
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        self.api_key = api_key
        self.session = None
        
        self.logger.info("GreyNoise Connector initialized", has_credentials=bool(api_key))

    @property
    def source_name(self) -> str:
        """Source identifier."""
        return "GreyNoise"

    @property
    def source_type(self) -> str:
        """Source classification."""
        return "Threat Intelligence & IP Reputation"

    def get_rate_limit(self) -> int:
        """Rate limit per hour."""
        return self.RATE_LIMIT_PER_HOUR

    def get_confidence_weight(self) -> float:
        """Confidence weight for this source."""
        return self.CONFIDENCE_WEIGHT

    def get_supported_entity_types(self) -> Set[EntityType]:
        """Entity types this connector can search."""
        return {
            EntityType.IP_ADDRESS,
            EntityType.DOMAIN,
            EntityType.URL
        }

    async def search(
        self,
        search_query: Dict[str, Any],
        limit: int = 100
    ) -> SearchResult:
        """
        Search GreyNoise database.
        
        Query format:
        {
            "ip": "8.8.8.8",                    # Lookup IP reputation
            "query": "classification:malicious", # Advanced query
            "limit": 100                        # Results limit
        }
        """
        result = SearchResult(
            connector_name=self.source_name,
            query=search_query,
            raw_results=[]
        )

        if not self.api_key:
            result.success = False
            result.error_message = "GreyNoise API key not configured"
            self.logger.error("GreyNoise search failed: missing credentials")
            return result

        try:
            await self.initialize()
            
            if "ip" in search_query:
                # Single IP lookup
                ip_result = await self._lookup_ip(search_query["ip"])
                if ip_result:
                    result.raw_results.append(ip_result)
                    result.success = True
            
            elif "query" in search_query:
                # Advanced query search
                query_results = await self._advanced_search(
                    search_query["query"],
                    limit=min(limit, search_query.get("limit", 100))
                )
                result.raw_results.extend(query_results)
                result.success = bool(query_results)
            
            else:
                result.error_message = "Query must contain 'ip' or 'query' key"
                result.success = False

            result.result_count = len(result.raw_results)
            self.logger.info(
                "GreyNoise search completed",
                query=search_query,
                result_count=result.result_count
            )

        except Exception as e:
            result.success = False
            result.error_message = f"GreyNoise search error: {str(e)}"
            self.logger.error("GreyNoise search failed", error=str(e))

        return result

    async def _lookup_ip(self, ip: str) -> Optional[Dict[str, Any]]:
        """Lookup IP reputation in GreyNoise."""
        try:
            url = f"{self.BASE_URL}/ips/{ip}"
            headers = {
                "Authorization": f"key {self.api_key}",
                "Accept": "application/json"
            }
            
            response = await self.make_request(url, "GET", headers=headers)
            if response and "seen" in response:
                return {
                    "ip": ip,
                    "classification": response.get("classification"),  # malicious, benign, unknown
                    "seen": response.get("seen"),
                    "last_seen": response.get("last_seen"),
                    "trust_level": response.get("trust_level"),
                    "threat_level": response.get("threat_level"),
                    "spoofable": response.get("spoofable", False),
                    "actor": response.get("actor"),
                    "bot": response.get("bot", False),
                    "vpn": response.get("vpn", False),
                    "proxy": response.get("proxy", False),
                    "metadata": response.get("metadata", {}),
                    "tags": response.get("tags", []),
                    "raw_data": response
                }
            return None
            
        except Exception as e:
            self.logger.error(f"GreyNoise IP lookup failed for {ip}", error=str(e))
            return None

    async def _advanced_search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Execute advanced query against GreyNoise."""
        try:
            url = f"{self.BASE_URL}/query"
            headers = {
                "Authorization": f"key {self.api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            
            payload = {
                "query": query,
                "limit": limit
            }
            
            response = await self.make_request(
                url, "POST", headers=headers, json=payload
            )
            
            if response and "data" in response:
                results = []
                for item in response.get("data", []):
                    results.append({
                        "ip": item.get("ip"),
                        "classification": item.get("classification"),
                        "seen": item.get("seen"),
                        "last_seen": item.get("last_seen"),
                        "actor": item.get("actor"),
                        "tags": item.get("tags", []),
                        "raw_data": item
                    })
                return results
            return []
            
        except Exception as e:
            self.logger.error(f"GreyNoise advanced search failed", error=str(e))
            return []

    async def validate_credentials(self) -> bool:
        """Validate API credentials."""
        if not self.api_key:
            return False
        
        try:
            await self.initialize()
            
            url = f"{self.BASE_URL}/account"
            headers = {
                "Authorization": f"key {self.api_key}",
                "Accept": "application/json"
            }
            
            response = await self.make_request(url, "GET", headers=headers)
            return response is not None and "id" in response
            
        except Exception as e:
            self.logger.error(f"GreyNoise credential validation failed", error=str(e))
            return False

    async def search_by_actor(self, actor_name: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for all IPs attributed to a threat actor."""
        query = f'actor:"{actor_name}"'
        return await self._advanced_search(query, limit=limit)

    async def search_malicious(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Search for malicious IPs."""
        query = "classification:malicious"
        return await self._advanced_search(query, limit=limit)

    async def search_honeypot(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Search for honeypot-targeted IPs."""
        query = "tags:honeypot"
        return await self._advanced_search(query, limit=limit)

    async def search_exploited(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Search for IPs with recent exploit activity."""
        query = "tags:exploit-attempt"
        return await self._advanced_search(query, limit=limit)
