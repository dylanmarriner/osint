"""
Core data models for OSINT framework entities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from uuid import uuid4
import json
import hashlib


class VerificationStatus(Enum):
    """Entity verification status levels."""
    VERIFIED = "verified"
    PROBABLE = "probable"
    POSSIBLE = "possible"
    UNLIKELY = "unlikely"


class RiskLevel(Enum):
    """Risk assessment levels."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EntityType(Enum):
    """Types of entities that can be discovered."""
    PERSON = "person"
    COMPANY = "company"
    DOMAIN = "domain"
    SOCIAL_PROFILE = "social_profile"
    EMAIL_ADDRESS = "email_address"
    PHONE_NUMBER = "phone_number"
    USERNAME = "username"


@dataclass
class SubjectIdentifiers:
    """Seed identifiers for investigation."""
    full_name: str
    known_usernames: List[str] = field(default_factory=list)
    email_addresses: List[str] = field(default_factory=list)
    phone_numbers: List[str] = field(default_factory=list)
    geographic_hints: Dict[str, str] = field(default_factory=dict)
    professional_hints: Dict[str, str] = field(default_factory=dict)
    known_domains: List[str] = field(default_factory=list)


@dataclass
class InvestigationConstraints:
    """Constraints and limits for investigation."""
    exclude_sensitive_attributes: bool = True
    exclude_minors: bool = True
    max_search_depth: int = 5
    retention_days: int = 30


@dataclass
class ConfidenceThresholds:
    """Minimum confidence thresholds."""
    minimum_entity_confidence: float = 70.0
    minimum_source_confidence: float = 60.0


