"""
WHOIS Reconnaissance Module — No API Keys Required

Performs WHOIS lookups using direct protocol queries and free public APIs.
Extracts registration data, contacts, and network ownership.

Free data sources:
- Direct WHOIS protocol (port 43)
- ip-api.com (free, 45 req/min) for IP geolocation
- ipinfo.io/widget (free, no key for basic data)
"""

import asyncio
import socket
import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

try:
    import whois as python_whois
    HAS_WHOIS = True
except ImportError:
    HAS_WHOIS = False

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class WhoisData:
    domain: str
    registrar: Optional[str] = None
    creation_date: Optional[str] = None
    expiration_date: Optional[str] = None
    updated_date: Optional[str] = None
    status: List[str] = field(default_factory=list)
    nameservers: List[str] = field(default_factory=list)
    registrant: Dict[str, str] = field(default_factory=dict)
    admin_contact: Dict[str, str] = field(default_factory=dict)
    tech_contact: Dict[str, str] = field(default_factory=dict)
    dnssec: Optional[str] = None
    raw_text: str = ""
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "registrar": self.registrar,
            "creation_date": self.creation_date,
            "expiration_date": self.expiration_date,
            "updated_date": self.updated_date,
            "status": self.status,
            "nameservers": self.nameservers,
            "registrant": self.registrant,
            "admin_contact": self.admin_contact,
            "tech_contact": self.tech_contact,
            "dnssec": self.dnssec,
            "errors": self.errors,
        }


@dataclass
class IPInfo:
    ip: str
    hostname: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    org: Optional[str] = None
    asn: Optional[str] = None
    isp: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    timezone: Optional[str] = None
    reverse_dns: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != []}


class WhoisRecon:
    """WHOIS and IP intelligence — free, no API keys required."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.WhoisRecon")

    async def domain_whois(self, domain: str) -> WhoisData:
        """Perform WHOIS lookup on a domain."""
        data = WhoisData(domain=domain)

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._sync_whois, domain
            )
            if result:
                data.registrar = self._safe_str(result.get("registrar"))
                data.creation_date = self._format_date(result.get("creation_date"))
                data.expiration_date = self._format_date(result.get("expiration_date"))
                data.updated_date = self._format_date(result.get("updated_date"))
                data.dnssec = self._safe_str(result.get("dnssec"))

                # Status
                status = result.get("status")
                if isinstance(status, list):
                    data.status = [str(s) for s in status]
                elif status:
                    data.status = [str(status)]

                # Nameservers
                ns = result.get("name_servers")
                if isinstance(ns, (list, set)):
                    data.nameservers = [str(n).lower() for n in ns]
                elif ns:
                    data.nameservers = [str(ns).lower()]

                # Contacts
                for prefix, target in [("registrant", data.registrant),
                                        ("admin", data.admin_contact),
                                        ("tech", data.tech_contact)]:
                    for suffix in ["name", "organization", "email", "country", "state", "city"]:
                        key = f"{prefix}_{suffix}" if prefix != "registrant" else suffix
                        val = result.get(key)
                        if val:
                            target[suffix] = self._safe_str(val)

                data.raw_text = str(result.text) if hasattr(result, "text") else ""

        except Exception as e:
            data.errors.append(f"WHOIS lookup failed: {str(e)}")
            self.logger.warning(f"WHOIS failed for {domain}: {e}")

        return data

    def _sync_whois(self, domain: str):
        if not HAS_WHOIS:
            raise ImportError("python-whois is required: pip install python-whois")
        return python_whois.whois(domain)

    async def ip_lookup(self, ip: str) -> IPInfo:
        """Free IP geolocation via ip-api.com (no API key, 45 req/min)."""
        info = IPInfo(ip=ip)

        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,lat,lon,timezone,isp,org,as,reverse,query"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("status") == "success":
                            info.city = data.get("city")
                            info.region = data.get("regionName")
                            info.country = data.get("country")
                            info.org = data.get("org")
                            info.isp = data.get("isp")
                            info.asn = data.get("as")
                            info.lat = data.get("lat")
                            info.lon = data.get("lon")
                            info.timezone = data.get("timezone")
                            info.reverse_dns = data.get("reverse")
                        else:
                            info.errors.append(data.get("message", "Unknown error"))
        except Exception as e:
            info.errors.append(f"IP lookup failed: {str(e)}")
            self.logger.warning(f"IP lookup failed for {ip}: {e}")

        return info

    def _safe_str(self, value) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, list):
            return str(value[0]) if value else None
        return str(value)

    def _format_date(self, value) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, list):
            value = value[0] if value else None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value) if value else None
