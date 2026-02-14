"""
Discovery Engine for OSINT Investigation Pipeline

Purpose
- Generate optimized search queries from seed identifiers
- Map queries to appropriate source connectors
- Validate and sanitize input data

Invariants
- All generated queries must be safe for public search engines
- No PII or sensitive data should be included in query parameters
- Every query must have at least one target connector
- Query generation must be deterministic for reproducible investigations

Failure Modes
- Invalid input format → raises ValidationError with specific field details
- No available connectors for query type → returns empty query list with warning
- Rate limiting exceeded → queries are queued for later processing
- Malicious input detected → query is rejected and security event logged

Debug Notes
- Check logs for 'query.generated' events to see what queries are created
- Use correlation_id to trace query generation through the pipeline
- Monitor query_validation_failed metrics for input quality issues
- Review security_alerts for any blocked malicious queries

Design Tradeoffs
- Chose exhaustive query generation over minimal queries to maximize discovery
- Tradeoff: More queries = higher discovery rate but increased resource usage
- Mitigation: Rate limiting and query deduplication prevent abuse
- Review trigger: If query success rate drops below 60%, optimize query strategy
"""

import asyncio
import hashlib
import logging
import re
import uuid
from datetime import datetime
from typing import Dict, List, Any, Set, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..models.entities import (
    InvestigationInput, 
    SubjectIdentifiers, 
    EntityType,
    validate_email,
    validate_phone,
    validate_domain,
    redact_sensitive_data
)
from ...connectors.base import ConnectorRegistry, EntityType as ConnectorEntityType


class QueryType(Enum):
    """Types of queries that can be generated."""
    NAME_SEARCH = "name_search"
    USERNAME_SEARCH = "username_search"
    EMAIL_SEARCH = "email_search"
    PHONE_SEARCH = "phone_search"
    DOMAIN_SEARCH = "domain_search"
    COMPANY_SEARCH = "company_search"
    LOCATION_SEARCH = "location_search"
    COMPOSITE_SEARCH = "composite_search"


class SecurityLevel(Enum):
    """Security validation levels for queries."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


@dataclass
class SearchQuery:
    """Individual search query with metadata."""
    query_id: str = field(default_factory=lambda: str(uuid4()))
    query_type: QueryType = QueryType.NAME_SEARCH
    query_string: str = ""
    target_connectors: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # 1=high, 2=medium, 3=low
    security_level: SecurityLevel = SecurityLevel.SAFE
    created_at: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str = ""

    def __post_init__(self):
        """Validate search query data."""
        if not self.query_string.strip():
            raise ValueError("Query string cannot be empty")
        if not self.target_connectors:
            raise ValueError("Query must have at least one target connector")
        if self.priority not in [1, 2, 3]:
            raise ValueError("Priority must be 1, 2, or 3")

    def get_query_hash(self) -> str:
        """Generate hash for query deduplication."""
        content = f"{self.query_type}:{self.query_string}:{','.join(sorted(self.target_connectors))}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "query_id": self.query_id,
            "query_type": self.query_type.value,
            "query_string": self.query_string,
            "target_connectors": self.target_connectors,
            "parameters": self.parameters,
            "priority": self.priority,
            "security_level": self.security_level.value,
            "created_at": self.created_at.isoformat(),
            "correlation_id": self.correlation_id
        }


@dataclass
class QueryPlan:
    """Complete query plan for an investigation."""
    investigation_id: str
    correlation_id: str
    queries: List[SearchQuery] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    estimated_duration_minutes: int = 0
    total_queries: int = 0

    def add_query(self, query: SearchQuery):
        """Add a query to the plan."""
        query.correlation_id = self.correlation_id
        self.queries.append(query)
        self.total_queries = len(self.queries)

    def get_queries_by_priority(self, priority: int) -> List[SearchQuery]:
        """Get queries filtered by priority."""
        return [q for q in self.queries if q.priority == priority]

    def estimate_duration(self) -> int:
        """Estimate total execution duration in minutes."""
        # Base estimates per query type (in minutes)
        duration_map = {
            QueryType.NAME_SEARCH: 2,
            QueryType.USERNAME_SEARCH: 1,
            QueryType.EMAIL_SEARCH: 3,
            QueryType.PHONE_SEARCH: 2,
            QueryType.DOMAIN_SEARCH: 1,
            QueryType.COMPANY_SEARCH: 2,
            QueryType.LOCATION_SEARCH: 1,
            QueryType.COMPOSITE_SEARCH: 4
        }
        
        total_minutes = 0
        for query in self.queries:
            total_minutes += duration_map.get(query.query_type, 2)
        
        self.estimated_duration_minutes = total_minutes
        return total_minutes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "investigation_id": self.investigation_id,
            "correlation_id": self.correlation_id,
            "queries": [q.to_dict() for q in self.queries],
            "created_at": self.created_at.isoformat(),
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "total_queries": self.total_queries
        }


class ValidationError(Exception):
    """Validation error for input data."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation failed for {field}: {message}")