@dataclass
class InvestigationInput:
    """Complete input for OSINT investigation."""
    investigation_id: str = field(default_factory=lambda: str(uuid4()))
    subject_identifiers: SubjectIdentifiers = field(default_factory=SubjectIdentifiers)
    investigation_constraints: InvestigationConstraints = field(default_factory=InvestigationConstraints)
    confidence_thresholds: ConfidenceThresholds = field(default_factory=ConfidenceThresholds)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "investigation_id": self.investigation_id,
            "subject_identifiers": {
                "full_name": self.subject_identifiers.full_name,
                "known_usernames": self.subject_identifiers.known_usernames,
                "email_addresses": self.subject_identifiers.email_addresses,
                "phone_numbers": self.subject_identifiers.phone_numbers,
                "geographic_hints": self.subject_identifiers.geographic_hints,
                "professional_hints": self.subject_identifiers.professional_hints,
                "known_domains": self.subject_identifiers.known_domains
            },
            "investigation_constraints": {
                "exclude_sensitive_attributes": self.investigation_constraints.exclude_sensitive_attributes,
                "exclude_minors": self.investigation_constraints.exclude_minors,
                "max_search_depth": self.investigation_constraints.max_search_depth,
                "retention_days": self.investigation_constraints.retention_days
            },
            "confidence_thresholds": {
                "minimum_entity_confidence": self.confidence_thresholds.minimum_entity_confidence,
                "minimum_source_confidence": self.confidence_thresholds.minimum_source_confidence
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvestigationInput":
        """Create from dictionary representation."""
        subject_data = data.get("subject_identifiers", {})
        constraints_data = data.get("investigation_constraints", {})
        thresholds_data = data.get("confidence_thresholds", {})

        return cls(
            investigation_id=data.get("investigation_id", str(uuid4())),
            subject_identifiers=SubjectIdentifiers(
                full_name=subject_data.get("full_name", ""),
                known_usernames=subject_data.get("known_usernames", []),
                email_addresses=subject_data.get("email_addresses", []),
                phone_numbers=subject_data.get("phone_numbers", []),
                geographic_hints=subject_data.get("geographic_hints", {}),
                professional_hints=subject_data.get("professional_hints", {}),
                known_domains=subject_data.get("known_domains", [])
            ),
            investigation_constraints=InvestigationConstraints(
                exclude_sensitive_attributes=constraints_data.get("exclude_sensitive_attributes", True),
                exclude_minors=constraints_data.get("exclude_minors", True),
                max_search_depth=constraints_data.get("max_search_depth", 5),
                retention_days=constraints_data.get("retention_days", 30)
            ),
            confidence_thresholds=ConfidenceThresholds(
                minimum_entity_confidence=thresholds_data.get("minimum_entity_confidence", 70.0),
                minimum_source_confidence=thresholds_data.get("minimum_source_confidence", 60.0)
            )
        )


@dataclass
class SearchResult:
    """Result from a source connector."""
    url: str
    title: str
    content: str
    metadata: Dict[str, Any]
    confidence: float
    source_type: str
    retrieved_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate search result data."""
        if not self.url:
            raise ValueError("URL cannot be empty")
        if not self.source_type:
            raise ValueError("Source type cannot be empty")
        if not 0 <= self.confidence <= 100:
            raise ValueError("Confidence must be between 0 and 100")

    def get_content_hash(self) -> str:
        """Generate SHA-256 hash of content for deduplication."""
        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
            "confidence": self.confidence,
            "source_type": self.source_type,
            "retrieved_at": self.retrieved_at.isoformat(),
            "content_hash": self.get_content_hash()
        }


@dataclass
class Entity:
    """Normalized entity discovered during investigation."""
    id: str = field(default_factory=lambda: str(uuid4()))
    investigation_id: str = ""
    entity_type: EntityType = EntityType.PERSON
    attributes: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    verification_status: VerificationStatus = VerificationStatus.POSSIBLE
    sources: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate entity data."""
        if not 0 <= self.confidence_score <= 100:
            raise ValueError("Confidence score must be between 0 and 100")
        if not self.attributes:
            raise ValueError("Entity must have at least one attribute")

    def add_source(self, source_url: str, source_type: str, confidence: float):
        """Add a source reference to this entity."""
        source_ref = {
            "url": source_url,
            "source_type": source_type,
            "confidence": confidence,
            "added_at": datetime.utcnow().isoformat()
        }
        self.sources.append(source_ref)
        self.updated_at = datetime.utcnow()

    def update_confidence(self, new_score: float):
        """Update confidence score and verification status."""
        self.confidence_score = new_score
        self.updated_at = datetime.utcnow()
        
        # Update verification status based on confidence
        if new_score >= 90:
            self.verification_status = VerificationStatus.VERIFIED
        elif new_score >= 75:
            self.verification_status = VerificationStatus.PROBABLE
        elif new_score >= 60:
            self.verification_status = VerificationStatus.POSSIBLE
        else:
            self.verification_status = VerificationStatus.UNLIKELY

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "investigation_id": self.investigation_id,
            "entity_type": self.entity_type.value,
            "attributes": self.attributes,
            "confidence_score": self.confidence_score,
            "verification_status": self.verification_status.value,
            "sources": self.sources,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class ExposureCategory:
    """Exposure category analysis."""
    category_name: str
    exposed_count: int
    risk_level: RiskLevel
    sources: List[str]
    risk_score: float = 0.0

    def calculate_risk_score(self) -> float:
        """Calculate risk score based on exposure count and sources."""
        base_score = min(100, self.exposed_count * 20)
        source_multiplier = 1.0 + (len(self.sources) * 0.1)
        self.risk_score = min(100, base_score * source_multiplier)
        return self.risk_score


@dataclass
class RemediationRecommendation:
    """Remediation recommendation for identified risks."""
    priority: str
    category: str
    action: str
    platforms: List[str]
    estimated_impact: float
    implementation_difficulty: str
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "priority": self.priority,
            "category": self.category,
            "action": self.action,
            "platforms": self.platforms,
            "estimated_impact": self.estimated_impact,
            "implementation_difficulty": self.implementation_difficulty,
            "description": self.description
        }


@dataclass
class TimelineEntry:
    """Timeline entry for subject activity."""
    date: str
    platform: str
    activity: str
    privacy_implication: str
    source_url: str
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "date": self.date,
            "platform": self.platform,
            "activity": self.activity,
            "privacy_implication": self.privacy_implication,
            "source_url": self.source_url,
            "confidence": self.confidence
        }


@dataclass
class ExecutiveSummary:
    """Executive summary of investigation findings."""
    risk_level: RiskLevel
    total_findings: int
    high_risk_findings: int
    key_exposures: List[str]
    recommendation_priority: str
    overall_confidence: float = 0.0

    def calculate_overall_confidence(self, entities: List[Entity]) -> float:
        """Calculate overall confidence from all entities."""
        if not entities:
            return 0.0
        total_confidence = sum(entity.confidence_score for entity in entities)
        self.overall_confidence = total_confidence / len(entities)
        return self.overall_confidence


