"""
Investigation Orchestrator — Central Pipeline Controller

Chains all recon modules and pipeline stages into a complete investigation.
Designed to be driven by the desktop UI via signals/callbacks.
Runs asynchronously so the UI thread stays responsive.
"""

import asyncio
import logging
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.connectors.local.dns_recon import DNSRecon
from src.connectors.local.whois_recon import WhoisRecon
from src.connectors.local.port_scanner import PortScanner
from src.connectors.local.cert_recon import CertRecon
from src.connectors.local.web_scraper import WebScraper
from src.connectors.local.username_checker import UsernameChecker
from src.connectors.local.email_harvester import EmailHarvester
from src.connectors.local.tech_fingerprinter import TechFingerprinter
from src.connectors.local.person_recon import PersonRecon

logger = logging.getLogger(__name__)


class InvestigationStage(Enum):
    INITIALIZING = "initializing"
    DNS_RECON = "dns_recon"
    WHOIS_LOOKUP = "whois_lookup"
    PORT_SCAN = "port_scan"
    CERT_TRANSPARENCY = "cert_transparency"
    WEB_ANALYSIS = "web_analysis"
    EMAIL_HARVEST = "email_harvest"
    USERNAME_CHECK = "username_check"
    PERSON_SEARCH = "person_search"
    ENTITY_RESOLUTION = "entity_resolution"
    RISK_SCORING = "risk_scoring"
    REPORT_GENERATION = "report_generation"
    COMPLETE = "complete"


class EntityType(Enum):
    DOMAIN = "domain"
    IP = "ip"
    EMAIL = "email"
    USERNAME = "username"
    PERSON = "person"
    ORGANIZATION = "organization"


@dataclass
class InvestigationConfig:
    """Configuration for an investigation."""
    target: str
    entity_type: EntityType = EntityType.DOMAIN
    # Module toggles
    run_dns: bool = True
    run_whois: bool = True
    run_ports: bool = True
    run_certs: bool = True
    run_web: bool = True
    run_emails: bool = True
    run_usernames: bool = False
    run_person_search: bool = True
    # Scan options
    port_scan_quick: bool = True  # Quick (20 ports) vs full (100 ports)
    subdomain_scan: bool = True
    max_email_pages: int = 10
    # Person search fields
    person_name: str = ""
    date_of_birth: str = ""
    location: str = ""
    # Output
    case_name: str = ""
    output_dir: str = ""


@dataclass
class InvestigationResult:
    """Complete investigation results."""
    config: Dict[str, Any] = field(default_factory=dict)
    target: str = ""
    entity_type: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0
    # Module results
    dns: Dict[str, Any] = field(default_factory=dict)
    whois: Dict[str, Any] = field(default_factory=dict)
    ip_info: Dict[str, Any] = field(default_factory=dict)
    ports: Dict[str, Any] = field(default_factory=dict)
    certificates: Dict[str, Any] = field(default_factory=dict)
    web: Dict[str, Any] = field(default_factory=dict)
    emails: Dict[str, Any] = field(default_factory=dict)
    usernames: Dict[str, Any] = field(default_factory=dict)
    person_data: Dict[str, Any] = field(default_factory=dict)
    # Analysis
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    risk_score: float = 0.0
    risk_factors: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v}

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