class SecurityValidationError(Exception):
    """Security validation error for queries."""
    def __init__(self, query: str, reason: str):
        self.query = query
        self.reason = reason
        super().__init__(f"Security validation failed: {reason}")


class DiscoveryEngine:
    """
    Core engine for generating OSINT search queries.

    Purpose
    - Transform seed identifiers into actionable search queries
    - Map queries to appropriate connectors based on capabilities
    - Apply security validation and rate limiting

    Invariants
    - All output queries must pass security validation
    - Every query must have valid target connectors
    - Query generation must be deterministic given same input
    - No sensitive data should leak into query strings

    Failure Modes
    - Invalid input data → ValidationError with specific field information
    - No available connectors → returns empty plan with appropriate logging
    - Security validation failure → SecurityValidationError with reason
    - Connector registry unavailable → system logs error and fails gracefully

    Debug Notes
    - Use correlation_id to trace query generation through the system
    - Monitor query_generation_time metrics for performance issues
    - Check security_validation_failed alerts for potential attacks
    - Review query_distribution metrics for connector balance

    Design Tradeoffs
    - Chose comprehensive query generation over minimal set for maximum discovery
    - Tradeoff: Higher resource usage but better investigation coverage
    - Mitigation: Priority system and rate limiting prevent resource exhaustion
    - Review trigger: If average query count exceeds 50 per investigation, optimize strategy
    """

    def __init__(self, connector_registry: ConnectorRegistry):
        """Initialize discovery engine with connector registry."""
        self.connector_registry = connector_registry
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Security patterns for query validation
        self._blocked_patterns = [
            r'(?i)(password|secret|token|key|auth)\s*[:=]\s*\S+',
            r'(?i)(drop\s+table|delete\s+from|insert\s+into)',
            r'(?i)(javascript:|data:|vbscript:)',
            r'<script[^>]*>.*?</script>',
            r'(?i)(union\s+select|exec\s*\(|system\s*\()'
        ]
        
        # Query templates for different search types
        self._query_templates = {
            QueryType.NAME_SEARCH: [
                "{name}",
                "{name} site:linkedin.com",
                "{name} site:github.com",
                "{name} site:twitter.com",
                "\"{name}\""
            ],
            QueryType.USERNAME_SEARCH: [
                "{username}",
                "{username} site:github.com",
                "{username} site:twitter.com",
                "{username} site:linkedin.com",
                "user:{username}"
            ],
            QueryType.EMAIL_SEARCH: [
                "\"{email}\"",
                "{email} site:linkedin.com",
                "{email} site:github.com",
                "mailto:{email}"
            ],
            QueryType.PHONE_SEARCH: [
                "\"{phone}\"",
                "{phone} site:facebook.com",
                "{phone} site:linkedin.com",
                "phone:{phone}"
            ],
            QueryType.DOMAIN_SEARCH: [
                "site:{domain}",
                "{domain} email",
                "{domain} contact",
                "whois {domain}"
            ],
            QueryType.COMPANY_SEARCH: [
                "{company} site:linkedin.com",
                "{company} careers",
                "{company} team",
                "{company} employees"
            ],
            QueryType.LOCATION_SEARCH: [
                "{location} software engineer",
                "{location} developer",
                "{location} tech"
            ]
        }

    async def generate_query_plan(self, investigation_input: InvestigationInput, 
                                 correlation_id: Optional[str] = None) -> QueryPlan:
        """
        Generate complete query plan from investigation input.

        Summary
        - Validate input and create optimized search queries
        - Map queries to appropriate connectors
        - Apply security validation and deduplication

        Preconditions
        - investigation_input must have valid subject identifiers
        - connector_registry must be initialized with available connectors
        - correlation_id must be provided or generated

        Postconditions
        - Returns QueryPlan with validated, deduplicated queries
        - All queries have appropriate target connectors
        - Plan includes duration estimates and priority ordering

        Error cases
        - Invalid input → ValidationError with field details
        - No connectors available → returns empty plan with warning
        - Security validation fails → SecurityValidationError

        Idempotency: Deterministic - same input produces same plan
        Side effects: Logs query generation metrics and security events
        """
        start_time = datetime.utcnow()
        
        # Generate correlation ID if not provided
        if not correlation_id:
            correlation_id = str(uuid4())
        
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "discovery.generate_plan",
            "investigation_id": investigation_input.investigation_id
        })
        
        logger.info("starting query plan generation", {
            "input_validation": "starting",
            "subject_name": investigation_input.subject_identifiers.full_name
        })

        try:
            # Validate input
            await self._validate_input(investigation_input, correlation_id)
            
            # Create query plan
            plan = QueryPlan(
                investigation_id=investigation_input.investigation_id,
                correlation_id=correlation_id
            )
            
            # Generate queries for each identifier type
            await self._generate_name_queries(investigation_input, plan, correlation_id)
            await self._generate_username_queries(investigation_input, plan, correlation_id)
            await self._generate_email_queries(investigation_input, plan, correlation_id)
            await self._generate_phone_queries(investigation_input, plan, correlation_id)
            await self._generate_domain_queries(investigation_input, plan, correlation_id)
            await self._generate_company_queries(investigation_input, plan, correlation_id)
            await self._generate_location_queries(investigation_input, plan, correlation_id)
            await self._generate_composite_queries(investigation_input, plan, correlation_id)
            
            # Deduplicate queries
            await self._deduplicate_queries(plan, correlation_id)
            
            # Estimate duration
            plan.estimate_duration()
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info("query plan generation completed", {
                "total_queries": plan.total_queries,
                "estimated_duration_minutes": plan.estimated_duration_minutes,
                "duration_ms": duration_ms,
                "query_types": list(set(q.query_type.value for q in plan.queries))
            })
            
            return plan
            
        except (ValidationError, SecurityValidationError) as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error("query plan generation failed", {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "duration_ms": duration_ms
            })
            raise
        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error("unexpected error in query plan generation", {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "duration_ms": duration_ms
            })
            raise RuntimeError(f"Query plan generation failed: {str(e)}")

    async def _validate_input(self, investigation_input: InvestigationInput, 
                            correlation_id: str) -> None:
        """
        Validate investigation input data.

        Summary
        - Check required fields and data formats
        - Validate email, phone, and domain formats
        - Apply security checks to prevent malicious input

        Preconditions
        - investigation_input must be properly initialized
        - correlation_id must be valid for logging

        Postconditions
        - All validation passes or ValidationError is raised
        - Security events are logged for suspicious patterns

        Error cases
        - Missing required fields → ValidationError
        - Invalid data formats → ValidationError
        - Suspicious patterns → SecurityValidationError
        """
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "discovery.validate_input"
        })
        
        identifiers = investigation_input.subject_identifiers
        
        # Validate required fields
        if not identifiers.full_name or len(identifiers.full_name.strip()) < 2:
            raise ValidationError("full_name", "Full name must be at least 2 characters")
        
        if len(identifiers.full_name) > 100:
            raise ValidationError("full_name", "Full name cannot exceed 100 characters")
        
        # Validate email addresses
        for i, email in enumerate(identifiers.email_addresses):
            if not validate_email(email):
                raise ValidationError(f"email_addresses[{i}]", f"Invalid email format: {email}")
        
        # Validate phone numbers
        for i, phone in enumerate(identifiers.phone_numbers):
            if not validate_phone(phone):
                raise ValidationError(f"phone_numbers[{i}]", f"Invalid phone format: {phone}")
        
        # Validate domains
        for i, domain in enumerate(identifiers.known_domains):
            if not validate_domain(domain):
                raise ValidationError(f"known_domains[{i}]", f"Invalid domain format: {domain}")
        
        # Security validation
        combined_input = f"{identifiers.full_name} {' '.join(identifiers.known_usernames)} {' '.join(identifiers.email_addresses)}"
        await self._security_validate(combined_input, correlation_id)
        
        logger.debug("input validation completed", {
            "name_length": len(identifiers.full_name),
            "username_count": len(identifiers.known_usernames),
            "email_count": len(identifiers.email_addresses),
            "phone_count": len(identifiers.phone_numbers),
            "domain_count": len(identifiers.known_domains)
        })

    async def _security_validate(self, text: str, correlation_id: str) -> None:
        """
        Apply security validation to input text.

        Summary
        - Check for blocked patterns and malicious content
        - Log security events for suspicious patterns
        - Raise SecurityValidationError for blocked content

        Preconditions
        - text must be non-empty string
        - correlation_id must be valid for audit logging

        Postconditions
        - Text passes security checks or exception is raised
        - Security events are logged for audit trail

        Error cases
        - Blocked pattern detected → SecurityValidationError
        - Suspicious pattern → SecurityValidationError
        """
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "discovery.security_validate"
        })
        
        # Check blocked patterns
        for pattern in self._blocked_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                logger.warning("blocked pattern detected", {
                    "pattern": pattern,
                    "text_sample": text[:100] + "..." if len(text) > 100 else text
                })
                raise SecurityValidationError(text, f"Contains blocked pattern: {pattern}")
        
        # Additional security checks
        if len(text) > 1000:
            logger.warning("suspiciously long input detected", {
                "text_length": len(text)
            })
            raise SecurityValidationError(text, "Input too long")
        
        # Check for potential injection attempts
        if any(char in text for char in ['<', '>', '"', "'", '&'] * 5):
            logger.warning("potential injection attempt detected", {
                "suspicious_chars": True
            })
            raise SecurityValidationError(text, "Contains suspicious character patterns")

    async def _generate_name_queries(self, investigation_input: InvestigationInput, 
                                   plan: QueryPlan, correlation_id: str) -> None:
        """Generate name-based search queries."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "discovery.generate_name_queries"
        })
        
        name = investigation_input.subject_identifiers.full_name
        templates = self._query_templates[QueryType.NAME_SEARCH]
        
        # Get connectors that support person searches
        target_connectors = []
        for connector in self.connector_registry.get_connectors_by_type(ConnectorEntityType.PERSON):
            target_connectors.append(connector.source_name)
        
        if not target_connectors:
            logger.warning("no connectors available for name searches")
            return
        
        for template in templates:
            query_string = template.format(name=name)
            
            # Security validation
            await self._security_validate(query_string, correlation_id)
            
            query = SearchQuery(
                query_type=QueryType.NAME_SEARCH,
                query_string=query_string,
                target_connectors=target_connectors.copy(),
                priority=1,  # High priority for name searches
                correlation_id=correlation_id
            )
            
            plan.add_query(query)
        
        logger.debug("name queries generated", {
            "query_count": len(templates),
            "name": redact_sensitive_data(name)
        })

    async def _generate_username_queries(self, investigation_input: InvestigationInput, 
                                       plan: QueryPlan, correlation_id: str) -> None:
        """Generate username-based search queries."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "discovery.generate_username_queries"
        })
        
        usernames = investigation_input.subject_identifiers.known_usernames
        if not usernames:
            return
        
        # Get connectors that support username searches
        target_connectors = []
        for connector in self.connector_registry.get_connectors_by_type(ConnectorEntityType.USERNAME):
            target_connectors.append(connector.source_name)
        
        if not target_connectors:
            logger.warning("no connectors available for username searches")
            return
        
        templates = self._query_templates[QueryType.USERNAME_SEARCH]
        
        for username in usernames:
            for template in templates:
                query_string = template.format(username=username)
                
                # Security validation
                await self._security_validate(query_string, correlation_id)
                
                query = SearchQuery(
                    query_type=QueryType.USERNAME_SEARCH,
                    query_string=query_string,
                    target_connectors=target_connectors.copy(),
                    priority=1,  # High priority for username searches
                    correlation_id=correlation_id
                )
                
                plan.add_query(query)
        
        logger.debug("username queries generated", {
            "username_count": len(usernames),
            "total_queries": len(usernames) * len(templates)
        })

    async def _generate_email_queries(self, investigation_input: InvestigationInput, 
                                    plan: QueryPlan, correlation_id: str) -> None:
        """Generate email-based search queries."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "discovery.generate_email_queries"
        })
        
        emails = investigation_input.subject_identifiers.email_addresses
        if not emails:
            return
        
        # Get connectors that support email searches
        target_connectors = []
        for connector in self.connector_registry.get_connectors_by_type(ConnectorEntityType.EMAIL_ADDRESS):
            target_connectors.append(connector.source_name)
        
        if not target_connectors:
            logger.warning("no connectors available for email searches")
            return
        
        templates = self._query_templates[QueryType.EMAIL_SEARCH]
        
        for email in emails:
            for template in templates:
                query_string = template.format(email=email)
                
                # Security validation
                await self._security_validate(query_string, correlation_id)
                
                query = SearchQuery(
                    query_type=QueryType.EMAIL_SEARCH,
                    query_string=query_string,
                    target_connectors=target_connectors.copy(),
                    priority=2,  # Medium priority for email searches
                    correlation_id=correlation_id
                )
                
                plan.add_query(query)
        
        logger.debug("email queries generated", {
            "email_count": len(emails),
            "total_queries": len(emails) * len(templates)
        })

    async def _generate_phone_queries(self, investigation_input: InvestigationInput, 
                                    plan: QueryPlan, correlation_id: str) -> None:
        """Generate phone-based search queries."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "discovery.generate_phone_queries"
        })
        
        phones = investigation_input.subject_identifiers.phone_numbers
        if not phones:
            return
        
        # Get connectors that support phone searches
        target_connectors = []
        for connector in self.connector_registry.get_connectors_by_type(ConnectorEntityType.PHONE_NUMBER):
            target_connectors.append(connector.source_name)
        
        if not target_connectors:
            logger.warning("no connectors available for phone searches")
            return
        
        templates = self._query_templates[QueryType.PHONE_SEARCH]
        
        for phone in phones:
            for template in templates:
                query_string = template.format(phone=phone)
                
                # Security validation
                await self._security_validate(query_string, correlation_id)
                
                query = SearchQuery(
                    query_type=QueryType.PHONE_SEARCH,
                    query_string=query_string,
                    target_connectors=target_connectors.copy(),
                    priority=2,  # Medium priority for phone searches
                    correlation_id=correlation_id
                )
                
                plan.add_query(query)
        
        logger.debug("phone queries generated", {
            "phone_count": len(phones),
            "total_queries": len(phones) * len(templates)
        })

    async def _generate_domain_queries(self, investigation_input: InvestigationInput, 
                                     plan: QueryPlan, correlation_id: str) -> None:
        """Generate domain-based search queries."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "discovery.generate_domain_queries"
        })
        
        domains = investigation_input.subject_identifiers.known_domains
        if not domains:
            return
        
        # Get connectors that support domain searches
        target_connectors = []
        for connector in self.connector_registry.get_connectors_by_type(ConnectorEntityType.DOMAIN):
            target_connectors.append(connector.source_name)
        
        if not target_connectors:
            logger.warning("no connectors available for domain searches")
            return
        
        templates = self._query_templates[QueryType.DOMAIN_SEARCH]
        
        for domain in domains:
            for template in templates:
                query_string = template.format(domain=domain)
                
                # Security validation
                await self._security_validate(query_string, correlation_id)
                
                query = SearchQuery(
                    query_type=QueryType.DOMAIN_SEARCH,
                    query_string=query_string,
                    target_connectors=target_connectors.copy(),
                    priority=2,  # Medium priority for domain searches
                    correlation_id=correlation_id
                )
                
                plan.add_query(query)
        
        logger.debug("domain queries generated", {
            "domain_count": len(domains),
            "total_queries": len(domains) * len(templates)
        })

    async def _generate_company_queries(self, investigation_input: InvestigationInput, 
                                      plan: QueryPlan, correlation_id: str) -> None:
        """Generate company-based search queries."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "discovery.generate_company_queries"
        })
        
        company = investigation_input.subject_identifiers.professional_hints.get("employer")
        if not company:
            return
        
        # Get connectors that support company searches
        target_connectors = []
        for connector in self.connector_registry.get_connectors_by_type(ConnectorEntityType.COMPANY):
            target_connectors.append(connector.source_name)
        
        if not target_connectors:
            logger.warning("no connectors available for company searches")
            return
        
        templates = self._query_templates[QueryType.COMPANY_SEARCH]
        
        for template in templates:
            query_string = template.format(company=company)
            
            # Security validation
            await self._security_validate(query_string, correlation_id)
            
            query = SearchQuery(
                query_type=QueryType.COMPANY_SEARCH,
                query_string=query_string,
                target_connectors=target_connectors.copy(),
                priority=2,  # Medium priority for company searches
                correlation_id=correlation_id
            )
            
            plan.add_query(query)
        
        logger.debug("company queries generated", {
            "company": company,
            "query_count": len(templates)
        })

    async def _generate_location_queries(self, investigation_input: InvestigationInput, 
                                       plan: QueryPlan, correlation_id: str) -> None:
        """Generate location-based search queries."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "discovery.generate_location_queries"
        })
        
        geo_hints = investigation_input.subject_identifiers.geographic_hints
        location_parts = []
        
        if geo_hints.get("city"):
            location_parts.append(geo_hints["city"])
        if geo_hints.get("region"):
            location_parts.append(geo_hints["region"])
        
        if not location_parts:
            return
        
        location = " ".join(location_parts)
        
        # Get connectors that support location searches
        target_connectors = []
        for connector in self.connector_registry.get_connectors_by_type(ConnectorEntityType.PERSON):
            target_connectors.append(connector.source_name)
        
        if not target_connectors:
            logger.warning("no connectors available for location searches")
            return
        
        templates = self._query_templates[QueryType.LOCATION_SEARCH]
        
        for template in templates:
            query_string = template.format(location=location)
            
            # Security validation
            await self._security_validate(query_string, correlation_id)
            
            query = SearchQuery(
                query_type=QueryType.LOCATION_SEARCH,
                query_string=query_string,
                target_connectors=target_connectors.copy(),
                priority=3,  # Low priority for location searches
                correlation_id=correlation_id
            )
            
            plan.add_query(query)
        
        logger.debug("location queries generated", {
            "location": location,
            "query_count": len(templates)
        })

    async def _generate_composite_queries(self, investigation_input: InvestigationInput, 
                                        plan: QueryPlan, correlation_id: str) -> None:
        """Generate composite search queries combining multiple identifiers."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "discovery.generate_composite_queries"
        })
        
        name = investigation_input.subject_identifiers.full_name
        company = investigation_input.subject_identifiers.professional_hints.get("employer")
        city = investigation_input.subject_identifiers.geographic_hints.get("city")
        
        composite_queries = []
        
        # Name + Company
        if company:
            composite_queries.append(f"\"{name}\" {company}")
            composite_queries.append(f"\"{name}\" site:linkedin.com {company}")
        
        # Name + Location
        if city:
            composite_queries.append(f"\"{name}\" {city}")
            composite_queries.append(f"\"{name}\" software engineer {city}")
        
        # Name + Company + Location
        if company and city:
            composite_queries.append(f"\"{name}\" {company} {city}")
        
        if not composite_queries:
            return
        
        # Get connectors that support person searches
        target_connectors = []
        for connector in self.connector_registry.get_connectors_by_type(ConnectorEntityType.PERSON):
            target_connectors.append(connector.source_name)
        
        if not target_connectors:
            logger.warning("no connectors available for composite searches")
            return
        
        for query_string in composite_queries:
            # Security validation
            await self._security_validate(query_string, correlation_id)
            
            query = SearchQuery(
                query_type=QueryType.COMPOSITE_SEARCH,
                query_string=query_string,
                target_connectors=target_connectors.copy(),
                priority=1,  # High priority for composite searches
                correlation_id=correlation_id
            )
            
            plan.add_query(query)
        
        logger.debug("composite queries generated", {
            "query_count": len(composite_queries),
            "has_company": bool(company),
            "has_location": bool(city)
        })

    async def _deduplicate_queries(self, plan: QueryPlan, correlation_id: str) -> None:
        """Remove duplicate queries from the plan."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "discovery.deduplicate_queries"
        })
        
        original_count = len(plan.queries)
        seen_hashes = set()
        deduplicated_queries = []
        
        for query in plan.queries:
            query_hash = query.get_query_hash()
            if query_hash not in seen_hashes:
                seen_hashes.add(query_hash)
                deduplicated_queries.append(query)
        
        plan.queries = deduplicated_queries
        plan.total_queries = len(plan.queries)
        
        duplicates_removed = original_count - plan.total_queries
        
        logger.debug("query deduplication completed", {
            "original_count": original_count,
            "final_count": plan.total_queries,
            "duplicates_removed": duplicates_removed
        })

    def get_engine_status(self) -> Dict[str, Any]:
        """Get discovery engine status and metrics."""
        return {
            "engine_name": "DiscoveryEngine",
            "available_connectors": len(self.connector_registry.list_connectors()),
            "query_templates_count": len(self._query_templates),
            "blocked_patterns_count": len(self._blocked_patterns),
            "supported_query_types": [qt.value for qt in QueryType]
        }
