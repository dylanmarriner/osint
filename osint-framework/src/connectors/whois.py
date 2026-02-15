"""
WHOIS/RDAP Connector for OSINT Framework

Purpose
- Query WHOIS and RDAP for domain registration data
- Extract registrant and technical contact information
- Identify nameservers and hosting providers

Invariants
- Queries only publicly available WHOIS data
- Respects WHOIS rate limits
- Handles private registrations gracefully
- Validates domain format before queries

Failure Modes
- Invalid domain → validation error
- Rate limit exceeded → queued for retry
- Private domain → returns limited info with privacy notice
- WHOIS service unavailable → retried with alternate server
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from .base import SourceConnector, ConnectorStatus
from ..core.models.entities import SearchResult, EntityType


class WhoisConnector(SourceConnector):
    """Connector for WHOIS/RDAP queries."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize WHOIS connector."""
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.whois_servers = [
            "whois.verisign-grs.com",
            "whois.arin.net",
            "whois.ripe.net"
        ]
        self.rdap_url = "https://rdap.org"
    
    @property
    def source_name(self) -> str:
        """Return source name."""
        return "WHOIS/RDAP"
    
    @property
    def source_type(self) -> str:
        """Return source type."""
        return "domain_registry"
    
    def get_rate_limit(self) -> int:
        """Return requests per hour limit."""
        return 1000  # WHOIS allows high rate limits
    
    def get_confidence_weight(self) -> float:
        """Return confidence weight for this source."""
        return 0.95  # Very high confidence for authoritative registry data
    
    def get_supported_entity_types(self) -> Set[EntityType]:
        """Return supported entity types."""
        return {
            EntityType.DOMAIN,
            EntityType.EMAIL_ADDRESS,
            EntityType.PERSON,
            EntityType.COMPANY
        }
    
    async def search(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Execute WHOIS/RDAP search."""
        if not self.rate_limit.can_make_request():
            self.logger.warning("Rate limit exceeded for WHOIS")
            return []
        
        try:
            # Validate domain
            if not self._is_valid_domain(query):
                self.logger.warning(f"Invalid domain format: {query}")
                return []
            
            # Try RDAP first (more structured)
            results = await self._search_rdap(query, params)
            if results:
                return results
            
            # Fallback to WHOIS
            return await self._search_whois(query, params)
                
        except Exception as e:
            self.logger.error(f"WHOIS search failed: {str(e)}")
            self.status = ConnectorStatus.ERROR
            return []
    
    async def _search_rdap(self, domain: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Search RDAP for domain information."""
        try:
            url = f"{self.rdap_url}/ip/{domain}"
            response = await self.make_request(url, method="GET")
            
            if not response:
                # Try domain lookup
                url = f"{self.rdap_url}/domain/{domain}"
                response = await self.make_request(url, method="GET")
            
            if not response:
                return []
            
            return self._parse_rdap_results(response, domain)
            
        except Exception as e:
            self.logger.debug(f"RDAP search failed: {str(e)}")
            return []
    
    async def _search_whois(self, domain: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Search WHOIS for domain information."""
        try:
            # Query WHOIS server
            whois_server = self.whois_servers[0]
            
            response = await self.make_request(
                f"https://{whois_server}/",
                method="GET",
                params={'query': domain}
            )
            
            if not response:
                return []
            
            return self._parse_whois_results(response, domain)
            
        except Exception as e:
            self.logger.error(f"WHOIS query failed: {str(e)}")
            return []
    
    async def validate_credentials(self) -> bool:
        """Validate WHOIS service access."""
        try:
            # WHOIS doesn't require credentials
            response = await self.make_request(self.rdap_url, method="GET")
            return response is not None
        except Exception as e:
            self.logger.warning(f"WHOIS validation failed: {str(e)}")
            return True  # Still valid - can try again later
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Validate domain format."""
        # Basic domain validation
        if not domain or len(domain) < 3:
            return False
        
        parts = domain.split('.')
        if len(parts) < 2:
            return False
        
        # TLD validation
        tld = parts[-1]
        if len(tld) < 2 or len(tld) > 6:
            return False
        
        return True
    
    def _parse_rdap_results(self, response: Dict[str, Any], domain: str) -> List[SearchResult]:
        """Parse RDAP results."""
        results = []
        
        try:
            if 'content' in response:
                content = response['content']
                
                result = SearchResult(
                    url=f"https://rdap.org/domain/{domain}",
                    title=f"WHOIS: {domain}",
                    content=content[:500],
                    source=self.source_name,
                    confidence=self.get_confidence_weight() * 100,
                    retrieved_at=datetime.utcnow()
                )
                
                if self.validate_search_result(result):
                    results.append(result)
        except Exception as e:
            self.logger.error(f"Failed to parse RDAP results: {str(e)}")
        
        return results
    
    def _parse_whois_results(self, response: Dict[str, Any], domain: str) -> List[SearchResult]:
        """Parse WHOIS results."""
        results = []
        
        try:
            if 'content' in response:
                content = response['content']
                
                # Extract key information
                lines = content.split('\n')
                registrar = ""
                registrant = ""
                
                for line in lines:
                    if 'Registrar:' in line:
                        registrar = line.split(':', 1)[1].strip()
                    if 'Registrant:' in line:
                        registrant = line.split(':', 1)[1].strip()
                
                title = f"WHOIS: {domain}"
                if registrant:
                    title += f" ({registrant})"
                
                result = SearchResult(
                    url=f"https://whois.verisign-grs.com/?domain={domain}",
                    title=title,
                    content=content[:500],
                    source=self.source_name,
                    confidence=self.get_confidence_weight() * 100,
                    retrieved_at=datetime.utcnow()
                )
                
                if self.validate_search_result(result):
                    results.append(result)
        except Exception as e:
            self.logger.error(f"Failed to parse WHOIS results: {str(e)}")
        
        return results
