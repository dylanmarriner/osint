"""
SEC EDGAR Connector for OSINT Framework

Searches SEC EDGAR (Electronic Data Gathering) for:
- Corporate filings and financial statements
- Executive names, titles, and compensation
- Insider ownership information
- Business segment details
- Risk factors and strategic information

API: https://www.sec.gov/cgi-bin/browse-edgar
"""

import asyncio
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime

import aiohttp
import structlog

from ..base import SourceConnector, SearchResult, EntityType


class SECEDGARConnector(SourceConnector):
    """
    Connector for SEC EDGAR corporate filing database.
    Extracts information from 10-K, 10-Q, 8-K, DEF 14A filings.
    """

    BASE_URL = "https://www.sec.gov/cgi-bin/browse-edgar"
    API_URL = "https://www.sec.gov/files/company_tickers.json"
    RATE_LIMIT_PER_HOUR = 10000  # Unlimited (public API)
    CONFIDENCE_WEIGHT = 0.98  # Official government source
    TIMEOUT_SECONDS = 20

    def __init__(self):
        """Initialize SEC EDGAR connector."""
        super().__init__()
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info("SEC EDGAR Connector initialized")

    @property
    def source_name(self) -> str:
        """Source identifier."""
        return "SEC EDGAR"

    @property
    def source_type(self) -> str:
        """Source classification."""
        return "Corporate Filing Database"

    def get_rate_limit(self) -> int:
        """Rate limit per hour."""
        return self.RATE_LIMIT_PER_HOUR

    def get_confidence_weight(self) -> float:
        """Confidence weight for this source."""
        return self.CONFIDENCE_WEIGHT

    def get_supported_entity_types(self) -> Set[EntityType]:
        """Entity types this connector can search."""
        return {EntityType.COMPANY}

    async def search(
        self,
        search_query: Dict[str, Any],
        limit: int = 100
    ) -> SearchResult:
        """
        Search SEC EDGAR filings.
        
        Query format:
        {
            "company_name": "Apple Inc",    # Search by company name
            "ticker": "AAPL",               # Search by stock ticker
            "cik": "0000320193",            # Search by CIK number
            "filing_type": "10-K"           # 10-K, 10-Q, 8-K, DEF 14A
        }
        """
        result = SearchResult(
            connector_name=self.source_name,
            query=search_query,
            raw_results=[]
        )

        company_id = None

        # Resolve company identifier
        if 'cik' in search_query:
            company_id = search_query['cik']
        elif 'ticker' in search_query:
            company_id = await self._resolve_ticker(search_query['ticker'])
        elif 'company_name' in search_query:
            company_id = await self._resolve_company_name(search_query['company_name'])

        if not company_id:
            result.success = False
            result.error_message = "Could not resolve company"
            return result

        try:
            await self._check_rate_limit()

            filing_type = search_query.get('filing_type', '10-K')
            filings = await self._search_filings(company_id, filing_type, limit)

            if filings:
                result.success = True
                result.parsed_entities = await self._parse_filings(company_id, filings)
                self.logger.info(
                    "SEC EDGAR search successful",
                    company_id=company_id,
                    filing_count=len(filings)
                )
            else:
                result.success = True
                result.parsed_entities = []
                self.logger.debug("SEC EDGAR no filings found", company_id=company_id)

        except asyncio.TimeoutError:
            result.success = False
            result.error_message = "Request timeout"
            self.logger.error("SEC EDGAR request timeout")

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            self.logger.error("SEC EDGAR search failed", error=str(e))

        return result

    async def _resolve_ticker(self, ticker: str) -> Optional[str]:
        """Resolve stock ticker to CIK."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.API_URL,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        # data is {index: {cik_str, ticker, title}}
                        for entry in data.values():
                            if entry.get('ticker', '').upper() == ticker.upper():
                                return str(entry.get('cik_str')).zfill(10)

        except Exception as e:
            self.logger.error("Ticker resolution failed", ticker=ticker, error=str(e))

        return None

    async def _resolve_company_name(self, company_name: str) -> Optional[str]:
        """Resolve company name to CIK."""
        params = {
            'company': company_name,
            'owner': 'exclude',
            'action': 'getcompany',
            'format': 'json'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('cik_lookup'):
                            cik = data['cik_lookup'].get('CIK_str')
                            return str(cik).zfill(10) if cik else None

        except Exception as e:
            self.logger.error("Company name resolution failed", name=company_name, error=str(e))

        return None

    async def _search_filings(
        self,
        cik: str,
        filing_type: str,
        limit: int
    ) -> List[Dict]:
        """Search for specific filing types."""
        params = {
            'action': 'getcompany',
            'CIK': cik,
            'type': filing_type,
            'dateb': '',
            'owner': 'exclude',
            'count': min(limit, 100),
            'format': 'json'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('filings', {}).get('filing', [])
                    else:
                        self.logger.warning(
                            "SEC EDGAR filing search failed",
                            cik=cik,
                            status=response.status
                        )
                        return []

        except Exception as e:
            self.logger.error("SEC EDGAR filing search error", cik=cik, error=str(e))
            return []

    async def _parse_filings(
        self,
        cik: str,
        filings: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Parse SEC filing data."""
        entities = []

        for filing in filings:
            entity = {
                'type': 'sec_filing',
                'cik': cik,
                'form_type': filing.get('form'),
                'date_filed': filing.get('filingDate'),
                'accession_number': filing.get('accessionNumber'),
                'filing_url': f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={cik}&accession_number={filing.get('accessionNumber')}&xbrl_type=v",
                'document_url': f"https://www.sec.gov/Archives/{filing.get('href')}",
                'confidence': self.CONFIDENCE_WEIGHT,
                'metadata': {
                    'film_number': filing.get('filmNumber'),
                    'size': filing.get('fileNum'),
                }
            }

            # Try to extract key information based on form type
            if filing.get('form') == '10-K':
                entity['form_details'] = {
                    'annual_report': True,
                    'fiscal_year': self._extract_fiscal_year(filing.get('filingDate')),
                    'content_types': ['executives', 'financials', 'risks', 'business_description']
                }
            elif filing.get('form') == 'DEF 14A':
                entity['form_details'] = {
                    'proxy_statement': True,
                    'content_types': ['executive_compensation', 'board_members', 'voting_matters']
                }
            elif filing.get('form') == '8-K':
                entity['form_details'] = {
                    'current_report': True,
                    'material_events': True
                }

            entities.append(entity)
            self.logger.debug(
                "SEC filing found",
                cik=cik,
                form=filing.get('form'),
                date=filing.get('filingDate')
            )

        return entities

    @staticmethod
    def _extract_fiscal_year(date_str: Optional[str]) -> Optional[int]:
        """Extract fiscal year from filing date."""
        if not date_str:
            return None
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.year
        except (ValueError, TypeError):
            return None

    async def validate_credentials(self) -> bool:
        """Validate service availability."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.API_URL,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    is_available = response.status == 200
                    self.logger.info("SEC EDGAR availability check", available=is_available)
                    return is_available

        except Exception as e:
            self.logger.error("SEC EDGAR availability check failed", error=str(e))
            return False


def create_connector() -> SECEDGARConnector:
    """Create a new SEC EDGAR connector instance."""
    return SECEDGARConnector()
