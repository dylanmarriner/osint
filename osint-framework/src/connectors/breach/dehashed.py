"""
Dehashed Connector for OSINT Framework

Searches the Dehashed credential leak database for compromised credentials
and provides detailed leak information.

API: https://www.dehashed.com/api
"""

import asyncio
import base64
import logging
from typing import Dict, List, Set, Optional, Any

import aiohttp
import structlog

from ..base import SourceConnector, SearchResult, EntityType


class DehashededConnector(SourceConnector):
    """
    Connector for Dehashed credential database.
    Searches for compromised credentials including emails, usernames, passwords, IPs.
    """

    BASE_URL = "https://api.dehashed.com/search"
    RATE_LIMIT_PER_HOUR = 600  # 10 requests/min
    CONFIDENCE_WEIGHT = 0.90
    TIMEOUT_SECONDS = 15

    def __init__(self, api_key: Optional[str] = None, email: Optional[str] = None):
        """Initialize Dehashed connector."""
        super().__init__()
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        self.api_key = api_key
        self.email = email
        self._auth_header = self._build_auth_header() if api_key and email else None

        self.logger.info("Dehashed Connector initialized", has_credentials=bool(self._auth_header))

    @property
    def source_name(self) -> str:
        """Source identifier."""
        return "Dehashed"

    @property
    def source_type(self) -> str:
        """Source classification."""
        return "Credential Leak Database"

    def get_rate_limit(self) -> int:
        """Rate limit per hour."""
        return self.RATE_LIMIT_PER_HOUR

    def get_confidence_weight(self) -> float:
        """Confidence weight for this source."""
        return self.CONFIDENCE_WEIGHT

    def get_supported_entity_types(self) -> Set[EntityType]:
        """Entity types this connector can search."""
        return {
            EntityType.EMAIL_ADDRESS,
            EntityType.USERNAME,
            EntityType.PHONE_NUMBER
        }

    async def search(
        self,
        search_query: Dict[str, Any],
        limit: int = 100
    ) -> SearchResult:
        """
        Search Dehashed database.
        
        Query format:
        {
            "email": "test@example.com"  # or
            "username": "john_smith"      # or
            "phone": "+1234567890"
        }
        """
        result = SearchResult(
            connector_name=self.source_name,
            query=search_query,
            raw_results=[]
        )

        if not self._auth_header:
            result.success = False
            result.error_message = "Missing Dehashed API credentials"
            self.logger.error("Dehashed search failed: missing credentials")
            return result

        # Extract search parameter
        search_param = None
        search_value = None

        if 'email' in search_query:
            search_param = 'email'
            search_value = search_query['email'].lower().strip()
        elif 'username' in search_query:
            search_param = 'username'
            search_value = search_query['username'].strip()
        elif 'phone' in search_query:
            search_param = 'phone'
            search_value = search_query['phone'].strip()
        else:
            result.success = False
            result.error_message = "No valid search parameter provided"
            return result

        try:
            await self._check_rate_limit()

            entries = await self._query_database(search_param, search_value, limit)

            if entries:
                result.success = True
                result.parsed_entities = self._parse_results(search_param, search_value, entries)
                self.logger.info(
                    "Dehashed search successful",
                    search_param=search_param,
                    entries_found=len(entries)
                )
            else:
                result.success = True
                result.parsed_entities = []
                self.logger.debug(
                    "Dehashed no results found",
                    search_param=search_param,
                    search_value=search_value
                )

        except asyncio.TimeoutError:
            result.success = False
            result.error_message = "Request timeout"
            self.logger.error(
                "Dehashed request timeout",
                search_param=search_param,
                search_value=search_value
            )

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            self.logger.error(
                "Dehashed search failed",
                search_param=search_param,
                error=str(e)
            )

        return result

    async def _query_database(
        self,
        search_param: str,
        search_value: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Query Dehashed database."""
        params = {
            'query': f'{search_param}:{search_value}',
            'size': min(limit, 10000)  # Dehashed max is 10k
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL,
                    params=params,
                    headers={
                        'Authorization': self._auth_header,
                        'Accept': 'application/json'
                    },
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('entries', [])
                    elif response.status == 401:
                        self.logger.error("Dehashed authentication failed")
                        return []
                    elif response.status == 429:
                        self.logger.warning("Dehashed rate limit hit")
                        return []
                    else:
                        self.logger.warning(
                            "Dehashed query failed",
                            status=response.status,
                            search_param=search_param
                        )
                        return []

        except asyncio.TimeoutError:
            raise

        except Exception as e:
            self.logger.error(
                "Dehashed query error",
                search_param=search_param,
                error=str(e)
            )
            return []

    def _parse_results(
        self,
        search_param: str,
        search_value: str,
        entries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Parse Dehashed API results."""
        entities = []

        for entry in entries:
            entity = {
                'type': 'credential_leak',
                'dehashed_id': entry.get('id'),
                'database_name': entry.get('database_name'),
                'email': entry.get('email'),
                'username': entry.get('username'),
                'password': entry.get('password'),
                'password_hash': entry.get('hashed_password'),
                'hash_type': entry.get('hash_type'),
                'phone': entry.get('phone_number'),
                'ip_address': entry.get('ip_address'),
                'name': entry.get('name'),
                'last_name': entry.get('last_name'),
                'address': entry.get('address'),
                'city': entry.get('city'),
                'state': entry.get('state'),
                'zip_code': entry.get('zip_code'),
                'country': entry.get('country'),
                'date_of_birth': entry.get('dob'),
                'vin': entry.get('vin'),
                'ssn': entry.get('ssn'),
                'linkedin_url': entry.get('linkedin_url'),
                'twitter_url': entry.get('twitter_url'),
                'created_at': entry.get('created_at'),
                'updated_at': entry.get('updated_at'),
                'search_param': search_param,
                'search_value': search_value,
                'confidence': self.CONFIDENCE_WEIGHT
            }

            # Calculate risk based on sensitive data
            risk_score = 0.5
            if entry.get('password'):
                risk_score += 0.25
            if entry.get('ssn'):
                risk_score += 0.20
            if entry.get('dob'):
                risk_score += 0.05

            entity['risk_score'] = min(1.0, risk_score)

            entities.append(entity)
            self.logger.debug(
                "Credential leak found",
                search_param=search_param,
                database=entry.get('database_name')
            )

        return entities

    def _build_auth_header(self) -> Optional[str]:
        """Build HTTP Basic Auth header."""
        if not self.api_key or not self.email:
            return None

        credentials = f"{self.email}:{self.api_key}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def validate_credentials(self) -> bool:
        """Validate API credentials."""
        if not self._auth_header:
            self.logger.warning("No Dehashed API credentials provided")
            return False

        try:
            params = {'query': 'email:test@example.com', 'size': 1}
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL,
                    params=params,
                    headers={'Authorization': self._auth_header},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    is_valid = response.status != 401
                    self.logger.info("Dehashed credentials validated", valid=is_valid)
                    return is_valid

        except Exception as e:
            self.logger.error("Dehashed credential validation failed", error=str(e))
            return False


def create_connector(api_key: Optional[str] = None, email: Optional[str] = None) -> DehashededConnector:
    """Create a new Dehashed connector instance."""
    return DehashededConnector(api_key=api_key, email=email)
