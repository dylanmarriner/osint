"""
Certificate Transparency Reconnaissance — Free, No API Key

Queries crt.sh (public CT log aggregator) via HTTPS to discover
subdomains, certificate timelines, and issuer information.

Free data source:
- crt.sh (Sectigo CT log search, public HTTPS, no rate limit key)
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class CertEntry:
    id: int = 0
    issuer_name: str = ""
    common_name: str = ""
    name_value: str = ""  # SAN entries
    not_before: str = ""
    not_after: str = ""
    serial_number: str = ""
    entry_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "issuer": self.issuer_name,
            "common_name": self.common_name,
            "san": self.name_value,
            "not_before": self.not_before,
            "not_after": self.not_after,
            "serial_number": self.serial_number,
        }


@dataclass
class CertReport:
    domain: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    certificates: List[CertEntry] = field(default_factory=list)
    unique_subdomains: List[str] = field(default_factory=list)
    unique_issuers: List[str] = field(default_factory=list)
    wildcard_certs: int = 0
    expired_certs: int = 0
    total_certs: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "timestamp": self.timestamp.isoformat(),
            "total_certs": self.total_certs,
            "unique_subdomains": self.unique_subdomains,
            "subdomain_count": len(self.unique_subdomains),
            "unique_issuers": self.unique_issuers,
            "wildcard_certs": self.wildcard_certs,
            "expired_certs": self.expired_certs,
            "certificates": [c.to_dict() for c in self.certificates[:100]],  # Cap at 100
            "errors": self.errors,
        }


class CertRecon:
    """Certificate Transparency recon via crt.sh — public, free, no API key."""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self.base_url = "https://crt.sh"
        self.logger = logging.getLogger(f"{__name__}.CertRecon")

    async def search(self, domain: str, include_expired: bool = True,
                     progress_callback=None) -> CertReport:
        """Search crt.sh for certificates matching a domain."""
        report = CertReport(domain=domain)

        if progress_callback:
            progress_callback("Cert Transparency: Querying crt.sh", 10)

        try:
            url = f"{self.base_url}/?q=%.{domain}&output=json"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout),
                                       headers={"User-Agent": "OSINT-Framework/2.0"}) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        await self._process_results(data, report, domain)
                    else:
                        report.errors.append(f"crt.sh returned status {resp.status}")
        except asyncio.TimeoutError:
            report.errors.append("crt.sh query timed out")
        except Exception as e:
            report.errors.append(f"crt.sh query failed: {str(e)}")
            self.logger.warning(f"crt.sh failed for {domain}: {e}")

        if progress_callback:
            progress_callback("Cert Transparency: Complete", 100)

        return report

    async def _process_results(self, data: List[Dict], report: CertReport, domain: str):
        """Process crt.sh JSON results."""
        subdomains: Set[str] = set()
        issuers: Set[str] = set()
        seen_serials: Set[str] = set()
        now = datetime.utcnow()

        for entry in data or []:
            serial = str(entry.get("serial_number", ""))
            if serial in seen_serials:
                continue
            seen_serials.add(serial)

            cert = CertEntry(
                id=entry.get("id", 0),
                issuer_name=entry.get("issuer_name", ""),
                common_name=entry.get("common_name", ""),
                name_value=entry.get("name_value", ""),
                not_before=entry.get("not_before", ""),
                not_after=entry.get("not_after", ""),
                serial_number=serial,
                entry_timestamp=entry.get("entry_timestamp", ""),
            )
            report.certificates.append(cert)

            # Extract subdomains from name_value (SAN field)
            for name in cert.name_value.split("\n"):
                name = name.strip().lower()
                if name and name.endswith(f".{domain.lower()}"):
                    if not name.startswith("*"):
                        subdomains.add(name)
                elif name == domain.lower():
                    subdomains.add(name)

                if name.startswith("*."):
                    report.wildcard_certs += 1

            # Issuer tracking
            if cert.issuer_name:
                # Extract O= from issuer name
                for part in cert.issuer_name.split(","):
                    part = part.strip()
                    if part.startswith("O="):
                        issuers.add(part[2:])
                        break

            # Check expiry
            try:
                expiry = datetime.strptime(cert.not_after, "%Y-%m-%dT%H:%M:%S")
                if expiry < now:
                    report.expired_certs += 1
            except (ValueError, TypeError):
                pass

        report.unique_subdomains = sorted(subdomains)
        report.unique_issuers = sorted(issuers)
        report.total_certs = len(report.certificates)
