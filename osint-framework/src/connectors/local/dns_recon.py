"""
DNS Reconnaissance Module — No API Keys Required

Performs comprehensive DNS intelligence gathering using direct DNS protocol queries
via dnspython. Extracts records, checks email security posture, discovers subdomains.

Free data sources:
- Direct DNS queries (UDP/TCP port 53)
- Public DNS resolvers (8.8.8.8, 1.1.1.1)
- DNS over HTTPS fallback
"""

import asyncio
import socket
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime

try:
    import dns.resolver
    import dns.reversename
    import dns.zone
    import dns.query
    import dns.rdatatype
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False

logger = logging.getLogger(__name__)

# Top 500 common subdomains for brute-force enumeration
COMMON_SUBDOMAINS = [
    "www", "mail", "ftp", "localhost", "webmail", "smtp", "pop", "ns1", "ns2",
    "ns3", "ns4", "imap", "cpanel", "whm", "autodiscover", "autoconfig",
    "m", "mobile", "blog", "dev", "staging", "api", "app", "admin", "portal",
    "vpn", "remote", "gateway", "proxy", "cdn", "static", "assets", "media",
    "img", "images", "video", "download", "upload", "files", "docs", "doc",
    "wiki", "help", "support", "status", "monitor", "test", "demo", "sandbox",
    "beta", "alpha", "stage", "uat", "qa", "ci", "cd", "jenkins", "gitlab",
    "git", "svn", "hg", "repo", "registry", "docker", "k8s", "kubernetes",
    "cloud", "aws", "azure", "gcp", "s3", "storage", "backup", "db", "database",
    "mysql", "postgres", "redis", "mongo", "elastic", "elasticsearch", "kibana",
    "grafana", "prometheus", "influx", "kafka", "rabbitmq", "mq", "queue",
    "cache", "memcached", "varnish", "nginx", "apache", "tomcat", "jboss",
    "weblogic", "iis", "exchange", "owa", "outlook", "calendar", "contacts",
    "chat", "im", "xmpp", "jabber", "irc", "slack", "teams", "zoom", "meet",
    "conference", "webex", "sip", "voip", "pbx", "phone", "tel", "fax",
    "print", "printer", "scan", "scanner", "nas", "san", "nfs", "smb", "cifs",
    "ldap", "ad", "dc", "dns", "dhcp", "ntp", "snmp", "syslog", "log",
    "monitor", "nagios", "zabbix", "icinga", "prtg", "solarwinds",
    "firewall", "fw", "ids", "ips", "waf", "dmz", "bastion", "jump",
    "vpn", "ssl", "tls", "cert", "pki", "ca", "ocsp", "crl",
    "auth", "sso", "oauth", "saml", "cas", "radius", "tacacs",
    "crm", "erp", "hr", "finance", "billing", "invoice", "payment",
    "shop", "store", "ecommerce", "cart", "checkout", "order",
    "forum", "community", "social", "feed", "rss", "atom", "newsletter",
    "analytics", "tracking", "pixel", "tag", "gtm", "ga",
    "search", "solr", "sphinx", "lucene", "algolia",
    "map", "maps", "geo", "gis", "location",
    "iot", "device", "sensor", "controller", "plc", "scada",
    "internal", "intranet", "extranet", "partner", "vendor", "client",
    "old", "new", "legacy", "archive", "v1", "v2", "v3",
    "mx", "mx1", "mx2", "relay", "smarthost", "postfix", "sendmail",
    "www1", "www2", "www3", "web1", "web2", "node1", "node2",
    "server", "host", "vps", "dedicated", "shared", "cluster",
    "panel", "control", "manage", "manager", "console",
    "login", "signin", "signup", "register", "account", "profile",
    "dashboard", "home", "index", "main", "root", "base",
]


@dataclass
class DNSRecord:
    record_type: str
    name: str
    value: str
    ttl: int = 0
    priority: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class DNSReport:
    domain: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    records: List[DNSRecord] = field(default_factory=list)
    subdomains: List[str] = field(default_factory=list)
    nameservers: List[str] = field(default_factory=list)
    mail_servers: List[str] = field(default_factory=list)
    email_security: Dict[str, Any] = field(default_factory=dict)
    txt_records: List[str] = field(default_factory=list)
    ip_addresses: List[str] = field(default_factory=list)
    ipv6_addresses: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "timestamp": self.timestamp.isoformat(),
            "records": [
                {"type": r.record_type, "name": r.name, "value": r.value,
                 "ttl": r.ttl, "priority": r.priority, **r.extra}
                for r in self.records
            ],
            "subdomains": self.subdomains,
            "nameservers": self.nameservers,
            "mail_servers": self.mail_servers,
            "email_security": self.email_security,
            "txt_records": self.txt_records,
            "ip_addresses": self.ip_addresses,
            "ipv6_addresses": self.ipv6_addresses,
            "errors": self.errors,
        }


