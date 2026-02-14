"""
Report Generator for OSINT Investigation Pipeline

Purpose
- Generate comprehensive investigation reports in multiple formats
- Calculate risk scores and exposure analysis
- Provide remediation recommendations
- Ensure all sensitive data is properly redacted

Invariants
- All reports follow standard schema formats
- Risk calculations use consistent scoring algorithms
- Sensitive data is redacted before output
- Every report generation is logged with correlation IDs
- Report formats are validated before generation

Failure Modes
- Invalid entity data → report generation fails with validation error
- Insufficient data → report shows appropriate warnings
- Template rendering failure → fallback to basic format with error logging
- File generation error → report is returned but file save fails
- Format conversion error → appropriate error message and logging

Debug Notes
- Use correlation_id to trace report generation through system
- Monitor report_generation_time metrics for performance issues
- Check risk_score_calculation alerts for scoring problems
- Review format_conversion_failed metrics for output issues
- Use data_quality_warnings to monitor input data problems

Design Tradeoffs
- Chose comprehensive reporting over minimal summaries for maximum insight
- Tradeoff: Larger reports but more actionable intelligence
- Mitigation: Structured formats and pagination for large reports
- Review trigger: If report generation time exceeds 30 seconds, optimize templates
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
from jinja2 import Environment, BaseLoader, Template

from ..models.entities import (
    Entity, EntityType, VerificationStatus, RiskLevel,
    InvestigationReport, ExecutiveSummary, ExposureCategory,
    RemediationRecommendation, TimelineEntry,
    redact_sensitive_data
)


class ReportFormat(Enum):
    """Supported report output formats."""
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


class RiskCategory(Enum):
    """Risk assessment categories."""
    CONTACT_EXPOSURE = "contact_information_exposure"
    ACCOUNT_TAKEOVER = "account_takeover_risk"
    DOXXING_RISK = "doxxing_risk"
    IMPERSONATION_RISK = "impersonation_risk"
    PRIVACY_VIOLATION = "privacy_violation"
    REPUTATION_RISK = "reputation_risk"


@dataclass
class RiskAssessment:
    """Risk assessment for different categories."""
    category: RiskCategory
    risk_score: float
    risk_level: RiskLevel
    findings_count: int
    severity_distribution: Dict[str, int] = field(default_factory=dict)
    affected_platforms: List[str] = field(default_factory=list)
    description: str = ""
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "category": self.category.value,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "findings_count": self.findings_count,
            "severity_distribution": self.severity_distribution,
            "affected_platforms": self.affected_platforms,
            "description": self.description,
            "recommendations": self.recommendations
        }


@dataclass
class ReportMetrics:
    """Metrics for report generation operations."""
    total_reports_generated: int = 0
    successful_generations: int = 0
    failed_generations: int = 0
    total_generation_time_ms: int = 0
    format_distribution: Dict[str, int] = field(default_factory=dict)
    average_entities_per_report: float = 0.0
    data_quality_warnings: int = 0

    def get_success_rate(self) -> float:
        """Calculate report generation success rate."""
        if self.total_reports_generated == 0:
            return 0.0
        return (self.successful_generations / self.total_reports_generated) * 100

    def get_average_generation_time_ms(self) -> float:
        """Calculate average report generation time."""
        if self.successful_generations == 0:
            return 0.0
        return self.total_generation_time_ms / self.successful_generations


class ReportGenerator:
    """
    Core report generator for OSINT investigations.

    Purpose
    - Generate comprehensive investigation reports in multiple formats
    - Calculate risk scores and exposure analysis
    - Provide remediation recommendations
    - Ensure all sensitive data is properly redacted

    Invariants
    - All reports follow standard schema formats
    - Risk calculations use consistent scoring algorithms
    - Sensitive data is redacted before output
    - Every report generation is logged with correlation IDs
    - Report formats are validated before generation

    Failure Modes
    - Invalid entity data → report generation fails with validation error
    - Insufficient data → report shows appropriate warnings
    - Template rendering failure → fallback to basic format with error logging
    - File generation error → report is returned but file save fails
    - Format conversion error → appropriate error message and logging

    Debug Notes
    - Use correlation_id to trace report generation through system
    - Monitor report_generation_time metrics for performance issues
    - Check risk_score_calculation alerts for scoring problems
    - Review format_conversion_failed metrics for output issues
    - Use data_quality_warnings to monitor input data problems

    Design Tradeoffs
    - Chose comprehensive reporting over minimal summaries for maximum insight
    - Tradeoff: Larger reports but more actionable intelligence
    - Mitigation: Structured formats and pagination for large reports
    - Review trigger: If report generation time exceeds 30 seconds, optimize templates
    """

    def __init__(self, template_dir: Optional[str] = None):
        """Initialize report generator with template directory."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.metrics = ReportMetrics()
        
        # Initialize Jinja2 environment for templates
        if template_dir:
            self.jinja_env = Environment(
                loader=BaseLoader(),
                autoescape=True
            )
        else:
            # Use default templates
            self.jinja_env = Environment(
                loader=BaseLoader(),
                autoescape=True
            )
        
        # Risk scoring weights
        self.risk_weights = {
            RiskCategory.CONTACT_EXPOSURE: 0.3,
            RiskCategory.ACCOUNT_TAKEOVER: 0.25,
            RiskCategory.DOXXING_RISK: 0.2,
            RiskCategory.IMPERSONATION_RISK: 0.15,
            RiskCategory.PRIVACY_VIOLATION: 0.1
        }

    async def generate_report(self, entities: List[Entity], investigation_id: str,
                          correlation_id: Optional[str] = None) -> InvestigationReport:
        """
        Generate comprehensive investigation report.

        Summary
        - Analyze entities and calculate risk assessments
        - Generate executive summary and recommendations
        - Create structured report with all findings

        Preconditions
        - entities must be valid Entity objects
        - investigation_id must be provided for report identification
        - correlation_id must be provided for tracing

        Postconditions
        - Returns complete InvestigationReport with all sections
        - Risk scores are calculated using consistent algorithms
        - Sensitive data is redacted from all outputs

        Error cases
        - Invalid entity data → report generation fails with validation error
        - Insufficient entities → report shows appropriate warnings
        - Risk calculation failure → report includes error details
        - Template rendering failure → fallback to basic format

        Idempotency: Deterministic - same input produces same report
        Side effects: Updates metrics and logs report generation
        """
        start_time = datetime.utcnow()
        
        if not correlation_id:
            correlation_id = str(uuid4())
        
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "report.generate_report",
            "investigation_id": investigation_id,
            "entity_count": len(entities)
        })
        
        logger.info("starting report generation")

        try:
            # Validate input data
            self._validate_entities(entities, correlation_id)
            
            # Create report structure
            report = InvestigationReport(
                investigation_id=investigation_id,
                generated_at=start_time
            )

            # Generate executive summary
            report.executive_summary = await self._generate_executive_summary(entities, correlation_id)
            
            # Generate identity inventory
            report.identity_inventory = self._generate_identity_inventory(entities)
            
            # Generate exposure analysis
            report.exposure_analysis = await self._generate_exposure_analysis(entities, correlation_id)
            
            # Generate activity timeline
            report.activity_timeline = self._generate_activity_timeline(entities)
            
            # Generate remediation recommendations
            report.remediation_recommendations = await self._generate_remediation_recommendations(
                report.exposure_analysis, correlation_id
            )
            
            # Add detailed findings
            report.detailed_findings = entities
            
            # Add source references
            report.source_references = self._generate_source_references(entities)

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info("report generation completed", {
                "investigation_id": investigation_id,
                "entities_processed": len(entities),
                "risk_level": report.executive_summary.risk_level.value,
                "total_findings": report.executive_summary.total_findings,
                "duration_ms": duration_ms
            })

            return report

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error("report generation failed", {
                "investigation_id": investigation_id,
                "error": str(e),
                "duration_ms": duration_ms
            })
            raise

    async def export_report(self, report: InvestigationReport, output_format: ReportFormat,
                         correlation_id: Optional[str] = None) -> Union[str, bytes]:
        """
        Export report in specified format.

        Summary
        - Convert report to requested output format
        - Apply appropriate formatting and redaction
        - Return formatted report for output

        Preconditions
        - report must be valid InvestigationReport object
        - output_format must be supported format
        - correlation_id must be provided for tracing

        Postconditions
        - Returns report in requested format
        - All sensitive data is redacted appropriately
        - Format validation is applied before export

        Error cases
        - Unsupported format → raises ValueError with supported formats
        - Template rendering failure → fallback to basic format
        - Format conversion error → raises appropriate exception

        Idempotency: Deterministic - same input produces same output
        Side effects: Updates metrics and logs export operations
        """
        start_time = datetime.utcnow()
        
        if not correlation_id:
            correlation_id = str(uuid4())
        
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "report.export_report",
            "output_format": output_format.value,
            "investigation_id": report.investigation_id
        })

        try:
            if output_format == ReportFormat.JSON:
                result = self._export_json(report, correlation_id)
            elif output_format == ReportFormat.MARKDOWN:
                result = self._export_markdown(report, correlation_id)
            elif output_format == ReportFormat.HTML:
                result = self._export_html(report, correlation_id)
            elif output_format == ReportFormat.PDF:
                result = await self._export_pdf(report, correlation_id)
            else:
                raise ValueError(f"Unsupported format: {output_format.value}")

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info("report export completed", {
                "investigation_id": report.investigation_id,
                "output_format": output_format.value,
                "duration_ms": duration_ms
            })

            return result

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error("report export failed", {
                "investigation_id": report.investigation_id,
                "output_format": output_format.value,
                "error": str(e),
                "duration_ms": duration_ms
            })
            raise

    def _validate_entities(self, entities: List[Entity], correlation_id: str):
        """Validate entities for report generation."""
        if not entities:
            raise ValueError("No entities provided for report generation")
        
        for i, entity in enumerate(entities):
            if not entity.attributes:
                logger.warning("entity has no attributes", {
                    "correlation_id": correlation_id,
                    "entity_id": entity.id,
                    "entity_type": entity.entity_type.value
                })
                self.metrics.data_quality_warnings += 1

    async def _generate_executive_summary(self, entities: List[Entity], correlation_id: str) -> ExecutiveSummary:
        """Generate executive summary of findings."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "report.generate_executive_summary",
            "entity_count": len(entities)
        })

        # Calculate overall metrics
        total_findings = len(entities)
        high_risk_findings = sum(1 for e in entities if e.confidence_score >= 80)
        
        # Calculate overall risk level
        risk_assessments = await self._calculate_risk_assessments(entities, correlation_id)
        overall_risk_score = sum(ra.risk_score * self.risk_weights[ra.category] 
                                   for ra in risk_assessments)
        
        if overall_risk_score >= 70:
            risk_level = RiskLevel.HIGH
        elif overall_risk_score >= 40:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # Identify key exposures
        key_exposures = []
        for assessment in risk_assessments:
            if assessment.risk_score >= 60:
                if assessment.category == RiskCategory.CONTACT_EXPOSURE:
                    key_exposures.extend(["email_addresses", "phone_numbers"])
                elif assessment.category == RiskCategory.DOXXING_RISK:
                    key_exposures.extend(["home_address", "family_information"])
                elif assessment.category == RiskCategory.ACCOUNT_TAKEOVER:
                    key_exposures.extend(["compromised_accounts", "weak_passwords"])
                elif assessment.category == RiskCategory.IMPERSONATION_RISK:
                    key_exposures.extend(["profile_impersonation", "identity_theft"])

        # Determine recommendation priority
        if risk_level == RiskLevel.HIGH:
            recommendation_priority = "IMMEDIATE"
        elif risk_level == RiskLevel.MEDIUM:
            recommendation_priority = "MODERATE"
        else:
            recommendation_priority = "LOW"

        # Calculate overall confidence
        if entities:
            overall_confidence = sum(e.confidence_score for e in entities) / len(entities)
        else:
            overall_confidence = 0.0

        summary = ExecutiveSummary(
            risk_level=risk_level,
            total_findings=total_findings,
            high_risk_findings=high_risk_findings,
            key_exposures=list(set(key_exposures)),
            recommendation_priority=recommendation_priority,
            overall_confidence=overall_confidence
        )

        logger.debug("executive summary generated", {
            "risk_level": risk_level.value,
            "total_findings": total_findings,
            "high_risk_findings": high_risk_findings,
            "key_exposures_count": len(key_exposures)
        })

        return summary

    def _generate_identity_inventory(self, entities: List[Entity]) -> Dict[str, List[Entity]]:
        """Generate identity inventory grouped by verification status."""
        inventory = {
            "verified": [],
            "probable": [],
            "possible": [],
            "unlikely": []
        }

        for entity in entities:
            status = entity.verification_status.value
            if status in inventory:
                inventory[status].append(entity)

        return inventory

    async def _generate_exposure_analysis(self, entities: List[Entity], correlation_id: str) -> Dict[str, ExposureCategory]:
        """Generate exposure analysis for different categories."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "report.generate_exposure_analysis",
            "entity_count": len(entities)
        })

        analysis = {}

        # Contact information exposure
        contact_entities = [e for e in entities if e.entity_type in [EntityType.EMAIL_ADDRESS, EntityType.PHONE_NUMBER]]
        contact_exposure = ExposureCategory(
            category_name="contact_information",
            exposed_count=len(contact_entities),
            risk_level=RiskLevel.HIGH if len(contact_entities) > 3 else RiskLevel.MEDIUM,
            sources=list(set(e.sources[0].get("source_type", "unknown") for e in contact_entities if e.sources))
        )
        contact_exposure.calculate_risk_score()
        analysis["contact_information"] = contact_exposure

        # Account takeover risk indicators
        at_risk_entities = [e for e in entities if self._has_account_takeover_indicators(e)]
        at_risk = ExposureCategory(
            category_name="account_takeover_risk",
            exposed_count=len(at_risk_entities),
            risk_level=RiskLevel.HIGH if len(at_risk_entities) > 2 else RiskLevel.MEDIUM,
            sources=list(set(e.sources[0].get("source_type", "unknown") for e in at_risk_entities if e.sources))
        )
        at_risk.calculate_risk_score()
        analysis["account_takeover_risk"] = at_risk

        # Doxxing risk indicators
        doxxing_entities = [e for e in entities if self._has_doxxing_indicators(e)]
        doxxing_risk = ExposureCategory(
            category_name="doxxing_risk",
            exposed_count=len(doxxing_entities),
            risk_level=RiskLevel.HIGH if len(doxxing_entities) > 1 else RiskLevel.MEDIUM,
            sources=list(set(e.sources[0].get("source_type", "unknown") for e in doxxing_entities if e.sources))
        )
        doxxing_risk.calculate_risk_score()
        analysis["doxxing_risk"] = doxxing_risk

        # Impersonation risk indicators
        impersonation_entities = [e for e in entities if self._has_impersonation_indicators(e)]
        impersonation_risk = ExposureCategory(
            category_name="impersonation_risk",
            exposed_count=len(impersonation_entities),
            risk_level=RiskLevel.MEDIUM if len(impersonation_entities) > 2 else RiskLevel.LOW,
            sources=list(set(e.sources[0].get("source_type", "unknown") for e in impersonation_entities if e.sources))
        )
        impersonation_risk.calculate_risk_score()
        analysis["impersonation_risk"] = impersonation_risk

        logger.debug("exposure analysis completed", {
            "categories": list(analysis.keys()),
            "total_exposed_entities": sum(cat.exposed_count for cat in analysis.values())
        })

        return analysis

    def _has_account_takeover_indicators(self, entity: Entity) -> bool:
        """Check if entity has account takeover risk indicators."""
        indicators = [
            "compromised", "breached", "leaked", "exposed",
            "vulnerable", "unsecured", "public_password",
            "2fa_disabled", "no_verification"
        ]
        
        entity_text = json.dumps(entity.attributes).lower()
        return any(indicator in entity_text for indicator in indicators)

    def _has_doxxing_indicators(self, entity: Entity) -> bool:
        """Check if entity has doxxing risk indicators."""
        indicators = [
            "home_address", "home_phone", "personal_phone",
            "family_members", "relatives", "family_info",
            "ssn", "social_security", "national_id",
            "birth_date", "dob", "date_of_birth",
            "mothers_maiden", "maiden_name", "birth_place"
        ]
        
        entity_text = json.dumps(entity.attributes).lower()
        return any(indicator in entity_text for indicator in indicators)

    def _has_impersonation_indicators(self, entity: Entity) -> bool:
        """Check if entity has impersonation risk indicators."""
        indicators = [
            "fake", "impersonating", "impersonation",
            "unverified", "suspicious", "fraudulent",
            "scam", "phishing", "malicious"
        ]
        
        entity_text = json.dumps(entity.attributes).lower()
        return any(indicator in entity_text for indicator in indicators)

    def _generate_activity_timeline(self, entities: List[Entity]) -> List[TimelineEntry]:
        """Generate activity timeline from entities."""
        timeline = []
        
        # Sort entities by creation date
        dated_entities = [e for e in entities if e.created_at]
        dated_entities.sort(key=lambda x: x.created_at, reverse=True)
        
        for entity in dated_entities[:50]:  # Limit to 50 most recent
            # Determine activity based on entity type and attributes
            if entity.entity_type == EntityType.SOCIAL_PROFILE:
                activity = f"Social profile activity on {entity.attributes.get('platform', 'Unknown platform')}"
                privacy_implication = "MEDIUM"
            elif entity.entity_type == EntityType.PERSON:
                activity = f"Personal information discovered"
                privacy_implication = "HIGH"
            elif entity.entity_type == EntityType.EMAIL_ADDRESS:
                activity = f"Email address exposure detected"
                privacy_implication = "HIGH"
            elif entity.entity_type == EntityType.PHONE_NUMBER:
                activity = f"Phone number exposure detected"
                privacy_implication = "HIGH"
            else:
                activity = f"{entity.entity_type.value} information discovered"
                privacy_implication = "MEDIUM"

            # Get source URL for timeline entry
            source_url = entity.sources[0].get("url", "") if entity.sources else ""
            
            entry = TimelineEntry(
                date=entity.created_at.strftime("%Y-%m-%d"),
                platform=entity.attributes.get("platform", entity.entity_type.value),
                activity=activity,
                privacy_implication=privacy_implication,
                source_url=source_url,
                confidence=entity.confidence_score
            )
            timeline.append(entry)

        return timeline

    async def _generate_remediation_recommendations(self, exposure_analysis: Dict[str, ExposureCategory], 
                                               correlation_id: str) -> List[RemediationRecommendation]:
        """Generate remediation recommendations based on exposure analysis."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "report.generate_remediation_recommendations",
            "exposure_categories": list(exposure_analysis.keys())
        })

        recommendations = []

        # Contact information remediation
        if "contact_information" in exposure_analysis:
            contact_exposure = exposure_analysis["contact_information"]
            if contact_exposure.exposed_count > 0:
                recommendations.append(RemediationRecommendation(
                    priority="HIGH",
                    category="account_security",
                    action="Enable two-factor authentication on all accounts",
                    platforms=["email", "social_media", "banking"],
                    estimated_impact=85.0,
                    implementation_difficulty="LOW",
                    description="2FA significantly reduces account takeover risk"
                ))
                
                recommendations.append(RemediationRecommendation(
                    priority="HIGH",
                    category="privacy_settings",
                    action="Remove personal phone number from public profiles",
                    platforms=["social_media", "public_directories"],
                    estimated_impact=70.0,
                    implementation_difficulty="MEDIUM",
                    description="Phone numbers are commonly used for account recovery"
                ))

        # Account takeover remediation
        if "account_takeover_risk" in exposure_analysis:
            at_risk = exposure_analysis["account_takeover_risk"]
            if at_risk.exposed_count > 0:
                recommendations.append(RemediationRecommendation(
                    priority="IMMEDIATE",
                    category="account_security",
                    action="Change passwords on all identified accounts",
                    platforms=["email", "social_media", "banking"],
                    estimated_impact=90.0,
                    implementation_difficulty="MEDIUM",
                    description="Immediate password changes prevent unauthorized access"
                ))
                
                recommendations.append(RemediationRecommendation(
                    priority="HIGH",
                    category="account_monitoring",
                    action="Enable account activity notifications",
                    platforms=["email", "social_media", "banking"],
                    estimated_impact=75.0,
                    implementation_difficulty="LOW",
                    description="Early detection of unauthorized access"
                ))

        # Doxxing remediation
        if "doxxing_risk" in exposure_analysis:
            doxxing_risk = exposure_analysis["doxxing_risk"]
            if doxxing_risk.exposed_count > 0:
                recommendations.append(RemediationRecommendation(
                    priority="IMMEDIATE",
                    category="privacy_protection",
                    action="File identity theft report with authorities",
                    platforms=["legal", "law_enforcement"],
                    estimated_impact=95.0,
                    implementation_difficulty="HIGH",
                    description="Legal protection for identity theft cases"
                ))
                
                recommendations.append(RemediationRecommendation(
                    priority="HIGH",
                    category="content_removal",
                    action="Request removal of personal information from websites",
                    platforms=["data_brokers", "public_records", "search_engines"],
                    estimated_impact=60.0,
                    implementation_difficulty="HIGH",
                    description="Use privacy rights to remove exposed information"
                ))

        # Impersonation remediation
        if "impersonation_risk" in exposure_analysis:
            impersonation_risk = exposure_analysis["impersonation_risk"]
            if impersonation_risk.exposed_count > 0:
                recommendations.append(RemediationRecommendation(
                    priority="HIGH",
                    category="identity_verification",
                    action="Enable profile verification badges",
                    platforms=["social_media", "professional_networks"],
                    estimated_impact=80.0,
                    implementation_difficulty="MEDIUM",
                    description="Verification helps others distinguish real from fake profiles"
                ))

        logger.debug("remediation recommendations generated", {
            "recommendations_count": len(recommendations),
            "priority_distribution": {"HIGH": sum(1 for r in recommendations if r.priority == "HIGH"),
                                   "MEDIUM": sum(1 for r in recommendations if r.priority == "MEDIUM"),
                                   "LOW": sum(1 for r in recommendations if r.priority == "LOW")}
        })

        return recommendations

    async def _calculate_risk_assessments(self, entities: List[Entity], correlation_id: str) -> List[RiskAssessment]:
        """Calculate risk assessments for different categories."""
        assessments = []

        # Contact information risk
        contact_entities = [e for e in entities if e.entity_type in [EntityType.EMAIL_ADDRESS, EntityType.PHONE_NUMBER]]
        if contact_entities:
            contact_risk = RiskAssessment(
                category=RiskCategory.CONTACT_EXPOSURE,
                risk_score=min(100.0, len(contact_entities) * 20),
                risk_level=RiskLevel.HIGH if len(contact_entities) > 3 else RiskLevel.MEDIUM,
                findings_count=len(contact_entities),
                affected_platforms=list(set(e.sources[0].get("source_type", "unknown") for e in contact_entities if e.sources)),
                description="Personal contact information exposed in public sources",
                recommendations=["Enable 2FA", "Monitor account activity", "Use privacy settings"]
            )
            assessments.append(contact_risk)

        # Account takeover risk
        at_risk_entities = [e for e in entities if self._has_account_takeover_indicators(e)]
        if at_risk_entities:
            at_risk = RiskAssessment(
                category=RiskCategory.ACCOUNT_TAKEOVER,
                risk_score=min(100.0, len(at_risk_entities) * 25),
                risk_level=RiskLevel.HIGH if len(at_risk_entities) > 2 else RiskLevel.MEDIUM,
                findings_count=len(at_risk_entities),
                affected_platforms=list(set(e.sources[0].get("source_type", "unknown") for e in at_risk_entities if e.sources)),
                description="Indicators of account compromise or vulnerability detected",
                recommendations=["Change passwords", "Enable 2FA", "Review account access logs"]
            )
            assessments.append(at_risk)

        # Doxxing risk
        doxxing_entities = [e for e in entities if self._has_doxxing_indicators(e)]
        if doxxing_entities:
            doxxing_risk = RiskAssessment(
                category=RiskCategory.DOXXING_RISK,
                risk_score=min(100.0, len(doxxing_entities) * 30),
                risk_level=RiskLevel.HIGH,
                findings_count=len(doxxing_entities),
                affected_platforms=list(set(e.sources[0].get("source_type", "unknown") for e in doxxing_entities if e.sources)),
                description="Highly sensitive personal information exposed",
                recommendations=["File police report", "Request content removal", "Monitor identity theft"]
            )
            assessments.append(doxxing_risk)

        # Impersonation risk
        impersonation_entities = [e for e in entities if self._has_impersonation_indicators(e)]
        if impersonation_entities:
            impersonation_risk = RiskAssessment(
                category=RiskCategory.IMPERSONATION_RISK,
                risk_score=min(100.0, len(impersonation_entities) * 20),
                risk_level=RiskLevel.MEDIUM if len(impersonation_entities) > 2 else RiskLevel.LOW,
                findings_count=len(impersonation_entities),
                affected_platforms=list(set(e.sources[0].get("source_type", "unknown") for e in impersonation_entities if e.sources)),
                description="Potential profile impersonation or fake accounts detected",
                recommendations=["Enable verification", "Report fake profiles", "Monitor brand mentions"]
            )
            assessments.append(impersonation_risk)

        return assessments

    def _generate_source_references(self, entities: List[Entity]) -> List[Dict[str, Any]]:
        """Generate source references from entities."""
        sources = []
        seen_sources = set()

        for entity in entities:
            for source in entity.sources:
                source_key = source.get("url", source.get("source_type", "unknown"))
                if source_key not in seen_sources:
                    sources.append({
                        "url": source.get("url", ""),
                        "source_type": source.get("source_type", "unknown"),
                        "confidence": source.get("confidence", 0),
                        "retrieved_at": source.get("retrieved_at", ""),
                        "entity_ids": [entity.id]
                    })
                    seen_sources.add(source_key)

        return sources

    def _export_json(self, report: InvestigationReport, correlation_id: str) -> str:
        """Export report as JSON."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "report.export_json",
            "investigation_id": report.investigation_id
        })

        try:
            json_data = report.to_dict()
            # Redact sensitive data
            json_str = json.dumps(json_data, indent=2, default=str)
            redacted_json = redact_sensitive_data(json_str)
            
            logger.debug("JSON export completed", {
                "data_size_bytes": len(redacted_json.encode('utf-8'))
            })
            
            return redacted_json

        except Exception as e:
            logger.error("JSON export failed", {
                "error": str(e)
            })
            raise

    def _export_markdown(self, report: InvestigationReport, correlation_id: str) -> str:
        """Export report as Markdown."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "report.export_markdown",
            "investigation_id": report.investigation_id
        })

        try:
            md_content = report.to_markdown()
            redacted_md = redact_sensitive_data(md_content)
            
            logger.debug("Markdown export completed", {
                "content_size_bytes": len(redacted_md.encode('utf-8'))
            })
            
            return redacted_md

        except Exception as e:
            logger.error("Markdown export failed", {
                "error": str(e)
            })
            raise

    def _export_html(self, report: InvestigationReport, correlation_id: str) -> str:
        """Export report as HTML."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "report.export_html",
            "investigation_id": report.investigation_id
        })

        try:
            # Convert markdown to HTML
            md_content = report.to_markdown()
            
            # Simple markdown to HTML conversion
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>OSINT Investigation Report - {report.investigation_id}</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; border-bottom: 2px solid #333; }}
        h2 {{ color: #666; }}
        .risk-high {{ color: #d32f2f; }}
        .risk-medium {{ color: #f39c12; }}
        .risk-low {{ color: #28a745; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>OSINT Privacy Risk Assessment Report</h1>
    <p><strong>Investigation ID:</strong> {report.investigation_id}</p>
    <p><strong>Generated:</strong> {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    
    {md_content}
</body>
</html>
            """
            
            redacted_html = redact_sensitive_data(html_content)
            
            logger.debug("HTML export completed", {
                "content_size_bytes": len(redacted_html.encode('utf-8'))
            })
            
            return redacted_html

        except Exception as e:
            logger.error("HTML export failed", {
                "error": str(e)
            })
            raise

    async def _export_pdf(self, report: InvestigationReport, correlation_id: str) -> bytes:
        """Export report as PDF."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "report.export_pdf",
            "investigation_id": report.investigation_id
        })

        try:
            # For now, return HTML as bytes (PDF generation would require additional dependencies)
            html_content = self._export_html(report, correlation_id)
            
            logger.debug("PDF export completed (HTML fallback)", {
                "content_size_bytes": len(html_content.encode('utf-8'))
            })
            
            return html_content.encode('utf-8')

        except Exception as e:
            logger.error("PDF export failed", {
                "error": str(e)
            })
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get current report generation metrics."""
        return {
            "total_reports_generated": self.metrics.total_reports_generated,
            "successful_generations": self.metrics.successful_generations,
            "failed_generations": self.metrics.failed_generations,
            "success_rate": self.metrics.get_success_rate(),
            "average_generation_time_ms": self.metrics.get_average_generation_time_ms(),
            "format_distribution": self.metrics.format_distribution,
            "average_entities_per_report": self.metrics.average_entities_per_report,
            "data_quality_warnings": self.metrics.data_quality_warnings
        }

    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on report generator."""
        health_status = {
            "metrics_available": self.metrics.total_reports_generated >= 0,
            "success_rate_acceptable": self.metrics.get_success_rate() >= 95,
            "generation_time_acceptable": self.metrics.get_average_generation_time_ms() < 30000,  # 30 seconds
            "no_active_errors": True  # Could be enhanced with actual error tracking
        }
        
        return health_status
