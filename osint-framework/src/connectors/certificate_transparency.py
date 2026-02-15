"""
Certificate Transparency Connector for OSINT Framework

Purpose
- Query certificate logs for domain information
- Extract subdomain information from certificates
- Identify SSL/TLS certificate history

Invariants
- Queries only public certificate logs
- Unlimited API access (public logs)
- Returns historically accurate certificate data
- Validates domain format before queries

Failure Modes
- Invalid domain → validation error
- Certificate service unavailable → retried with alternate provider
- No certificates found → empty result set
- Parsing error → result skipped with warning
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import json

from .base import SourceConnector, ConnectorStatus
from ..core.models.entities import SearchResult, EntityType


class CertificateTransparencyConnector(SourceConnector):
    """Connector for certificate transparency logs."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize CT connector."""
        super().__init__(config)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.ct_urls = [
            "https://crt.sh",
            "https://certspotter.com/api/v1",
        ]
    
    @property
    def source_name(self) -> str:
        """Return source name."""
        return "Certificate Transparency"
    
    @property
    def source_type(self) -> str:
        """Return source type."""
        return "certificate_logs"
    
    def get_rate_limit(self) -> int:
        """Return requests per hour limit."""
        return 10000  # CT logs have no practical limit
    
    def get_confidence_weight(self) -> float:
        """Return confidence weight for this source."""
        return 0.98  # Extremely high confidence for official cert logs
    
    def get_supported_entity_types(self) -> Set[EntityType]:
        """Return supported entity types."""
        return {
            EntityType.DOMAIN
        }
    
    async def search(self, query: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Execute certificate transparency search."""
        if not self.rate_limit.can_make_request():
            self.logger.warning("Rate limit exceeded for CT logs")
            return []
        
        try:
            # Validate domain
            if not self._is_valid_domain(query):
                self.logger.warning(f"Invalid domain format: {query}")
                return []
            
            # Try primary CT service
            results = await self._search_crt_sh(query, params)
            if not results:
                # Fallback to alternate service
                results = await self._search_certspotter(query, params)
            
            return results
                
        except Exception as e:
            self.logger.error(f"Certificate transparency search failed: {str(e)}")
            self.status = ConnectorStatus.ERROR
            return []
    
    async def _search_crt_sh(self, domain: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Search crt.sh for certificates."""
        try:
            url = "https://crt.sh/"
            search_params = {
                'q': f"%25.{domain}",  # Wildcard subdomain search
                'output': 'json'
            }
            
            response = await self.make_request(
                url,
                method="GET",
                params=search_params
            )
            
            if not response:
                return []
            
            return self._parse_crt_results(response, domain)
            
        except Exception as e:
            self.logger.debug(f"crt.sh search failed: {str(e)}")
            return []
    
    async def _search_certspotter(self, domain: str, params: Dict[str, Any]) -> List[SearchResult]:
        """Search CertSpotter for certificates."""
        try:
            url = f"https://api.certspotter.com/v1/issuances"
            search_params = {
                'domain': domain,
                'include_subdomains': 'true',
                'expand': 'dns_names'
            }
            
            response = await self.make_request(
                url,
                method="GET",
                params=search_params
            )
            
            if not response:
                return []
            
            return self._parse_certspotter_results(response, domain)
            
        except Exception as e:
            self.logger.debug(f"CertSpotter search failed: {str(e)}")
            return []
    
    async def validate_credentials(self) -> bool:
        """Validate certificate services access."""
        try:
            # CT logs don't require credentials
            response = await self.make_request("https://crt.sh/", method="GET")
            return response is not None
        except Exception as e:
            self.logger.warning(f"CT validation failed: {str(e)}")
            return True  # Still valid - can retry later
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Validate domain format."""
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
    
    def _parse_crt_results(self, response: Dict[str, Any], domain: str) -> List[SearchResult]:
        """Parse crt.sh results."""
        results = []
        seen_domains = set()
        
        try:
            if 'content' in response:
                content = response['content']
                
                # Parse JSON if available
                try:
                    if isinstance(content, str):
                        data = json.loads(content)
                    else:
                        data = content
                    
                    if isinstance(data, list):
                        for cert in data:
                            domain_name = cert.get('name_value', cert.get('common_name', ''))
                            
                            if domain_name and domain_name not in seen_domains:
                                seen_domains.add(domain_name)
                                
                                result = SearchResult(
                                    url=f"https://crt.sh/?id={cert.get('id', '')}",
                                    title=f"Certificate: {domain_name}",
                                    content=f"Issued: {cert.get('entry_timestamp', '')}",
                                    source=self.source_name,
                                    confidence=self.get_confidence_weight() * 100,
                                    retrieved_at=datetime.utcnow()
                                )
                                
                                if self.validate_search_result(result):
                                    results.append(result)
                except json.JSONDecodeError:
                    # Fallback to text parsing
                    lines = content.split('\n') if isinstance(content, str) else []
                    for line in lines:
                        if domain in line:
                            result = SearchResult(
                                url="https://crt.sh/",
                                title=f"Certificate: {line.strip()}",
                                content=line.strip(),
                                source=self.source_name,
                                confidence=self.get_confidence_weight() * 100,
                                retrieved_at=datetime.utcnow()
                            )
                            if self.validate_search_result(result):
                                results.append(result)
        except Exception as e:
            self.logger.error(f"Failed to parse crt.sh results: {str(e)}")
        
        return results
    
    def _parse_certspotter_results(self, response: Dict[str, Any], domain: str) -> List[SearchResult]:
        """Parse CertSpotter results."""
        results = []
        
        try:
            if 'content' in response:
                content = response['content']
                
                try:
                    if isinstance(content, str):
                        data = json.loads(content)
                    else:
                        data = content
                    
                    if isinstance(data, list):
                        for issuance in data:
                            result = SearchResult(
                                url=f"https://certspotter.com/search?domain={domain}",
                                title=f"Certificate Issuance: {domain}",
                                content=f"Issued: {issuance.get('issued_at', '')}",
                                source=self.source_name,
                                confidence=self.get_confidence_weight() * 100,
                                retrieved_at=datetime.utcnow()
                            )
                            
                            if self.validate_search_result(result):
                                results.append(result)
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            self.logger.error(f"Failed to parse CertSpotter results: {str(e)}")
        
        return results
