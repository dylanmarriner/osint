"""
Crunchbase Connector for OSINT Framework

Searches Crunchbase startup database for:
- Startup funding rounds (seed, series A-Z, IPO, acquisition)
- Founder and team member information
- Investor networks and participation
- Company valuation and financials
- Investment history and timeline
- Company relationships and acquisitions

API: https://www.crunchbase.com/
"""

import asyncio
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
import aiohttp
import structlog

from ..base import SourceConnector, SearchResult, EntityType


class CrunchbaseConnector(SourceConnector):
    """
    Connector for Crunchbase startup and investment database.
    Provides funding and company relationship data.
    """

    BASE_URL = "https://api.crunchbase.com/v3.1"
    RATE_LIMIT_PER_HOUR = 300
    CONFIDENCE_WEIGHT = 0.85
    TIMEOUT_SECONDS = 20

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Crunchbase connector."""
        super().__init__()
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        self.api_key = api_key
        self.session = None
        
        self.logger.info("Crunchbase Connector initialized", has_credentials=bool(api_key))

    @property
    def source_name(self) -> str:
        """Source identifier."""
        return "Crunchbase"

    @property
    def source_type(self) -> str:
        """Source classification."""
        return "Startup Funding & Investment Database"

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
        Search Crunchbase database.
        
        Query format:
        {
            "company_name": "Stripe",          # Search by company name
            "founder": "Patrick Collison",     # Search by founder name
            "investor": "Y Combinator",        # Search by investor name
            "domain": "stripe.com",            # Search by company domain
            "funding_stage": "Series B"        # Search by funding stage
        }
        """
        result = SearchResult(
            connector_name=self.source_name,
            query=search_query,
            raw_results=[]
        )

        if not self.api_key:
            # Allow limited searches without API key
            self.logger.warning("Crunchbase API key not configured, using limited search")

        try:
            await self.initialize()
            
            if "company_name" in search_query:
                companies = await self._search_companies(
                    search_query["company_name"],
                    limit=limit
                )
                result.raw_results.extend(companies)
                result.success = bool(companies)
            
            elif "founder" in search_query:
                people = await self._search_people(
                    search_query["founder"],
                    role="founder",
                    limit=limit
                )
                result.raw_results.extend(people)
                result.success = bool(people)
            
            elif "investor" in search_query:
                investors = await self._search_investors(
                    search_query["investor"],
                    limit=limit
                )
                result.raw_results.extend(investors)
                result.success = bool(investors)
            
            elif "domain" in search_query:
                companies = await self._search_by_domain(
                    search_query["domain"]
                )
                if companies:
                    result.raw_results.append(companies)
                    result.success = True
            
            else:
                result.error_message = "Query must contain company_name, founder, investor, or domain"
                result.success = False

            result.result_count = len(result.raw_results)
            self.logger.info(
                "Crunchbase search completed",
                query=search_query,
                result_count=result.result_count
            )

        except Exception as e:
            result.success = False
            result.error_message = f"Crunchbase search error: {str(e)}"
            self.logger.error("Crunchbase search failed", error=str(e))

        return result

    async def _search_companies(
        self,
        company_name: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for companies."""
        try:
            if not self.api_key:
                return []
            
            url = f"{self.BASE_URL}/companies"
            params = {
                "api_key": self.api_key,
                "name": company_name,
                "limit": min(limit, 100)
            }
            
            response = await self.make_request(url, "GET", params=params)
            
            if response and "entities" in response:
                companies = []
                for entity in response["entities"][:limit]:
                    company_data = entity.get("entity", {})
                    companies.append({
                        "uuid": company_data.get("uuid"),
                        "name": company_data.get("name"),
                        "domain": company_data.get("domain"),
                        "founded_on": company_data.get("founded_on"),
                        "status": company_data.get("status"),
                        "country_code": company_data.get("country_code"),
                        "city": company_data.get("city"),
                        "description": company_data.get("description"),
                        "logo_url": company_data.get("logo_url"),
                        "total_funding": company_data.get("total_funding_usd"),
                        "funding_stage": company_data.get("last_funding_type"),
                        "employee_count": company_data.get("employee_count"),
                        "raw_data": company_data
                    })
                return companies
            return []
            
        except Exception as e:
            self.logger.error(f"Crunchbase company search failed", error=str(e))
            return []

    async def _search_people(
        self,
        person_name: str,
        role: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for people (founders, executives, investors)."""
        try:
            if not self.api_key:
                return []
            
            url = f"{self.BASE_URL}/people"
            params = {
                "api_key": self.api_key,
                "name": person_name,
                "limit": min(limit, 100)
            }
            
            if role:
                params["role"] = role
            
            response = await self.make_request(url, "GET", params=params)
            
            if response and "entities" in response:
                people = []
                for entity in response["entities"][:limit]:
                    person_data = entity.get("entity", {})
                    people.append({
                        "uuid": person_data.get("uuid"),
                        "name": person_data.get("name"),
                        "title": person_data.get("title"),
                        "country_code": person_data.get("country_code"),
                        "bio": person_data.get("bio"),
                        "profile_image_url": person_data.get("profile_image_url"),
                        "facebook_url": person_data.get("facebook_url"),
                        "linkedin_url": person_data.get("linkedin_url"),
                        "twitter_url": person_data.get("twitter_url"),
                        "primary_affiliation": person_data.get("primary_affiliation"),
                        "raw_data": person_data
                    })
                return people
            return []
            
        except Exception as e:
            self.logger.error(f"Crunchbase people search failed", error=str(e))
            return []

    async def _search_investors(
        self,
        investor_name: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for investors."""
        try:
            if not self.api_key:
                return []
            
            url = f"{self.BASE_URL}/investors"
            params = {
                "api_key": self.api_key,
                "name": investor_name,
                "limit": min(limit, 100)
            }
            
            response = await self.make_request(url, "GET", params=params)
            
            if response and "entities" in response:
                investors = []
                for entity in response["entities"][:limit]:
                    investor_data = entity.get("entity", {})
                    investors.append({
                        "uuid": investor_data.get("uuid"),
                        "name": investor_data.get("name"),
                        "type": investor_data.get("investor_type"),
                        "country_code": investor_data.get("country_code"),
                        "city": investor_data.get("city"),
                        "founded_on": investor_data.get("founded_on"),
                        "total_investments": investor_data.get("num_investments"),
                        "total_portfolio_value": investor_data.get("total_portfolio_value_usd"),
                        "description": investor_data.get("description"),
                        "website": investor_data.get("website_url"),
                        "raw_data": investor_data
                    })
                return investors
            return []
            
        except Exception as e:
            self.logger.error(f"Crunchbase investor search failed", error=str(e))
            return []

    async def _search_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """Search for company by domain."""
        try:
            if not self.api_key:
                return None
            
            url = f"{self.BASE_URL}/organizations"
            params = {
                "api_key": self.api_key,
                "domain_name": domain
            }
            
            response = await self.make_request(url, "GET", params=params)
            
            if response and "entities" in response and len(response["entities"]) > 0:
                company_data = response["entities"][0].get("entity", {})
                
                # Fetch funding rounds
                funding_rounds = await self._get_funding_rounds(company_data.get("uuid"))
                
                return {
                    "uuid": company_data.get("uuid"),
                    "name": company_data.get("name"),
                    "domain": company_data.get("domain"),
                    "founded_on": company_data.get("founded_on"),
                    "status": company_data.get("status"),
                    "country_code": company_data.get("country_code"),
                    "city": company_data.get("city"),
                    "total_funding": company_data.get("total_funding_usd"),
                    "funding_rounds": funding_rounds,
                    "founders": await self._get_company_founders(company_data.get("uuid")),
                    "raw_data": company_data
                }
            return None
            
        except Exception as e:
            self.logger.error(f"Crunchbase domain search failed", error=str(e))
            return None

    async def _get_funding_rounds(self, company_uuid: str) -> List[Dict[str, Any]]:
        """Get funding rounds for a company."""
        try:
            if not self.api_key:
                return []
            
            url = f"{self.BASE_URL}/organizations/{company_uuid}/funding_rounds"
            params = {"api_key": self.api_key}
            
            response = await self.make_request(url, "GET", params=params)
            
            if response and "funding_rounds" in response:
                rounds = []
                for round_data in response["funding_rounds"]:
                    rounds.append({
                        "uuid": round_data.get("uuid"),
                        "type": round_data.get("funding_type"),
                        "announced_on": round_data.get("announced_on"),
                        "closed_on": round_data.get("closed_on"),
                        "money_raised_usd": round_data.get("money_raised_usd"),
                        "investor_count": round_data.get("investor_count"),
                        "investors": round_data.get("investors", []),
                        "raw_data": round_data
                    })
                return rounds
            return []
            
        except Exception as e:
            self.logger.error(f"Crunchbase funding rounds fetch failed", error=str(e))
            return []

    async def _get_company_founders(self, company_uuid: str) -> List[Dict[str, Any]]:
        """Get founders of a company."""
        try:
            if not self.api_key:
                return []
            
            url = f"{self.BASE_URL}/organizations/{company_uuid}/founders"
            params = {"api_key": self.api_key}
            
            response = await self.make_request(url, "GET", params=params)
            
            if response and "founders" in response:
                founders = []
                for founder_data in response["founders"]:
                    founders.append({
                        "uuid": founder_data.get("uuid"),
                        "name": founder_data.get("name"),
                        "title": founder_data.get("title"),
                        "profile_url": founder_data.get("profile_url"),
                        "raw_data": founder_data
                    })
                return founders
            return []
            
        except Exception as e:
            self.logger.error(f"Crunchbase founders fetch failed", error=str(e))
            return []

    async def validate_credentials(self) -> bool:
        """Validate API credentials."""
        if not self.api_key:
            return False
        
        try:
            await self.initialize()
            
            url = f"{self.BASE_URL}/organizations"
            params = {
                "api_key": self.api_key,
                "name": "test",
                "limit": 1
            }
            
            response = await self.make_request(url, "GET", params=params)
            return response is not None
            
        except Exception as e:
            self.logger.error(f"Crunchbase credential validation failed", error=str(e))
            return False
