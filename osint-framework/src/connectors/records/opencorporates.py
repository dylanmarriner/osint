"""
OpenCorporates Connector for OSINT Framework

Searches OpenCorporates global company registry for:
- Company registration details and legal information
- Officer and director identification
- Filing history and company changes
- Address and location tracking
- Company relationships and hierarchies

API: https://opencorporates.com/
"""

import asyncio
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
import aiohttp
import structlog

from ..base import SourceConnector, SearchResult, EntityType


class OpenCorporatesConnector(SourceConnector):
    """
    Connector for OpenCorporates global company registry.
    Provides company and director information.
    """

    BASE_URL = "https://api.opencorporates.com/v0.4"
    RATE_LIMIT_PER_HOUR = 500
    CONFIDENCE_WEIGHT = 0.90
    TIMEOUT_SECONDS = 20

    def __init__(self, api_token: Optional[str] = None):
        """Initialize OpenCorporates connector."""
        super().__init__()
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        self.api_token = api_token
        self.session = None
        
        self.logger.info("OpenCorporates Connector initialized", has_credentials=bool(api_token))

    @property
    def source_name(self) -> str:
        """Source identifier."""
        return "OpenCorporates"

    @property
    def source_type(self) -> str:
        """Source classification."""
        return "Global Company Registry"

    def get_rate_limit(self) -> int:
        """Rate limit per hour."""
        return self.RATE_LIMIT_PER_HOUR

    def get_confidence_weight(self) -> float:
        """Confidence weight for this source."""
        return self.CONFIDENCE_WEIGHT

    def get_supported_entity_types(self) -> Set[EntityType]:
        """Entity types this connector can search."""
        return {
            EntityType.COMPANY,
            EntityType.PERSON,
            EntityType.DOMAIN
        }

    async def search(
        self,
        search_query: Dict[str, Any],
        limit: int = 100
    ) -> SearchResult:
        """
        Search OpenCorporates database.
        
        Query format:
        {
            "company_name": "Apple Inc",       # Search by company name
            "company_number": "000123456",     # Search by registration number
            "officer": "John Smith",           # Search by officer/director name
            "address": "1 Infinite Loop",      # Search by address
            "jurisdiction": "us_ca"            # Jurisdiction code
        }
        """
        result = SearchResult(
            connector_name=self.source_name,
            query=search_query,
            raw_results=[]
        )

        try:
            await self.initialize()
            
            if "company_name" in search_query:
                companies = await self._search_companies(
                    search_query["company_name"],
                    jurisdiction=search_query.get("jurisdiction"),
                    limit=limit
                )
                result.raw_results.extend(companies)
                result.success = bool(companies)
            
            elif "company_number" in search_query:
                company = await self._lookup_company(
                    search_query["company_number"],
                    jurisdiction=search_query.get("jurisdiction")
                )
                if company:
                    result.raw_results.append(company)
                    result.success = True
            
            elif "officer" in search_query:
                officers = await self._search_officers(
                    search_query["officer"],
                    limit=limit
                )
                result.raw_results.extend(officers)
                result.success = bool(officers)
            
            elif "address" in search_query:
                companies = await self._search_by_address(
                    search_query["address"],
                    jurisdiction=search_query.get("jurisdiction"),
                    limit=limit
                )
                result.raw_results.extend(companies)
                result.success = bool(companies)
            
            else:
                result.error_message = "Query must contain company_name, company_number, officer, or address"
                result.success = False

            result.result_count = len(result.raw_results)
            self.logger.info(
                "OpenCorporates search completed",
                query=search_query,
                result_count=result.result_count
            )

        except Exception as e:
            result.success = False
            result.error_message = f"OpenCorporates search error: {str(e)}"
            self.logger.error("OpenCorporates search failed", error=str(e))

        return result

    async def _search_companies(
        self,
        company_name: str,
        jurisdiction: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for companies by name."""
        try:
            params = {
                "q": company_name,
                "limit": min(limit, 100),
                "order": "score"
            }
            
            if jurisdiction:
                params["jurisdiction_code"] = jurisdiction
            
            if self.api_token:
                params["api_token"] = self.api_token
            
            url = f"{self.BASE_URL}/companies/search"
            response = await self.make_request(url, "GET", params=params)
            
            if response and "results" in response:
                companies = []
                for company in response.get("results", []):
                    company_data = company.get("company", {})
                    companies.append({
                        "name": company_data.get("name"),
                        "company_number": company_data.get("company_number"),
                        "jurisdiction_code": company_data.get("jurisdiction_code"),
                        "incorporation_date": company_data.get("incorporation_date"),
                        "dissolution_date": company_data.get("dissolution_date"),
                        "company_type": company_data.get("company_type"),
                        "status": company_data.get("status"),
                        "registered_address": company_data.get("registered_address_in_full"),
                        "url": company_data.get("url"),
                        "previous_names": company_data.get("previous_names", []),
                        "raw_data": company_data
                    })
                return companies
            return []
            
        except Exception as e:
            self.logger.error(f"OpenCorporates company search failed", error=str(e))
            return []

    async def _lookup_company(
        self,
        company_number: str,
        jurisdiction: str = "us_ca"
    ) -> Optional[Dict[str, Any]]:
        """Lookup specific company."""
        try:
            params = {}
            if self.api_token:
                params["api_token"] = self.api_token
            
            url = f"{self.BASE_URL}/companies/{jurisdiction}/{company_number}"
            response = await self.make_request(url, "GET", params=params)
            
            if response and "company" in response:
                company = response["company"]
                return {
                    "name": company.get("name"),
                    "company_number": company.get("company_number"),
                    "jurisdiction_code": company.get("jurisdiction_code"),
                    "incorporation_date": company.get("incorporation_date"),
                    "dissolution_date": company.get("dissolution_date"),
                    "company_type": company.get("company_type"),
                    "status": company.get("status"),
                    "registered_address": company.get("registered_address_in_full"),
                    "officers": await self._get_company_officers(company_number, jurisdiction),
                    "filings": company.get("filings", []),
                    "previous_names": company.get("previous_names", []),
                    "raw_data": company
                }
            return None
            
        except Exception as e:
            self.logger.error(f"OpenCorporates company lookup failed", error=str(e))
            return None

    async def _get_company_officers(
        self,
        company_number: str,
        jurisdiction: str
    ) -> List[Dict[str, Any]]:
        """Get officers and directors for a company."""
        try:
            params = {}
            if self.api_token:
                params["api_token"] = self.api_token
            
            url = f"{self.BASE_URL}/companies/{jurisdiction}/{company_number}/officers"
            response = await self.make_request(url, "GET", params=params)
            
            if response and "officers" in response:
                officers = []
                for officer in response["officers"]:
                    officers.append({
                        "name": officer.get("name"),
                        "position": officer.get("position"),
                        "start_date": officer.get("start_date"),
                        "end_date": officer.get("end_date"),
                        "nationality": officer.get("nationality"),
                        "address": officer.get("address"),
                        "raw_data": officer
                    })
                return officers
            return []
            
        except Exception as e:
            self.logger.error(f"OpenCorporates officer lookup failed", error=str(e))
            return []

    async def _search_officers(
        self,
        officer_name: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for officers by name."""
        try:
            params = {
                "q": officer_name,
                "limit": min(limit, 100)
            }
            
            if self.api_token:
                params["api_token"] = self.api_token
            
            url = f"{self.BASE_URL}/officers/search"
            response = await self.make_request(url, "GET", params=params)
            
            if response and "results" in response:
                officers = []
                for result in response.get("results", []):
                    officer = result.get("officer", {})
                    officers.append({
                        "name": officer.get("name"),
                        "position": officer.get("position"),
                        "company_name": officer.get("company_name"),
                        "company_number": officer.get("company_number"),
                        "jurisdiction_code": officer.get("jurisdiction_code"),
                        "address": officer.get("address"),
                        "raw_data": officer
                    })
                return officers
            return []
            
        except Exception as e:
            self.logger.error(f"OpenCorporates officer search failed", error=str(e))
            return []

    async def _search_by_address(
        self,
        address: str,
        jurisdiction: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for companies by address."""
        try:
            params = {
                "q": address,
                "limit": min(limit, 100)
            }
            
            if jurisdiction:
                params["jurisdiction_code"] = jurisdiction
            
            if self.api_token:
                params["api_token"] = self.api_token
            
            url = f"{self.BASE_URL}/companies/search"
            response = await self.make_request(url, "GET", params=params)
            
            if response and "results" in response:
                companies = []
                for company in response.get("results", []):
                    company_data = company.get("company", {})
                    if address.lower() in company_data.get("registered_address_in_full", "").lower():
                        companies.append({
                            "name": company_data.get("name"),
                            "company_number": company_data.get("company_number"),
                            "registered_address": company_data.get("registered_address_in_full"),
                            "jurisdiction_code": company_data.get("jurisdiction_code"),
                            "raw_data": company_data
                        })
                return companies
            return []
            
        except Exception as e:
            self.logger.error(f"OpenCorporates address search failed", error=str(e))
            return []

    async def validate_credentials(self) -> bool:
        """Validate API credentials."""
        try:
            await self.initialize()
            
            # Free tier doesn't require authentication, but test a simple search
            params = {"q": "test", "limit": 1}
            if self.api_token:
                params["api_token"] = self.api_token
            
            url = f"{self.BASE_URL}/companies/search"
            response = await self.make_request(url, "GET", params=params)
            return response is not None
            
        except Exception as e:
            self.logger.error(f"OpenCorporates credential validation failed", error=str(e))
            return False
