"""
Wayback Machine Connector for OSINT Framework

Searches the Internet Archive Wayback Machine for historical snapshots
of websites, allowing temporal analysis and historical data recovery.

API: https://archive.org/advancedsearch.php
     https://web.archive.org/web/{timestamp}/{url}
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from urllib.parse import quote

import aiohttp
import structlog

from ..base import SourceConnector, SearchResult, EntityType


class WaybackMachineConnector(SourceConnector):
    """
    Connector for Internet Archive Wayback Machine.
    Retrieves historical snapshots of websites and historical data.
    """

    BASE_URL = "https://archive.org/advancedsearch.php"
    CDX_API_URL = "https://cdx-api.archive.org/v1/snapshot"
    RATE_LIMIT_PER_HOUR = 1200  # 20/min = 1200/hr
    CONFIDENCE_WEIGHT = 0.85
    TIMEOUT_SECONDS = 15

    def __init__(self):
        """Initialize Wayback Machine connector."""
        super().__init__()
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info("Wayback Machine Connector initialized")

    @property
    def source_name(self) -> str:
        """Source identifier."""
        return "Wayback Machine"

    @property
    def source_type(self) -> str:
        """Source classification."""
        return "Web Archive"

    def get_rate_limit(self) -> int:
        """Rate limit per hour."""
        return self.RATE_LIMIT_PER_HOUR

    def get_confidence_weight(self) -> float:
        """Confidence weight for this source."""
        return self.CONFIDENCE_WEIGHT

    def get_supported_entity_types(self) -> Set[EntityType]:
        """Entity types this connector can search."""
        return {EntityType.DOMAIN}

    async def search(
        self,
        search_query: Dict[str, Any],
        limit: int = 100
    ) -> SearchResult:
        """
        Search Wayback Machine for historical snapshots.
        
        Query format:
        {
            "domain": "example.com",
            "start_date": "2010-01-01",  # Optional: YYYY-MM-DD
            "end_date": "2023-12-31"     # Optional: YYYY-MM-DD
        }
        """
        result = SearchResult(
            connector_name=self.source_name,
            query=search_query,
            raw_results=[]
        )

        domain = search_query.get("domain", "").strip()
        if not domain:
            self.logger.warning("Empty domain provided to Wayback Machine search")
            return result

        start_date = search_query.get("start_date")
        end_date = search_query.get("end_date")

        try:
            await self._check_rate_limit()

            snapshots = await self._query_snapshots(domain, start_date, end_date, limit)

            if snapshots:
                result.success = True
                result.parsed_entities = self._parse_results(domain, snapshots)
                self.logger.info(
                    "Wayback Machine search successful",
                    domain=domain,
                    snapshot_count=len(snapshots)
                )
            else:
                result.success = True
                result.parsed_entities = []
                self.logger.debug("Wayback Machine no snapshots found", domain=domain)

        except asyncio.TimeoutError:
            result.success = False
            result.error_message = "Request timeout"
            self.logger.error("Wayback Machine request timeout", domain=domain)

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            self.logger.error("Wayback Machine search failed", domain=domain, error=str(e))

        return result

    async def _query_snapshots(
        self,
        domain: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query Wayback Machine CDX API for snapshots."""
        
        # Prepare domain for CDX API
        url = f"https://{domain}/*"

        params = {
            'url': url,
            'output': 'json',
            'limit': min(limit, 10000),
            'matchType': 'prefix',
            'collapse': 'statuscode'  # Group by HTTP status
        }

        if start_date:
            params['from'] = start_date.replace('-', '')
        if end_date:
            params['to'] = end_date.replace('-', '')

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://cdx-api.archive.org/v1/search",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Data format: [[timestamp, original, status, mime, length, offset, filename], ...]
                        if data and len(data) > 1:
                            return data[1:]  # Skip header row
                    else:
                        self.logger.warning(
                            "Wayback Machine query failed",
                            domain=domain,
                            status=response.status
                        )
                    return []

        except Exception as e:
            self.logger.error("Wayback Machine query error", domain=domain, error=str(e))
            return []

    def _parse_results(
        self,
        domain: str,
        snapshots: List[List]
    ) -> List[Dict[str, Any]]:
        """Parse Wayback Machine CDX API results."""
        entities = []

        for snapshot in snapshots:
            if len(snapshot) < 5:
                continue

            timestamp, original, status_code, mime_type, length = snapshot[:5]

            try:
                snap_date = datetime.strptime(timestamp, '%Y%m%d%H%M%S')
            except (ValueError, TypeError):
                self.logger.warning("Failed to parse timestamp", timestamp=timestamp)
                snap_date = None

            entity = {
                'type': 'wayback_snapshot',
                'domain': domain,
                'original_url': original,
                'timestamp': timestamp,
                'snapshot_date': snap_date.isoformat() if snap_date else None,
                'http_status': int(status_code),
                'mime_type': mime_type,
                'content_length': int(length) if length else None,
                'wayback_url': f"https://web.archive.org/web/{timestamp}/{original}",
                'confidence': self.CONFIDENCE_WEIGHT
            }

            entities.append(entity)
            self.logger.debug(
                "Wayback snapshot found",
                domain=domain,
                date=timestamp,
                status=status_code
            )

        return entities

    async def validate_credentials(self) -> bool:
        """Validate service availability."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://archive.org/advancedsearch.php",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    is_available = response.status == 200
                    self.logger.info("Wayback Machine availability check", available=is_available)
                    return is_available

        except Exception as e:
            self.logger.error("Wayback Machine availability check failed", error=str(e))
            return False


class WaybackScreenshotsConnector(SourceConnector):
    """
    Connector for Wayback Machine screenshots and page analysis.
    Analyzes how pages changed over time.
    """

    RATE_LIMIT_PER_HOUR = 600
    CONFIDENCE_WEIGHT = 0.80

    def __init__(self):
        """Initialize Wayback screenshots connector."""
        super().__init__()
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

    @property
    def source_name(self) -> str:
        return "Wayback Machine Screenshots"

    @property
    def source_type(self) -> str:
        return "Web Archive Visualization"

    def get_rate_limit(self) -> int:
        return self.RATE_LIMIT_PER_HOUR

    def get_confidence_weight(self) -> float:
        return self.CONFIDENCE_WEIGHT

    def get_supported_entity_types(self) -> Set[EntityType]:
        return {EntityType.DOMAIN}

    async def search(
        self,
        search_query: Dict[str, Any],
        limit: int = 100
    ) -> SearchResult:
        """
        Get screenshot information from Wayback Machine.
        """
        result = SearchResult(
            connector_name=self.source_name,
            query=search_query,
            raw_results=[]
        )

        domain = search_query.get("domain", "").strip()
        if not domain:
            return result

        try:
            # Get available screenshots
            screenshots = await self._get_available_screenshots(domain, limit)

            if screenshots:
                result.success = True
                result.parsed_entities = screenshots
                self.logger.info(
                    "Screenshots retrieved",
                    domain=domain,
                    count=len(screenshots)
                )
            else:
                result.success = True
                result.parsed_entities = []

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            self.logger.error("Screenshot retrieval failed", domain=domain, error=str(e))

        return result

    async def _get_available_screenshots(self, domain: str, limit: int) -> List[Dict]:
        """Get available screenshot thumbnails."""
        entities = []

        # Wayback Machine provides screenshots for major snapshots
        # Get major captures (roughly yearly)
        params = {
            'url': domain,
            'matchType': 'domain',
            'output': 'json',
            'collapse': 'statuscode',
            'filter': 'statuscode:200',
            'limit': min(limit, 365)
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://cdx-api.archive.org/v1/search",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Get representative snapshots
                        if data and len(data) > 1:
                            snapshots = data[1:]
                            # Select every nth snapshot for screenshots (to avoid too many)
                            step = max(1, len(snapshots) // limit)
                            
                            for snapshot in snapshots[::step][:limit]:
                                 if len(snapshot) >= 1:
                                     timestamp = snapshot[0]
                                     # Generate actual screenshot URL with proper format
                                     snapshot_url = f"https://web.archive.org/web/{timestamp}/{domain}"
                                     # Construct thumbnail URL from Wayback Machine API
                                     # The thumbnail is typically available for successful captures
                                     thumbnail_url = f"https://web.archive.org/web/{timestamp}id_/{domain}/"
                                     
                                     entity = {
                                         'type': 'wayback_screenshot',
                                         'domain': domain,
                                         'timestamp': timestamp,
                                         'screenshot_url': snapshot_url,
                                         'thumbnail_url': thumbnail_url,
                                         'confidence': self.CONFIDENCE_WEIGHT,
                                         'metadata': {
                                             'availability_url': f"https://web.archive.org/web/{timestamp}*/{domain}/"
                                         }
                                     }
                                     entities.append(entity)

        except Exception as e:
            self.logger.error("Screenshot query error", domain=domain, error=str(e))

        return entities

    async def validate_credentials(self) -> bool:
        return True  # No credentials needed


def create_wayback_connector() -> WaybackMachineConnector:
    """Create a Wayback Machine connector instance."""
    return WaybackMachineConnector()


def create_screenshots_connector() -> WaybackScreenshotsConnector:
    """Create a Wayback Screenshots connector instance."""
    return WaybackScreenshotsConnector()