@dataclass
class InvestigationReport:
    """Complete investigation report."""
    investigation_id: str
    generated_at: datetime = field(default_factory=datetime.utcnow)
    report_version: str = "1.0"
    executive_summary: ExecutiveSummary = field(default_factory=ExecutiveSummary)
    identity_inventory: Dict[str, List[Entity]] = field(default_factory=dict)
    exposure_analysis: Dict[str, ExposureCategory] = field(default_factory=dict)
    activity_timeline: List[TimelineEntry] = field(default_factory=list)
    remediation_recommendations: List[RemediationRecommendation] = field(default_factory=list)
    detailed_findings: List[Entity] = field(default_factory=list)
    source_references: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "report_metadata": {
                "investigation_id": self.investigation_id,
                "generated_at": self.generated_at.isoformat(),
                "report_version": self.report_version
            },
            "executive_summary": {
                "risk_level": self.executive_summary.risk_level.value,
                "total_findings": self.executive_summary.total_findings,
                "high_risk_findings": self.executive_summary.high_risk_findings,
                "key_exposures": self.executive_summary.key_exposures,
                "recommendation_priority": self.executive_summary.recommendation_priority,
                "overall_confidence": self.executive_summary.overall_confidence
            },
            "identity_inventory": {
                status: [entity.to_dict() for entity in entities]
                for status, entities in self.identity_inventory.items()
            },
            "exposure_analysis": {
                category: ExposureCategory(
                    category_name=data.category_name,
                    exposed_count=data.exposed_count,
                    risk_level=data.risk_level,
                    sources=data.sources,
                    risk_score=data.risk_score
                ).to_dict() if not isinstance(data, ExposureCategory) else data.to_dict()
                for category, data in self.exposure_analysis.items()
            },
            "activity_timeline": [entry.to_dict() for entry in self.activity_timeline],
            "remediation_recommendations": [rec.to_dict() for rec in self.remediation_recommendations],
            "detailed_findings": [entity.to_dict() for entity in self.detailed_findings],
            "source_references": self.source_references
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        md = f"""# OSINT Privacy Risk Assessment Report

## Executive Summary
**Risk Level**: {self._get_risk_emoji(self.executive_summary.risk_level)} {self.executive_summary.risk_level.value}  
**Total Findings**: {self.executive_summary.total_findings}  
**High Risk Findings**: {self.executive_summary.high_risk_findings}  
**Overall Confidence**: {self.executive_summary.overall_confidence:.1f}%

### Key Exposures Identified
"""
        for exposure in self.executive_summary.key_exposures:
            md += f"- **{exposure}**\n"

        md += f"""
### Immediate Recommendations
"""
        for i, rec in enumerate(self.remediation_recommendations[:5], 1):
            md += f"{i}. **{rec.action}** (Impact: {rec.estimated_impact}%, Difficulty: {rec.implementation_difficulty})\n"

        md += f"""
## Identity Inventory
"""
        for status, entities in self.identity_inventory.items():
            md += f"### {status.title()} Identities ({len(entities)})\n"
            for entity in entities[:3]:  # Show top 3
                md += f"- **{entity.attributes.get('name', 'Unknown')}** on {entity.attributes.get('platform', 'Unknown')} (Confidence: {entity.confidence_score}%)\n"

        md += f"""
## Exposure Analysis
"""
        for category, exposure in self.exposure_analysis.items():
            md += f"### {category.replace('_', ' ').title()}\n"
            md += f"- **Exposed Count**: {exposure.exposed_count}\n"
            md += f"- **Risk Level**: {exposure.risk_level.value}\n"
            md += f"- **Risk Score**: {exposure.risk_score:.1f}\n"

        return md

    def _get_risk_emoji(self, risk_level: RiskLevel) -> str:
        """Get emoji for risk level."""
        emoji_map = {
            RiskLevel.HIGH: "🔴",
            RiskLevel.MEDIUM: "🟡",
            RiskLevel.LOW: "🟢"
        }
        return emoji_map.get(risk_level, "⚪")


# Validation functions
def validate_email(email: str) -> bool:
    """Validate email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Validate phone number format (E.164)."""
    import re
    pattern = r'^\+?[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone))


def validate_domain(domain: str) -> bool:
    """Validate domain format."""
    import re
    pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$'
    return bool(re.match(pattern, domain))


def redact_sensitive_data(text: str) -> str:
    """Redact sensitive patterns from text."""
    import re
    
    patterns = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
    }
    
    redacted = text
    for pattern_type, pattern in patterns.items():
        redacted = re.sub(pattern, f'[REDACTED_{pattern_type.upper()}]', redacted)
    
    return redacted