class InvestigationOrchestrator:
    """
    Central investigation orchestrator.
    
    Chains recon modules and assembles results into a unified report.
    Provides progress callbacks for UI integration.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.Orchestrator")
        self._cancelled = False

        # Initialize recon modules
        self.dns = DNSRecon()
        self.whois = WhoisRecon()
        self.port_scanner = PortScanner()
        self.cert_recon = CertRecon()
        self.web_scraper = WebScraper()
        self.username_checker = UsernameChecker()
        self.email_harvester = EmailHarvester()
        self.tech_fingerprinter = TechFingerprinter()
        self.person_recon = PersonRecon()

    async def run_investigation(self, config: InvestigationConfig,
                                 progress_callback: Optional[Callable] = None,
                                 stage_callback: Optional[Callable] = None) -> InvestigationResult:
        """
        Execute a full investigation pipeline.
        
        Args:
            config: Investigation configuration
            progress_callback: Called with (message: str, percent: int)
            stage_callback: Called with (stage: InvestigationStage, status: str)
        """
        self._cancelled = False
        result = InvestigationResult(
            target=config.target,
            entity_type=config.entity_type.value,
            started_at=datetime.utcnow().isoformat(),
        )
        start_time = datetime.utcnow()

        def _progress(msg: str, pct: int):
            if progress_callback:
                progress_callback(msg, pct)

        def _stage(stage: InvestigationStage, status: str = "running"):
            if stage_callback:
                stage_callback(stage, status)

        try:
            # Determine what to run based on entity type
            if config.entity_type == EntityType.DOMAIN:
                await self._investigate_domain(config, result, _progress, _stage)
            elif config.entity_type == EntityType.IP:
                await self._investigate_ip(config, result, _progress, _stage)
            elif config.entity_type == EntityType.EMAIL:
                await self._investigate_email(config, result, _progress, _stage)
            elif config.entity_type == EntityType.USERNAME:
                await self._investigate_username(config, result, _progress, _stage)
            elif config.entity_type in (EntityType.PERSON, EntityType.ORGANIZATION):
                await self._investigate_entity(config, result, _progress, _stage)

            # Entity resolution & relationship mapping
            if not self._cancelled:
                _stage(InvestigationStage.ENTITY_RESOLUTION, "running")
                _progress("Resolving entities and relationships", 85)
                self._resolve_entities(result)
                _stage(InvestigationStage.ENTITY_RESOLUTION, "complete")

            # Risk scoring
            if not self._cancelled:
                _stage(InvestigationStage.RISK_SCORING, "running")
                _progress("Calculating risk scores", 92)
                self._calculate_risk(result)
                _stage(InvestigationStage.RISK_SCORING, "complete")

            # Generate summary
            if not self._cancelled:
                _stage(InvestigationStage.REPORT_GENERATION, "running")
                _progress("Generating report", 97)
                self._generate_summary(result)
                _stage(InvestigationStage.REPORT_GENERATION, "complete")

        except Exception as e:
            result.errors.append(f"Investigation failed: {str(e)}")
            self.logger.error(f"Investigation failed: {e}", exc_info=True)

        end_time = datetime.utcnow()
        result.completed_at = end_time.isoformat()
        result.duration_seconds = (end_time - start_time).total_seconds()

        _stage(InvestigationStage.COMPLETE, "complete")
        _progress("Investigation complete", 100)

        return result

    def cancel(self):
        """Cancel the running investigation."""
        self._cancelled = True

    async def _investigate_domain(self, config: InvestigationConfig,
                                   result: InvestigationResult,
                                   progress, stage):
        """Run domain-focused investigation."""
        domain = config.target.replace("https://", "").replace("http://", "").strip("/")

        # 1. DNS Recon
        if config.run_dns and not self._cancelled:
            stage(InvestigationStage.DNS_RECON, "running")
            progress("Running DNS reconnaissance", 5)
            try:
                dns_report = await self.dns.full_recon(domain, subdomain_scan=config.subdomain_scan)
                result.dns = dns_report.to_dict()
                result.errors.extend([f"DNS: {e}" for e in dns_report.errors])
            except Exception as e:
                result.errors.append(f"DNS recon failed: {str(e)}")
            stage(InvestigationStage.DNS_RECON, "complete")

        # 2. WHOIS Lookup
        if config.run_whois and not self._cancelled:
            stage(InvestigationStage.WHOIS_LOOKUP, "running")
            progress("Running WHOIS lookup", 15)
            try:
                whois_data = await self.whois.domain_whois(domain)
                result.whois = whois_data.to_dict()
                # IP geolocation for resolved IPs
                if result.dns.get("ip_addresses"):
                    ip = result.dns["ip_addresses"][0]
                    ip_info = await self.whois.ip_lookup(ip)
                    result.ip_info = ip_info.to_dict()
            except Exception as e:
                result.errors.append(f"WHOIS failed: {str(e)}")
            stage(InvestigationStage.WHOIS_LOOKUP, "complete")

        # 3. Port Scan
        if config.run_ports and not self._cancelled:
            stage(InvestigationStage.PORT_SCAN, "running")
            progress("Scanning ports", 25)
            try:
                scan = await self.port_scanner.scan(domain, quick=config.port_scan_quick)
                result.ports = scan.to_dict()
            except Exception as e:
                result.errors.append(f"Port scan failed: {str(e)}")
            stage(InvestigationStage.PORT_SCAN, "complete")

        # 4. Cert Transparency
        if config.run_certs and not self._cancelled:
            stage(InvestigationStage.CERT_TRANSPARENCY, "running")
            progress("Querying certificate transparency", 40)
            try:
                certs = await self.cert_recon.search(domain)
                result.certificates = certs.to_dict()
            except Exception as e:
                result.errors.append(f"Cert recon failed: {str(e)}")
            stage(InvestigationStage.CERT_TRANSPARENCY, "complete")

        # 5. Web Analysis
        if config.run_web and not self._cancelled:
            stage(InvestigationStage.WEB_ANALYSIS, "running")
            progress("Analyzing website", 55)
            try:
                page = await self.web_scraper.analyze(domain)
                result.web = page.to_dict()
            except Exception as e:
                result.errors.append(f"Web analysis failed: {str(e)}")
            stage(InvestigationStage.WEB_ANALYSIS, "complete")

        # 6. Email Harvesting
        if config.run_emails and not self._cancelled:
            stage(InvestigationStage.EMAIL_HARVEST, "running")
            progress("Harvesting email addresses", 70)
            try:
                harvest = await self.email_harvester.harvest(domain)
                result.emails = harvest.to_dict()
            except Exception as e:
                result.errors.append(f"Email harvest failed: {str(e)}")
            stage(InvestigationStage.EMAIL_HARVEST, "complete")

    async def _investigate_ip(self, config, result, progress, stage):
        """Run IP-focused investigation."""
        ip = config.target

        # WHOIS + Geolocation
        if config.run_whois:
            stage(InvestigationStage.WHOIS_LOOKUP, "running")
            progress("Running IP lookup", 10)
            try:
                ip_info = await self.whois.ip_lookup(ip)
                result.ip_info = ip_info.to_dict()
                # Reverse DNS
                reverse = await self.dns.reverse_lookup(ip)
                if reverse:
                    result.dns["reverse_dns"] = reverse
            except Exception as e:
                result.errors.append(f"IP lookup failed: {str(e)}")
            stage(InvestigationStage.WHOIS_LOOKUP, "complete")

        # Port Scan
        if config.run_ports:
            stage(InvestigationStage.PORT_SCAN, "running")
            progress("Scanning ports", 30)
            try:
                scan = await self.port_scanner.scan(ip, quick=config.port_scan_quick)
                result.ports = scan.to_dict()
            except Exception as e:
                result.errors.append(f"Port scan failed: {str(e)}")
            stage(InvestigationStage.PORT_SCAN, "complete")

    async def _investigate_email(self, config, result, progress, stage):
        """Run email-focused investigation."""
        email = config.target
        domain = email.split("@")[1] if "@" in email else email

        # DNS for the email domain
        if config.run_dns:
            stage(InvestigationStage.DNS_RECON, "running")
            progress("Checking email domain DNS", 10)
            try:
                dns_report = await self.dns.full_recon(domain, subdomain_scan=False)
                result.dns = dns_report.to_dict()
            except Exception as e:
                result.errors.append(f"DNS failed: {str(e)}")
            stage(InvestigationStage.DNS_RECON, "complete")

        # Email validation
        progress("Validating email", 30)
        try:
            validation = await self.email_harvester.check_email_exists(email)
            result.emails = {"target_email": email, "validation": validation}
        except Exception as e:
            result.errors.append(f"Email validation failed: {str(e)}")

        # Username check (the part before @)
        if config.run_usernames:
            username = email.split("@")[0]
            stage(InvestigationStage.USERNAME_CHECK, "running")
            progress(f"Checking username '{username}' across platforms", 50)
            try:
                username_report = await self.username_checker.check(username)
                result.usernames = username_report.to_dict()
            except Exception as e:
                result.errors.append(f"Username check failed: {str(e)}")
            stage(InvestigationStage.USERNAME_CHECK, "complete")

    async def _investigate_username(self, config, result, progress, stage):
        """Run username-focused investigation."""
        stage(InvestigationStage.USERNAME_CHECK, "running")
        progress("Checking username across platforms", 20)
        try:
            report = await self.username_checker.check(config.target)
            result.usernames = report.to_dict()
        except Exception as e:
            result.errors.append(f"Username check failed: {str(e)}")
        stage(InvestigationStage.USERNAME_CHECK, "complete")

    async def _investigate_entity(self, config, result, progress, stage):
        """Run person/organization investigation with full person search."""
        name = config.person_name or config.target

        # 1. Person Search (people-finder sites, social, web mentions)
        if config.run_person_search and not self._cancelled:
            stage(InvestigationStage.PERSON_SEARCH, "running")
            progress(f"Searching for '{name}'", 10)
            try:
                person_report = await self.person_recon.search(
                    full_name=name,
                    date_of_birth=config.date_of_birth,
                    location=config.location,
                    progress_callback=lambda msg, pct: progress(msg, 10 + int(pct * 0.5)),
                )
                result.person_data = person_report.to_dict()
                result.errors.extend([f"Person: {e}" for e in person_report.errors])
            except Exception as e:
                result.errors.append(f"Person search failed: {str(e)}")
            stage(InvestigationStage.PERSON_SEARCH, "complete")

        # 2. Username check (generated usernames from person search)
        if config.run_usernames and not self._cancelled:
            stage(InvestigationStage.USERNAME_CHECK, "running")
            progress("Checking generated usernames across platforms", 65)
            try:
                # Use first generated username, or derive from name
                usernames_to_check = result.person_data.get("possible_usernames", [])
                if not usernames_to_check:
                    usernames_to_check = [name.replace(" ", "").lower()]
                # Check the top 3 username candidates
                all_found = []
                for uname in usernames_to_check[:3]:
                    report = await self.username_checker.check(uname)
                    data = report.to_dict()
                    for found in data.get("found_on", []):
                        found["username_variant"] = uname
                        all_found.append(found)
                result.usernames = {"found_on": all_found, "checked_usernames": usernames_to_check[:3]}
            except Exception as e:
                result.errors.append(f"Username check failed: {str(e)}")
            stage(InvestigationStage.USERNAME_CHECK, "complete")

    def _resolve_entities(self, result: InvestigationResult):
        """Build entity list and relationships from all collected data."""
        entities = []
        relationships = []
        entity_id = 0

        # Target entity
        target_entity = {
            "id": entity_id, "type": result.entity_type,
            "value": result.target, "label": result.target,
            "is_target": True
        }
        entities.append(target_entity)

        # DNS-derived entities
        for ip in result.dns.get("ip_addresses", []):
            entity_id += 1
            entities.append({"id": entity_id, "type": "ip", "value": ip, "label": ip})
            relationships.append({"source": 0, "target": entity_id, "type": "resolves_to", "label": "A record"})

        for ns in result.dns.get("nameservers", []):
            entity_id += 1
            entities.append({"id": entity_id, "type": "nameserver", "value": ns, "label": ns})
            relationships.append({"source": 0, "target": entity_id, "type": "uses_nameserver"})

        for mx in result.dns.get("mail_servers", []):
            entity_id += 1
            entities.append({"id": entity_id, "type": "mail_server", "value": mx, "label": mx})
            relationships.append({"source": 0, "target": entity_id, "type": "uses_mail_server"})

        for sub in result.dns.get("subdomains", []):
            entity_id += 1
            entities.append({"id": entity_id, "type": "subdomain", "value": sub, "label": sub})
            relationships.append({"source": 0, "target": entity_id, "type": "has_subdomain"})

        # CT-derived subdomains
        for sub in result.certificates.get("unique_subdomains", []):
            if not any(e["value"] == sub for e in entities):
                entity_id += 1
                entities.append({"id": entity_id, "type": "subdomain", "value": sub, "label": sub})
                relationships.append({"source": 0, "target": entity_id, "type": "cert_subdomain"})

        # WHOIS-derived entities
        registrar = result.whois.get("registrar")
        if registrar:
            entity_id += 1
            entities.append({"id": entity_id, "type": "registrar", "value": registrar, "label": registrar})
            relationships.append({"source": 0, "target": entity_id, "type": "registered_with"})

        # IP geolocation
        if result.ip_info.get("org"):
            entity_id += 1
            entities.append({"id": entity_id, "type": "organization", "value": result.ip_info["org"], "label": result.ip_info["org"]})
            # Link to the IP
            ip_entity = next((e for e in entities if e["type"] == "ip"), None)
            if ip_entity:
                relationships.append({"source": ip_entity["id"], "target": entity_id, "type": "owned_by"})

        # Email entities
        for email_data in result.emails.get("emails", []):
            email = email_data if isinstance(email_data, str) else email_data.get("email", "")
            if email:
                entity_id += 1
                entities.append({"id": entity_id, "type": "email", "value": email, "label": email})
                relationships.append({"source": 0, "target": entity_id, "type": "found_email"})

        # Web-derived entities
        for platform, url in result.web.get("social_links", {}).items():
            entity_id += 1
            entities.append({"id": entity_id, "type": "social_profile", "value": url, "label": f"{platform}"})
            relationships.append({"source": 0, "target": entity_id, "type": "has_social_profile"})

        # Port-derived entities (services)
        for port_data in result.ports.get("open_ports", []):
            entity_id += 1
            label = f"{port_data.get('service', 'unknown')}:{port_data['port']}"
            entities.append({"id": entity_id, "type": "service", "value": label, "label": label})
            ip_entity = next((e for e in entities if e["type"] == "ip"), None)
            if ip_entity:
                relationships.append({"source": ip_entity["id"], "target": entity_id, "type": "runs_service"})

        # Username matches
        for found in result.usernames.get("found_on", []):
            entity_id += 1
            entities.append({
                "id": entity_id, "type": "social_profile",
                "value": found.get("url", ""), "label": found.get("platform", "")
            })
            relationships.append({"source": 0, "target": entity_id, "type": "username_match"})

        # Person search derived entities
        for profile in result.person_data.get("social_profiles", []):
            if not any(e["value"] == profile.get("url", "") for e in entities):
                entity_id += 1
                entities.append({
                    "id": entity_id, "type": "social_profile",
                    "value": profile.get("url", ""),
                    "label": profile.get("platform", "Unknown")
                })
                relationships.append({"source": 0, "target": entity_id, "type": "person_social_profile"})

        for email in result.person_data.get("possible_emails", []):
            if not any(e["value"] == email for e in entities):
                entity_id += 1
                entities.append({"id": entity_id, "type": "email", "value": email, "label": email})
                relationships.append({"source": 0, "target": entity_id, "type": "possible_email"})

        for phone in result.person_data.get("phone_numbers", []):
            entity_id += 1
            entities.append({"id": entity_id, "type": "phone", "value": phone, "label": phone})
            relationships.append({"source": 0, "target": entity_id, "type": "phone_number"})

        for addr in result.person_data.get("addresses", []):
            entity_id += 1
            entities.append({"id": entity_id, "type": "address", "value": addr, "label": addr[:40]})
            relationships.append({"source": 0, "target": entity_id, "type": "known_address"})

        for employer in result.person_data.get("employers", []):
            entity_id += 1
            entities.append({"id": entity_id, "type": "organization", "value": employer, "label": employer[:40]})
            relationships.append({"source": 0, "target": entity_id, "type": "employed_by"})

        result.entities = entities
        result.relationships = relationships

        # Build timeline
        self._build_timeline(result)

    def _build_timeline(self, result: InvestigationResult):
        """Build a chronological timeline from all data points."""
        timeline = []

        # Domain registration dates
        if result.whois.get("creation_date"):
            timeline.append({
                "date": result.whois["creation_date"],
                "event": "Domain registered",
                "category": "registration",
                "source": "whois",
                "detail": f"Registrar: {result.whois.get('registrar', 'Unknown')}"
            })
        if result.whois.get("expiration_date"):
            timeline.append({
                "date": result.whois["expiration_date"],
                "event": "Domain expires",
                "category": "registration",
                "source": "whois",
            })

        # Certificate issuance/expiry dates
        for cert in result.certificates.get("certificates", [])[:20]:
            if cert.get("not_before"):
                timeline.append({
                    "date": cert["not_before"],
                    "event": f"Certificate issued for {cert.get('common_name', 'unknown')}",
                    "category": "certificate",
                    "source": "crt.sh",
                })

        # Sort timeline by date
        timeline.sort(key=lambda x: x.get("date", ""))
        result.timeline = timeline

    def _calculate_risk(self, result: InvestigationResult):
        """Calculate risk score based on findings."""
        score = 0.0
        factors = []

        # Open ports risk
        open_ports = result.ports.get("open_port_count", 0)
        if open_ports > 20:
            score += 25
            factors.append({"factor": "Excessive open ports", "score": 25, "detail": f"{open_ports} ports open"})
        elif open_ports > 10:
            score += 15
            factors.append({"factor": "Many open ports", "score": 15, "detail": f"{open_ports} ports open"})
        elif open_ports > 5:
            score += 5
            factors.append({"factor": "Several open ports", "score": 5, "detail": f"{open_ports} ports open"})

        # Security headers
        sec_score = result.web.get("security_headers", {}).get("score", 100)
        if sec_score < 30:
            score += 20
            factors.append({"factor": "Poor security headers", "score": 20, "detail": f"Score: {sec_score}/100"})
        elif sec_score < 60:
            score += 10
            factors.append({"factor": "Weak security headers", "score": 10, "detail": f"Score: {sec_score}/100"})

        # Email security
        email_sec = result.dns.get("email_security", {})
        if not email_sec.get("spf"):
            score += 10
            factors.append({"factor": "No SPF record", "score": 10, "detail": "Email spoofing possible"})
        elif email_sec.get("spf", {}).get("strict") is False:
            score += 5
            factors.append({"factor": "Soft SPF policy", "score": 5, "detail": "Using ~all instead of -all"})

        if not email_sec.get("dmarc"):
            score += 10
            factors.append({"factor": "No DMARC record", "score": 10, "detail": "No email authentication policy"})

        if not email_sec.get("dkim_selector_found"):
            score += 5
            factors.append({"factor": "No DKIM found", "score": 5, "detail": "Common selectors not found"})

        # Exposed emails
        email_count = result.emails.get("email_count", 0)
        if email_count > 10:
            score += 15
            factors.append({"factor": "Many exposed emails", "score": 15, "detail": f"{email_count} emails found on website"})
        elif email_count > 3:
            score += 5
            factors.append({"factor": "Exposed emails", "score": 5, "detail": f"{email_count} emails found"})

        # Old technologies
        techs = result.web.get("technologies", [])
        risky_techs = [t for t in techs if t in ("jQuery", "PHP", "ASP.NET")]
        if risky_techs:
            score += 5
            factors.append({"factor": "Legacy technology detected", "score": 5, "detail": ", ".join(risky_techs)})

        # Exposed subdomains
        subdomain_count = len(result.dns.get("subdomains", [])) + result.certificates.get("subdomain_count", 0)
        if subdomain_count > 50:
            score += 10
            factors.append({"factor": "Large attack surface", "score": 10, "detail": f"{subdomain_count} subdomains discovered"})

        # Normalize to 0-100
        result.risk_score = min(score, 100)
        result.risk_factors = factors

    def _generate_summary(self, result: InvestigationResult):
        """Generate a human-readable summary of findings."""
        lines = [f"Investigation Summary for {result.target}"]
        lines.append("=" * 50)

        # Person-specific summary
        if result.person_data:
            pd = result.person_data
            if pd.get("age"):
                lines.append(f"• Age: {pd['age']}")
            if pd.get("location"):
                lines.append(f"• Location: {pd['location']}")
            profiles = pd.get("social_profiles", [])
            if profiles:
                lines.append(f"• Social profiles found: {len(profiles)}")
                for p in profiles[:5]:
                    lines.append(f"  → {p.get('platform', '?')}: {p.get('url', '')}")
            records = pd.get("public_records", [])
            if records:
                lines.append(f"• Public records found on: {', '.join(r.get('source', '') for r in records)}")
            phones = pd.get("phone_numbers", [])
            if phones:
                lines.append(f"• Phone numbers: {', '.join(phones[:5])}")
            addresses = pd.get("addresses", [])
            if addresses:
                lines.append(f"• Known addresses: {len(addresses)}")
            emails = pd.get("possible_emails", [])
            if emails:
                lines.append(f"• Possible emails ({len(emails)}): {', '.join(emails[:5])}")
            mentions = pd.get("web_mentions", [])
            if mentions:
                lines.append(f"• Web mentions found: {len(mentions)}")
            archived = pd.get("archived_pages", [])
            if archived:
                lines.append(f"• Archived pages found: {len(archived)}")
            if pd.get("confidence_score"):
                lines.append(f"• Data confidence: {pd['confidence_score']:.0f}/100")

        # Domain/IP summary
        if result.dns.get("ip_addresses"):
            lines.append(f"• Resolves to: {', '.join(result.dns['ip_addresses'][:3])}")

        if result.ip_info.get("org"):
            loc_parts = [result.ip_info.get("city"), result.ip_info.get("country")]
            loc = ", ".join(p for p in loc_parts if p)
            lines.append(f"• Hosted by: {result.ip_info['org']} ({loc})")

        if result.whois.get("registrar"):
            lines.append(f"• Registrar: {result.whois['registrar']}")

        if result.whois.get("creation_date"):
            lines.append(f"• Registered: {result.whois['creation_date']}")

        open_ports = result.ports.get("open_port_count", 0)
        if open_ports:
            services = [f"{p['service']}:{p['port']}" for p in result.ports.get("open_ports", [])[:5]]
            lines.append(f"• Open ports ({open_ports}): {', '.join(services)}")

        if result.web.get("technologies"):
            lines.append(f"• Technologies: {', '.join(result.web['technologies'][:10])}")

        sub_count = len(result.dns.get("subdomains", [])) + result.certificates.get("subdomain_count", 0)
        if sub_count:
            lines.append(f"• Subdomains discovered: {sub_count}")

        email_count = result.emails.get("email_count", 0)
        if email_count:
            lines.append(f"• Emails found: {email_count}")

        lines.append(f"• Risk Score: {result.risk_score}/100")
        if result.risk_factors:
            for f in result.risk_factors[:5]:
                lines.append(f"  ⚠ {f['factor']}: {f.get('detail', '')}")

        lines.append(f"• Entities discovered: {len(result.entities)}")
        lines.append(f"• Relationships mapped: {len(result.relationships)}")
        lines.append(f"• Duration: {result.duration_seconds:.1f}s")

        result.summary = "\n".join(lines)