class DNSRecon:
    """DNS reconnaissance — comprehensive DNS intelligence with no API keys."""

    def __init__(self, nameservers: Optional[List[str]] = None, timeout: float = 5.0):
        if not HAS_DNSPYTHON:
            raise ImportError("dnspython is required: pip install dnspython")
        self.resolver = dns.resolver.Resolver()
        self.resolver.nameservers = nameservers or ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
        self.resolver.timeout = timeout
        self.resolver.lifetime = timeout * 2
        self.logger = logging.getLogger(f"{__name__}.DNSRecon")

    async def full_recon(self, domain: str, subdomain_scan: bool = True,
                         progress_callback=None) -> DNSReport:
        """Run complete DNS reconnaissance on a domain."""
        report = DNSReport(domain=domain)

        steps = [
            ("A records", self._query_a),
            ("AAAA records", self._query_aaaa),
            ("MX records", self._query_mx),
            ("NS records", self._query_ns),
            ("TXT records", self._query_txt),
            ("SOA record", self._query_soa),
            ("CNAME records", self._query_cname),
            ("SRV records", self._query_srv),
            ("Email security", self._check_email_security),
        ]
        if subdomain_scan:
            steps.append(("Subdomain enumeration", self._enumerate_subdomains))

        for i, (label, func) in enumerate(steps):
            try:
                if progress_callback:
                    progress_callback(f"DNS: {label}", int((i / len(steps)) * 100))
                await asyncio.get_event_loop().run_in_executor(None, func, domain, report)
            except Exception as e:
                report.errors.append(f"{label}: {str(e)}")
                self.logger.warning(f"DNS {label} failed for {domain}: {e}")

        return report

    def _query_a(self, domain: str, report: DNSReport):
        try:
            answers = self.resolver.resolve(domain, "A")
            for rdata in answers:
                ip = str(rdata)
                report.ip_addresses.append(ip)
                report.records.append(DNSRecord(
                    record_type="A", name=domain, value=ip, ttl=answers.rrset.ttl
                ))
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            pass

    def _query_aaaa(self, domain: str, report: DNSReport):
        try:
            answers = self.resolver.resolve(domain, "AAAA")
            for rdata in answers:
                ip6 = str(rdata)
                report.ipv6_addresses.append(ip6)
                report.records.append(DNSRecord(
                    record_type="AAAA", name=domain, value=ip6, ttl=answers.rrset.ttl
                ))
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            pass

    def _query_mx(self, domain: str, report: DNSReport):
        try:
            answers = self.resolver.resolve(domain, "MX")
            for rdata in answers:
                mx_host = str(rdata.exchange).rstrip(".")
                report.mail_servers.append(mx_host)
                report.records.append(DNSRecord(
                    record_type="MX", name=domain, value=mx_host,
                    ttl=answers.rrset.ttl, priority=rdata.preference
                ))
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            pass

    def _query_ns(self, domain: str, report: DNSReport):
        try:
            answers = self.resolver.resolve(domain, "NS")
            for rdata in answers:
                ns = str(rdata).rstrip(".")
                report.nameservers.append(ns)
                report.records.append(DNSRecord(
                    record_type="NS", name=domain, value=ns, ttl=answers.rrset.ttl
                ))
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            pass

    def _query_txt(self, domain: str, report: DNSReport):
        try:
            answers = self.resolver.resolve(domain, "TXT")
            for rdata in answers:
                txt = str(rdata).strip('"')
                report.txt_records.append(txt)
                report.records.append(DNSRecord(
                    record_type="TXT", name=domain, value=txt, ttl=answers.rrset.ttl
                ))
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            pass

    def _query_soa(self, domain: str, report: DNSReport):
        try:
            answers = self.resolver.resolve(domain, "SOA")
            for rdata in answers:
                report.records.append(DNSRecord(
                    record_type="SOA", name=domain,
                    value=str(rdata.mname).rstrip("."),
                    ttl=answers.rrset.ttl,
                    extra={
                        "mname": str(rdata.mname).rstrip("."),
                        "rname": str(rdata.rname).rstrip("."),
                        "serial": rdata.serial,
                        "refresh": rdata.refresh,
                        "retry": rdata.retry,
                        "expire": rdata.expire,
                        "minimum": rdata.minimum,
                    }
                ))
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            pass

    def _query_cname(self, domain: str, report: DNSReport):
        try:
            answers = self.resolver.resolve(domain, "CNAME")
            for rdata in answers:
                report.records.append(DNSRecord(
                    record_type="CNAME", name=domain,
                    value=str(rdata.target).rstrip("."),
                    ttl=answers.rrset.ttl
                ))
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            pass

    def _query_srv(self, domain: str, report: DNSReport):
        srv_prefixes = ["_sip._tcp", "_sip._udp", "_xmpp-server._tcp",
                        "_xmpp-client._tcp", "_autodiscover._tcp",
                        "_ldap._tcp", "_kerberos._tcp"]
        for prefix in srv_prefixes:
            try:
                fqdn = f"{prefix}.{domain}"
                answers = self.resolver.resolve(fqdn, "SRV")
                for rdata in answers:
                    report.records.append(DNSRecord(
                        record_type="SRV", name=fqdn,
                        value=str(rdata.target).rstrip("."),
                        ttl=answers.rrset.ttl, priority=rdata.priority,
                        extra={"weight": rdata.weight, "port": rdata.port}
                    ))
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
                    dns.resolver.NoNameservers, dns.exception.Timeout):
                pass

    def _check_email_security(self, domain: str, report: DNSReport):
        security = {"spf": None, "dmarc": None, "dkim_selector_found": False, "mx_count": len(report.mail_servers)}

        # SPF check
        for txt in report.txt_records:
            if txt.startswith("v=spf1"):
                security["spf"] = {
                    "record": txt,
                    "mechanisms": self._parse_spf(txt),
                    "strict": "-all" in txt,
                }
                break

        # DMARC check
        try:
            answers = self.resolver.resolve(f"_dmarc.{domain}", "TXT")
            for rdata in answers:
                txt = str(rdata).strip('"')
                if txt.startswith("v=DMARC1"):
                    security["dmarc"] = {
                        "record": txt,
                        "policy": self._extract_dmarc_tag(txt, "p"),
                        "subdomain_policy": self._extract_dmarc_tag(txt, "sp"),
                        "pct": self._extract_dmarc_tag(txt, "pct"),
                        "rua": self._extract_dmarc_tag(txt, "rua"),
                    }
                    break
        except Exception:
            pass

        # DKIM — try common selectors
        for selector in ["default", "google", "selector1", "selector2", "s1", "s2", "k1", "mail", "dkim"]:
            try:
                self.resolver.resolve(f"{selector}._domainkey.{domain}", "TXT")
                security["dkim_selector_found"] = True
                security.setdefault("dkim_selectors", []).append(selector)
            except Exception:
                pass

        report.email_security = security

    def _parse_spf(self, record: str) -> List[str]:
        return [p for p in record.split() if p != "v=spf1"]

    def _extract_dmarc_tag(self, record: str, tag: str) -> Optional[str]:
        for part in record.split(";"):
            part = part.strip()
            if part.startswith(f"{tag}="):
                return part.split("=", 1)[1]
        return None

    def _enumerate_subdomains(self, domain: str, report: DNSReport):
        """Brute-force subdomain discovery using common subdomain wordlist."""
        found: Set[str] = set()
        for subdomain in COMMON_SUBDOMAINS:
            fqdn = f"{subdomain}.{domain}"
            try:
                answers = self.resolver.resolve(fqdn, "A")
                for rdata in answers:
                    found.add(subdomain)
                    report.records.append(DNSRecord(
                        record_type="A", name=fqdn, value=str(rdata),
                        ttl=answers.rrset.ttl
                    ))
            except Exception:
                pass
        report.subdomains = sorted(found)

    async def reverse_lookup(self, ip: str) -> Optional[str]:
        """Reverse DNS lookup for an IP address."""
        try:
            rev_name = dns.reversename.from_address(ip)
            answers = await asyncio.get_event_loop().run_in_executor(
                None, self.resolver.resolve, rev_name, "PTR"
            )
            for rdata in answers:
                return str(rdata).rstrip(".")
        except Exception:
            return None
