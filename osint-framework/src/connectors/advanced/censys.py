"""
Censys Connector for OSINT Framework

Searches Censys internet-wide scanning datasets for:
- SSL certificate enumeration and discovery
- Subdomain and host enumeration
- Organization infrastructure mapping
- Port scanning and service detection
- Autonomous system analysis

API: https://api.censys.io/
"""

import asyncio
import base64
import logging
from typing import Dict, List, Set, Optional, Any

import aiohttp
import structlog

from ..base import SourceConnector, SearchResult, EntityType


class CensysConnector(SourceConnector):
    """
    Connector for Censys internet scanning database.
    Provides certificate enumeration and host discovery.
    """

    BASE_URL = "https://api.censys.io/v2"
    RATE_LIMIT_PER_HOUR = 120
    CONFIDENCE_WEIGHT = 0.90
    TIMEOUT_SECONDS = 20

    def __init__(self, api_id: Optional[str] = None, api_secret: Optional[str] = None):
        """Initialize Censys connector."""
        super().__init__()
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        self.api_id = api_id
        self.api_secret = api_secret
        self._auth_header = self._build_auth_header() if api_id and api_secret else None

        self.logger.info("Censys Connector initialized", has_credentials=bool(self._auth_header))

    @property
    def source_name(self) -> str:
        """Source identifier."""
        return "Censys"

    @property
    def source_type(self) -> str:
        """Source classification."""
        return "Certificate & Host Database"

    def get_rate_limit(self) -> int:
        """Rate limit per hour."""
        return self.RATE_LIMIT_PER_HOUR

    def get_confidence_weight(self) -> float:
        """Confidence weight for this source."""
        return self.CONFIDENCE_WEIGHT

    def get_supported_entity_types(self) -> Set[EntityType]:
        """Entity types this connector can search."""
        return {
            EntityType.DOMAIN,
            EntityType.COMPANY
        }

    async def search(
        self,
        search_query: Dict[str, Any],
        limit: int = 100
    ) -> SearchResult:
        """
        Search Censys database.
        
        Query format:
        {
            "domain": "example.com",        # Certificate search for domain
            "certificate": "sha256_hash",   # Lookup specific certificate
            "organization": "Company Name"  # Find certs for org
        }
        """
        result = SearchResult(
            connector_name=self.source_name,
            query=search_query,
            raw_results=[]
        )

        if not self._auth_header:
            result.success = False
            result.error_message = "Censys API credentials not configured"
            self.logger.error("Censys search failed: missing credentials")
            return result

        try:
            await self._check_rate_limit()

            # Determine search type
            if 'domain' in search_query:
                results = await self._search_by_domain(search_query['domain'], limit)
            elif 'certificate' in search_query:
                results = await self._lookup_certificate(search_query['certificate'])
            elif 'organization' in search_query:
                results = await self._search_by_organization(search_query['organization'], limit)
            else:
                result.success = False
                result.error_message = "Invalid search parameters"
                return result

            if results:
                result.success = True
                result.parsed_entities = self._parse_results(results)
                self.logger.info(
                    "Censys search successful",
                    result_count=len(results)
                )
            else:
                result.success = True
                result.parsed_entities = []
                self.logger.debug("Censys no results found")

        except asyncio.TimeoutError:
            result.success = False
            result.error_message = "Request timeout"
            self.logger.error("Censys request timeout")

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            self.logger.error("Censys search failed", error=str(e))

        return result

    async def _search_by_domain(self, domain: str, limit: int) -> List[Dict]:
        """Search for certificates covering a domain."""
        query = f"names={domain}"
        params = {'q': query, 'per_page': min(limit, 100)}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/certificates",
                    params=params,
                    headers={'Authorization': f'Basic {self._auth_header}'},
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('results', [])
                    else:
                        self.logger.warning(
                            "Censys domain search failed",
                            domain=domain,
                            status=response.status
                        )
                        return []

        except Exception as e:
            self.logger.error("Censys domain search error", domain=domain, error=str(e))
            return []

    async def _lookup_certificate(self, cert_hash: str) -> Dict:
        """Lookup specific certificate by SHA-256."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/certificates/{cert_hash}",
                    headers={'Authorization': f'Basic {self._auth_header}'},
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        self.logger.debug("Certificate not found", cert_hash=cert_hash)
                        return {}
                    else:
                        self.logger.warning(
                            "Censys cert lookup failed",
                            cert_hash=cert_hash,
                            status=response.status
                        )
                        return {}

        except Exception as e:
            self.logger.error("Censys cert lookup error", cert_hash=cert_hash, error=str(e))
            return {}

    async def _search_by_organization(self, org: str, limit: int) -> List[Dict]:
        """Search for certificates issued to organization."""
        query = f"parsed.issuer.organization={org}"
        params = {'q': query, 'per_page': min(limit, 100)}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/certificates",
                    params=params,
                    headers={'Authorization': f'Basic {self._auth_header}'},
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('results', [])
                    else:
                        self.logger.warning(
                            "Censys org search failed",
                            org=org,
                            status=response.status
                        )
                        return []

        except Exception as e:
            self.logger.error("Censys org search error", org=org, error=str(e))
            return []

    def _parse_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """Parse Censys API results."""
        entities = []

        for result in results:
            parsed = result.get('parsed', {})
            
            entity = {
                'type': 'ssl_certificate',
                'sha256': result.get('sha256_fingerprint'),
                'sha1': result.get('sha1_fingerprint'),
                'md5': result.get('md5_fingerprint'),
                'subject': {
                    'cn': parsed.get('subject', {}).get('common_name'),
                    'o': parsed.get('subject', {}).get('organization'),
                    'ou': parsed.get('subject', {}).get('organizational_unit'),
                    'c': parsed.get('subject', {}).get('country'),
                    'st': parsed.get('subject', {}).get('state'),
                    'l': parsed.get('subject', {}).get('locality'),
                },
                'issuer': {
                    'cn': parsed.get('issuer', {}).get('common_name'),
                    'o': parsed.get('issuer', {}).get('organization'),
                    'c': parsed.get('issuer', {}).get('country'),
                },
                'validity': {
                    'not_before': parsed.get('validity', {}).get('not_before'),
                    'not_after': parsed.get('validity', {}).get('not_after'),
                    'days_remaining': self._calculate_days_remaining(
                        parsed.get('validity', {}).get('not_after')
                    )
                },
                'names': parsed.get('names', []),
                'public_key': {
                    'type': parsed.get('public_key', {}).get('key_algorithm'),
                    'bits': parsed.get('public_key', {}).get('rsa', {}).get('length'),
                },
                'extensions': {
                    'key_usage': parsed.get('extensions', {}).get('key_usage'),
                    'extended_key_usage': parsed.get('extensions', {}).get('extended_key_usage'),
                    'subject_alt_name': parsed.get('extensions', {}).get('subject_alt_name'),
                },
                'seen_in_ct_logs': result.get('seen_in_ct_logs', False),
                'ct_log_entries': result.get('ct_log_entries', []),
                'updated_at': result.get('updated_at'),
                'confidence': self.CONFIDENCE_WEIGHT
            }

            entities.append(entity)
            self.logger.debug(
                "Certificate found",
                sha256=result.get('sha256_fingerprint')[:16],
                names_count=len(parsed.get('names', []))
            )

        return entities

    @staticmethod
    def _calculate_days_remaining(not_after: Optional[str]) -> Optional[int]:
        """Calculate days until certificate expiration."""
        if not not_after:
            return None

        from datetime import datetime
        try:
            expiry = datetime.fromisoformat(not_after.replace('Z', '+00:00'))
            delta = expiry - datetime.now(expiry.tzinfo)
            return delta.days
        except (ValueError, TypeError):
            return None

    def _build_auth_header(self) -> Optional[str]:
        """Build HTTP Basic Auth header."""
        if not self.api_id or not self.api_secret:
            return None

        credentials = f"{self.api_id}:{self.api_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return encoded

    async def validate_credentials(self) -> bool:
        """Validate Censys API credentials."""
        if not self._auth_header:
            self.logger.warning("No Censys API credentials provided")
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/account",
                    headers={'Authorization': f'Basic {self._auth_header}'},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    is_valid = response.status == 200
                    self.logger.info("Censys credentials validated", valid=is_valid)
                    return is_valid

        except Exception as e:
            self.logger.error("Censys credential validation failed", error=str(e))
            return False


def create_connector(api_id: Optional[str] = None, api_secret: Optional[str] = None) -> CensysConnector:
    """Create a new Censys connector instance."""
    return CensysConnector(api_id=api_id, api_secret=api_secret)
