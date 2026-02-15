"""
HaveIBeenPwned Connector for OSINT Framework

Searches the HIBP breach database for compromised email addresses
and provides information about data breaches.

API: https://haveibeenpwned.com/API/v3
"""

import asyncio
import logging
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass

import aiohttp
import structlog

from ..base import SourceConnector, SearchResult, EntityType


@dataclass
class BreachInfo:
    """Information about a data breach."""
    name: str
    title: str
    domain: str
    date: str
    compromised_count: int
    description: str
    breach_date: str
    added_date: str
    modified_date: str


class HAVEIBEENPWNEDConnector(SourceConnector):
    """
    Connector for HaveIBeenPwned breach database.
    Queries email addresses against known data breaches.
    """

    # API Configuration
    BASE_URL = "https://haveibeenpwned.com/api/v3"
    RATE_LIMIT_PER_HOUR = 1800  # 120/min = 1800/hr
    CONFIDENCE_WEIGHT = 0.95  # High confidence - official source
    TIMEOUT_SECONDS = 10

    def __init__(self, api_key: Optional[str] = None, user_agent: Optional[str] = None):
        """Initialize HIBP connector."""
        super().__init__()
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        self.api_key = api_key
        self.user_agent = user_agent or "OSINT-Framework/1.0"
        self.session: Optional[aiohttp.ClientSession] = None

        self.logger.info("HIBP Connector initialized", has_api_key=bool(api_key))

    @property
    def source_name(self) -> str:
        """Source identifier."""
        return "HaveIBeenPwned"

    @property
    def source_type(self) -> str:
        """Source classification."""
        return "Breach Database"

    def get_rate_limit(self) -> int:
        """Rate limit per hour."""
        return self.RATE_LIMIT_PER_HOUR

    def get_confidence_weight(self) -> float:
        """Confidence weight for this source."""
        return self.CONFIDENCE_WEIGHT

    def get_supported_entity_types(self) -> Set[EntityType]:
        """Entity types this connector can search."""
        return {EntityType.EMAIL_ADDRESS}

    async def search(
        self,
        search_query: Dict[str, Any],
        limit: int = 100
    ) -> SearchResult:
        """
        Search for email in HIBP breach database.
        
        Query format:
        {
            "email": "test@example.com"
        }
        """
        result = SearchResult(
            connector_name=self.source_name,
            query=search_query,
            raw_results=[]
        )

        email = search_query.get("email", "").lower().strip()
        if not email:
            self.logger.warning("Empty email provided to HIBP search")
            return result

        try:
            await self._check_rate_limit()

            breaches = await self._query_breaches(email)
            pastes = await self._query_pastes(email)

            if breaches or pastes:
                result.success = True
                result.parsed_entities = self._parse_results(email, breaches, pastes)
                self.logger.info(
                    "HIBP search successful",
                    email=email,
                    breach_count=len(breaches),
                    paste_count=len(pastes)
                )
            else:
                result.success = True
                result.parsed_entities = []
                self.logger.debug("HIBP no breaches found", email=email)

        except asyncio.TimeoutError:
            result.success = False
            result.error_message = "Request timeout"
            self.logger.error("HIBP request timeout", email=email)

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            self.logger.error("HIBP search failed", email=email, error=str(e))

        return result

    async def _query_breaches(self, email: str) -> List[Dict[str, Any]]:
        """Query HIBP for breaches involving this email."""
        url = f"{self.BASE_URL}/breachedaccount/{email}"
        headers = self._get_headers()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        return []
                    else:
                        self.logger.warning(
                            "HIBP breach query failed",
                            email=email,
                            status=response.status
                        )
                        return []

        except Exception as e:
            self.logger.error("HIBP breach query error", email=email, error=str(e))
            return []

    async def _query_pastes(self, email: str) -> List[Dict[str, Any]]:
        """Query HIBP for pastes involving this email."""
        url = f"{self.BASE_URL}/pasteaccount/{email}"
        headers = self._get_headers()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        return []
                    else:
                        self.logger.warning(
                            "HIBP paste query failed",
                            email=email,
                            status=response.status
                        )
                        return []

        except Exception as e:
            self.logger.error("HIBP paste query error", email=email, error=str(e))
            return []

    def _parse_results(
        self,
        email: str,
        breaches: List[Dict],
        pastes: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Parse HIBP API results."""
        entities = []

        # Process breach data
        for breach in breaches:
            entity = {
                'type': 'breach_exposure',
                'email': email,
                'breach_name': breach.get('Name'),
                'breach_title': breach.get('Title'),
                'breach_date': breach.get('BreachDate'),
                'added_date': breach.get('AddedDate'),
                'modified_date': breach.get('ModifiedDate'),
                'domain': breach.get('Domain'),
                'description': breach.get('Description'),
                'compromised_count': breach.get('PwnCount'),
                'is_verified': breach.get('IsVerified'),
                'is_fabricated': breach.get('IsFabricated'),
                'is_sensitive': breach.get('IsSensitive'),
                'is_retired': breach.get('IsRetired'),
                'is_spam_list': breach.get('IsSpamList'),
                'data_classes': breach.get('DataClasses', []),
                'confidence': self.CONFIDENCE_WEIGHT
            }
            entities.append(entity)
            self.logger.debug(
                "Breach exposure found",
                email=email,
                breach=breach.get('Name')
            )

        # Process paste data
        for paste in pastes:
            entity = {
                'type': 'paste_exposure',
                'email': email,
                'paste_id': paste.get('Id'),
                'source': paste.get('Source'),
                'title': paste.get('Title'),
                'date': paste.get('Date'),
                'count': paste.get('EmailCount'),
                'confidence': self.CONFIDENCE_WEIGHT * 0.9  # Slightly lower than breaches
            }
            entities.append(entity)
            self.logger.debug(
                "Paste exposure found",
                email=email,
                source=paste.get('Source')
            )

        return entities

    def _get_headers(self) -> Dict[str, str]:
        """Build request headers."""
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'application/json'
        }
        
        if self.api_key:
            headers['hibp-api-key'] = self.api_key

        return headers

    async def validate_credentials(self) -> bool:
        """Validate API credentials."""
        if not self.api_key:
            self.logger.warning("No API key provided for HIBP - limited functionality")
            return False

        try:
            headers = self._get_headers()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/breachedaccount/test@example.com",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    # Any non-401 response means auth works
                    is_valid = response.status != 401
                    self.logger.info("HIBP credentials validated", valid=is_valid)
                    return is_valid

        except Exception as e:
            self.logger.error("HIBP credential validation failed", error=str(e))
            return False


# Convenience function to create connector
def create_connector(api_key: Optional[str] = None) -> HAVEIBEENPWNEDConnector:
    """Create a new HIBP connector instance."""
    return HAVEIBEENPWNEDConnector(api_key=api_key)
