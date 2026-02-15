"""
Shodan Connector for OSINT Framework

Searches Shodan's internet-wide scanning database for:
- Devices and servers running on the internet
- Port scanning and service detection
- Vulnerability identification
- Geographic location of services
- Organization/network mapping

API: https://api.shodan.io/
"""

import asyncio
import logging
from typing import Dict, List, Set, Optional, Any

import aiohttp
import structlog

from ..base import SourceConnector, SearchResult, EntityType


class ShodanConnector(SourceConnector):
    """
    Connector for Shodan internet device database.
    Identifies internet-facing devices, services, and vulnerabilities.
    """

    BASE_URL = "https://api.shodan.io"
    RATE_LIMIT_PER_HOUR = 60  # 1 req/sec with API key
    CONFIDENCE_WEIGHT = 0.85
    TIMEOUT_SECONDS = 15

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Shodan connector."""
        super().__init__()
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        self.api_key = api_key

        if not api_key:
            self.logger.warning("No Shodan API key provided - service unavailable")

        self.logger.info("Shodan Connector initialized", has_key=bool(api_key))

    @property
    def source_name(self) -> str:
        """Source identifier."""
        return "Shodan"

    @property
    def source_type(self) -> str:
        """Source classification."""
        return "Device & Service Database"

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
            EntityType.EMAIL_ADDRESS,
            EntityType.COMPANY
        }

    async def search(
        self,
        search_query: Dict[str, Any],
        limit: int = 100
    ) -> SearchResult:
        """
        Search Shodan database.
        
        Query format options:
        {
            "hostname": "example.com",           # Find devices on domain
            "ip": "1.2.3.4",                    # Lookup IP address
            "org": "Company Name",              # Find company infrastructure
            "query": "port:443 ssl:certificate"  # Advanced Shodan query
        }
        """
        result = SearchResult(
            connector_name=self.source_name,
            query=search_query,
            raw_results=[]
        )

        if not self.api_key:
            result.success = False
            result.error_message = "Shodan API key not configured"
            self.logger.error("Shodan search failed: missing API key")
            return result

        try:
            await self._check_rate_limit()

            # Determine search type and execute
            if 'hostname' in search_query:
                devices = await self._search_by_hostname(search_query['hostname'], limit)
            elif 'ip' in search_query:
                devices = await self._lookup_ip(search_query['ip'])
            elif 'org' in search_query:
                devices = await self._search_by_org(search_query['org'], limit)
            elif 'query' in search_query:
                devices = await self._advanced_search(search_query['query'], limit)
            else:
                result.success = False
                result.error_message = "Invalid search parameters"
                return result

            if devices:
                result.success = True
                result.parsed_entities = self._parse_results(devices)
                self.logger.info(
                    "Shodan search successful",
                    device_count=len(devices)
                )
            else:
                result.success = True
                result.parsed_entities = []
                self.logger.debug("Shodan no results found")

        except asyncio.TimeoutError:
            result.success = False
            result.error_message = "Request timeout"
            self.logger.error("Shodan request timeout")

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            self.logger.error("Shodan search failed", error=str(e))

        return result

    async def _search_by_hostname(self, hostname: str, limit: int) -> List[Dict]:
        """Search for devices on a hostname."""
        params = {
            'hostname': hostname,
            'key': self.api_key,
            'limit': min(limit, 100)
        }

        return await self._execute_search('/shodan/host/search', params)

    async def _lookup_ip(self, ip: str) -> Dict:
        """Lookup specific IP address."""
        params = {'key': self.api_key}

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/shodan/host/{ip}"
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        self.logger.debug("IP not found in Shodan", ip=ip)
                        return {}
                    else:
                        self.logger.warning(
                            "Shodan IP lookup failed",
                            ip=ip,
                            status=response.status
                        )
                        return {}

        except Exception as e:
            self.logger.error("Shodan IP lookup error", ip=ip, error=str(e))
            return {}

    async def _search_by_org(self, org: str, limit: int) -> List[Dict]:
        """Search for devices by organization."""
        query = f'org:"{org}"'
        params = {
            'query': query,
            'key': self.api_key,
            'limit': min(limit, 100)
        }

        return await self._execute_search('/shodan/host/search', params)

    async def _advanced_search(self, query: str, limit: int) -> List[Dict]:
        """Execute advanced Shodan query."""
        params = {
            'query': query,
            'key': self.api_key,
            'limit': min(limit, 100)
        }

        return await self._execute_search('/shodan/host/search', params)

    async def _execute_search(
        self,
        endpoint: str,
        params: Dict[str, Any]
    ) -> List[Dict]:
        """Execute search query."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}{endpoint}",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('matches', [])
                    elif response.status == 401:
                        self.logger.error("Shodan authentication failed")
                        return []
                    elif response.status == 429:
                        self.logger.warning("Shodan rate limit hit")
                        return []
                    else:
                        self.logger.warning(
                            "Shodan query failed",
                            status=response.status
                        )
                        return []

        except asyncio.TimeoutError:
            raise

        except Exception as e:
            self.logger.error("Shodan query error", error=str(e))
            return []

    def _parse_results(self, devices: List[Dict]) -> List[Dict[str, Any]]:
        """Parse Shodan results."""
        entities = []

        for device in devices:
            entity = {
                'type': 'internet_device',
                'ip_address': device.get('ip_str'),
                'hostnames': device.get('hostnames', []),
                'ports': device.get('ports', []),
                'services': self._extract_services(device),
                'location': {
                    'country': device.get('country_code'),
                    'country_name': device.get('country_name'),
                    'city': device.get('city'),
                    'latitude': device.get('latitude'),
                    'longitude': device.get('longitude')
                },
                'organization': device.get('org'),
                'isp': device.get('isp'),
                'asn': device.get('asn'),
                'last_update': device.get('last_update'),
                'vulnerabilities': device.get('vulns', []),
                'http_data': self._extract_http_info(device),
                'ssl_certificates': self._extract_ssl_info(device),
                'tags': device.get('tags', []),
                'confidence': self.CONFIDENCE_WEIGHT
            }

            entities.append(entity)
            self.logger.debug(
                "Device found",
                ip=device.get('ip_str'),
                ports=device.get('ports')
            )

        return entities

    def _extract_services(self, device: Dict) -> List[Dict]:
        """Extract service information from device."""
        services = []

        for port in device.get('ports', []):
            # Get data for this port
            port_data = device.get(f'data', [])
            
            service = {
                'port': port,
                'protocol': self._get_protocol(port),
            }

            services.append(service)

        return services

    def _extract_http_info(self, device: Dict) -> Optional[Dict]:
        """Extract HTTP service information."""
        # Look for HTTP data
        for data_item in device.get('data', []):
            if data_item.get('_shodan', {}).get('module') == 'http':
                return {
                    'status': data_item.get('http', {}).get('status'),
                    'title': data_item.get('http', {}).get('title'),
                    'server': data_item.get('http', {}).get('server'),
                    'html_hash': data_item.get('_shodan', {}).get('ptr_records'),
                }

        return None

    def _extract_ssl_info(self, device: Dict) -> List[Dict]:
        """Extract SSL certificate information."""
        certs = []

        for data_item in device.get('data', []):
            if data_item.get('_shodan', {}).get('module') == 'ssl':
                ssl_data = data_item.get('ssl', {})
                cert = {
                    'issuer': ssl_data.get('cert', {}).get('issuer', {}).get('O'),
                    'subject': ssl_data.get('cert', {}).get('subject', {}).get('CN'),
                    'valid_from': ssl_data.get('cert', {}).get('valid', {}).get('from'),
                    'valid_to': ssl_data.get('cert', {}).get('valid', {}).get('to'),
                    'fingerprint': ssl_data.get('fingerprint'),
                }
                certs.append(cert)

        return certs

    @staticmethod
    def _get_protocol(port: int) -> str:
        """Get protocol name for common ports."""
        common_ports = {
            22: 'SSH',
            23: 'Telnet',
            25: 'SMTP',
            53: 'DNS',
            80: 'HTTP',
            110: 'POP3',
            143: 'IMAP',
            443: 'HTTPS',
            445: 'SMB',
            3306: 'MySQL',
            3389: 'RDP',
            5432: 'PostgreSQL',
            5900: 'VNC',
            8080: 'HTTP-Alt',
            8443: 'HTTPS-Alt',
            27017: 'MongoDB',
            6379: 'Redis',
        }
        return common_ports.get(port, 'Unknown')

    async def validate_credentials(self) -> bool:
        """Validate Shodan API key."""
        if not self.api_key:
            self.logger.warning("No Shodan API key provided")
            return False

        try:
            params = {'key': self.api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/api/info",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    is_valid = response.status == 200
                    self.logger.info("Shodan credentials validated", valid=is_valid)
                    return is_valid

        except Exception as e:
            self.logger.error("Shodan credential validation failed", error=str(e))
            return False


def create_connector(api_key: Optional[str] = None) -> ShodanConnector:
    """Create a new Shodan connector instance."""
    return ShodanConnector(api_key=api_key)
