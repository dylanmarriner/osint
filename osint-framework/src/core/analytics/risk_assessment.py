"""
Risk Assessment Engine for OSINT Framework

Comprehensive security and privacy risk evaluation:
- Privacy exposure scoring
- Vulnerability assessment
- Threat modeling
- Identity theft risk calculation
- Breach impact analysis
- Remediation recommendations
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class RiskLevel(Enum):
    """Risk severity levels."""
    CRITICAL = "CRITICAL"  # >90
    HIGH = "HIGH"  # 70-90
    MEDIUM = "MEDIUM"  # 40-70
    LOW = "LOW"  # 10-40
    MINIMAL = "MINIMAL"  # <10


class VulnerabilityType(Enum):
    """Types of vulnerabilities."""
    WEAK_PASSWORD = "weak_password"
    REUSED_PASSWORD = "reused_password"
    NO_2FA = "no_2fa"
    UNENCRYPTED_COMMUNICATION = "unencrypted_communication"
    EXPOSED_PERSONAL_DATA = "exposed_personal_data"
    PUBLIC_LOCATION_DATA = "public_location_data"
    SOCIAL_ENGINEERING_VECTOR = "social_engineering_vector"
    OUTDATED_SOFTWARE = "outdated_software"
    OPEN_PORTS = "open_ports"
    MISCONFIGURED_SERVICES = "misconfigured_services"


@dataclass
class Vulnerability:
    """A specific vulnerability."""
    vuln_type: VulnerabilityType
    severity: RiskLevel
    title: str
    description: str
    affected_accounts: List[str] = field(default_factory=list)
    remediation: str = ""
    remediation_effort: str = "MEDIUM"  # LOW, MEDIUM, HIGH

    def to_dict(self) -> Dict:
        return {
            'type': self.vuln_type.value,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'affected_accounts': self.affected_accounts,
            'remediation': self.remediation,
            'remediation_effort': self.remediation_effort
        }


@dataclass
class RiskAssessment:
    """Complete risk assessment for a person."""
    assessment_id: str
    subject_id: str
    overall_risk_score: float  # 0-100
    risk_level: RiskLevel
    privacy_exposure_score: float
    security_risk_score: float
    identity_theft_risk: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    exposed_data_types: Set[str] = field(default_factory=set)
    breach_count: int = 0
    breach_timeline: Dict[str, int] = field(default_factory=dict)
    
    recommendations: List[Dict] = field(default_factory=list)
    remediation_impact: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'assessment_id': self.assessment_id,
            'subject_id': self.subject_id,
            'overall_risk_score': self.overall_risk_score,
            'risk_level': self.risk_level.value,
            'privacy_exposure_score': self.privacy_exposure_score,
            'security_risk_score': self.security_risk_score,
            'identity_theft_risk': self.identity_theft_risk,
            'timestamp': self.timestamp.isoformat(),
            'vulnerabilities': [v.to_dict() for v in self.vulnerabilities],
            'exposed_data_types': list(self.exposed_data_types),
            'breach_count': self.breach_count,
            'breach_timeline': self.breach_timeline,
            'recommendations': self.recommendations,
            'remediation_impact': self.remediation_impact
        }


class RiskAssessmentEngine:
    """Comprehensive risk assessment and analysis."""

    def __init__(self):
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

    # ==================== Risk Scoring ====================

    async def calculate_overall_risk(self, person_data: Dict[str, Any]) -> RiskAssessment:
        """
        Calculate comprehensive risk score.
        
        person_data should contain:
        {
            'subject_id': str,
            'breaches': list of breach data,
            'accounts': list of account data,
            'personal_data_exposed': dict,
            'network_size': int,
            'geographic_data': dict,
        }
        """
        subject_id = person_data.get('subject_id', 'unknown')
        assessment_id = f"risk_{subject_id}_{datetime.utcnow().timestamp()}"

        # Calculate component scores
        privacy_score = await self._calculate_privacy_exposure(person_data)
        security_score = await self._calculate_security_risk(person_data)
        identity_theft_score = await self._calculate_identity_theft_risk(person_data)

        # Weighted overall score
        overall_score = (
            privacy_score * 0.35 +
            security_score * 0.35 +
            identity_theft_score * 0.30
        )

        # Determine risk level
        risk_level = self._score_to_level(overall_score)

        # Identify vulnerabilities
        vulnerabilities = await self._identify_vulnerabilities(person_data)

        # Get recommendations
        recommendations = self._generate_recommendations(vulnerabilities, privacy_score)

        assessment = RiskAssessment(
            assessment_id=assessment_id,
            subject_id=subject_id,
            overall_risk_score=overall_score,
            risk_level=risk_level,
            privacy_exposure_score=privacy_score,
            security_risk_score=security_score,
            identity_theft_risk=identity_theft_score,
            vulnerabilities=vulnerabilities,
            breach_count=len(person_data.get('breaches', [])),
            recommendations=recommendations
        )

        # Extract exposed data types
        assessment.exposed_data_types = self._extract_exposed_data_types(person_data)

        # Build breach timeline
        assessment.breach_timeline = await self._build_breach_timeline(person_data)

        # Calculate remediation impact
        assessment.remediation_impact = self._calculate_remediation_impact(vulnerabilities)

        self.logger.info(
            "Risk assessment complete",
            subject_id=subject_id,
            overall_score=overall_score,
            risk_level=risk_level.value
        )

        return assessment

    async def _calculate_privacy_exposure(self, person_data: Dict) -> float:
        """
        Calculate privacy exposure score (0-100).
        Factors:
        - Contact information exposure (email, phone, address)
        - Personal identity data (photos, DOB, SSN)
        - Location history
        - Behavioral data
        - Network connections
        """
        score = 0.0

        # Contact information (30%)
        contact_score = 0.0
        if 'emails_exposed' in person_data:
            contact_score += len(person_data['emails_exposed']) * 10
        if 'phones_exposed' in person_data:
            contact_score += len(person_data['phones_exposed']) * 15
        if 'addresses_exposed' in person_data:
            contact_score += len(person_data['addresses_exposed']) * 20
        contact_score = min(100, contact_score)
        score += contact_score * 0.30

        # Personal identity (25%)
        identity_score = 0.0
        if person_data.get('ssn_exposed'):
            identity_score += 40
        if person_data.get('dob_exposed'):
            identity_score += 25
        if person_data.get('photos_public'):
            identity_score += 15
        identity_score = min(100, identity_score)
        score += identity_score * 0.25

        # Location data (20%)
        location_score = 0.0
        if person_data.get('current_location_public'):
            location_score += 30
        if person_data.get('residence_history_public'):
            location_score += 40
        if person_data.get('gps_location_exposed'):
            location_score += 30
        location_score = min(100, location_score)
        score += location_score * 0.20

        # Behavioral data (15%)
        behavioral_score = 0.0
        posts_count = len(person_data.get('social_posts', []))
        behavioral_score = min(100, posts_count)
        score += behavioral_score * 0.15

        # Network (10%)
        network_size = person_data.get('network_size', 0)
        network_score = min(100, network_size / 10)
        score += network_score * 0.10

        return min(100, score)

    async def _calculate_security_risk(self, person_data: Dict) -> float:
        """
        Calculate security risk score (0-100).
        Factors:
        - Weak/reused passwords
        - Missing 2FA
        - Compromised accounts
        - Data breaches
        - Vulnerability exposure
        """
        score = 0.0

        # Breach exposure (35%)
        breach_score = 0.0
        breach_count = len(person_data.get('breaches', []))
        if breach_count > 0:
            breach_score = min(100, breach_count * 15)
            # Extra points for recent breaches
            for breach in person_data.get('breaches', []):
                if breach.get('is_recent'):
                    breach_score += 20
        breach_score = min(100, breach_score)
        score += breach_score * 0.35

        # Account security (30%)
        account_score = 0.0
        accounts = person_data.get('accounts', [])
        weak_password_count = sum(1 for a in accounts if a.get('weak_password'))
        account_score += weak_password_count * 25
        no_2fa_count = sum(1 for a in accounts if not a.get('has_2fa'))
        account_score += no_2fa_count * 15
        account_score = min(100, account_score)
        score += account_score * 0.30

        # Device/network security (20%)
        network_score = 0.0
        if person_data.get('devices_found'):
            network_score += min(100, len(person_data['devices_found']) * 10)
        if person_data.get('open_ports'):
            network_score += 30
        network_score = min(100, network_score)
        score += network_score * 0.20

        # Vulnerability exposure (15%)
        vuln_score = 0.0
        if person_data.get('vulnerabilities'):
            vuln_score = min(100, len(person_data['vulnerabilities']) * 20)
        score += vuln_score * 0.15

        return min(100, score)

    async def _calculate_identity_theft_risk(self, person_data: Dict) -> float:
        """
        Calculate identity theft risk (0-100).
        Factors:
        - PII exposure (SSN, DOB, full name)
        - Address/location
        - Financial data
        - Credit history data
        """
        score = 0.0

        # PII availability (40%)
        pii_score = 0.0
        if person_data.get('ssn_exposed'):
            pii_score += 50
        if person_data.get('dob_exposed'):
            pii_score += 25
        if person_data.get('full_name_exposed'):
            pii_score += 10
        if person_data.get('mothers_maiden_name_exposed'):
            pii_score += 30
        pii_score = min(100, pii_score)
        score += pii_score * 0.40

        # Address/residence (25%)
        address_score = 0.0
        if person_data.get('address_exposed'):
            address_score += 50
        if person_data.get('residence_history_exposed'):
            address_score += 30
        address_score = min(100, address_score)
        score += address_score * 0.25

        # Financial data (20%)
        financial_score = 0.0
        if person_data.get('credit_card_exposed'):
            financial_score += 50
        if person_data.get('bank_account_exposed'):
            financial_score += 40
        if person_data.get('income_data_exposed'):
            financial_score += 20
        financial_score = min(100, financial_score)
        score += financial_score * 0.20

        # Credential availability (15%)
        cred_score = 0.0
        if person_data.get('passwords_exposed'):
            cred_score += 50
        if person_data.get('security_questions_answered'):
            cred_score += 30
        cred_score = min(100, cred_score)
        score += cred_score * 0.15

        return min(100, score)

    async def _identify_vulnerabilities(
        self,
        person_data: Dict[str, Any]
    ) -> List[Vulnerability]:
        """Identify specific vulnerabilities."""
        vulnerabilities = []

        # Breach exposure
        if person_data.get('breaches'):
            vulnerabilities.append(Vulnerability(
                vuln_type=VulnerabilityType.EXPOSED_PERSONAL_DATA,
                severity=self._score_to_level(80),
                title=f"{len(person_data['breaches'])} Data Breaches Found",
                description=f"Personal data exposed in {len(person_data['breaches'])} known breaches",
                affected_accounts=[b.get('name') for b in person_data['breaches']],
                remediation="Monitor credit reports, change passwords, consider credit freeze"
            ))

        # Account security
        accounts = person_data.get('accounts', [])
        weak_password_accounts = [a for a in accounts if a.get('weak_password')]
        if weak_password_accounts:
            vulnerabilities.append(Vulnerability(
                vuln_type=VulnerabilityType.WEAK_PASSWORD,
                severity=RiskLevel.HIGH,
                title="Weak Passwords Detected",
                description=f"{len(weak_password_accounts)} accounts use weak/short passwords",
                affected_accounts=[a.get('name') for a in weak_password_accounts],
                remediation="Use strong, unique passwords (12+ chars, mixed case, numbers, symbols)",
                remediation_effort="MEDIUM"
            ))

        # Missing 2FA
        no_2fa_accounts = [a for a in accounts if not a.get('has_2fa')]
        if no_2fa_accounts:
            vulnerabilities.append(Vulnerability(
                vuln_type=VulnerabilityType.NO_2FA,
                severity=RiskLevel.HIGH,
                title="2FA Not Enabled",
                description=f"{len(no_2fa_accounts)} critical accounts lack 2FA",
                affected_accounts=[a.get('name') for a in no_2fa_accounts],
                remediation="Enable 2FA on all critical accounts (email, banking, social)",
                remediation_effort="LOW"
            ))

        # PII exposure
        if person_data.get('ssn_exposed'):
            vulnerabilities.append(Vulnerability(
                vuln_type=VulnerabilityType.EXPOSED_PERSONAL_DATA,
                severity=RiskLevel.CRITICAL,
                title="SSN Exposed in Breach",
                description="Social Security Number found in data breach",
                remediation="Place fraud alert/credit freeze with credit bureaus",
                remediation_effort="HIGH"
            ))

        # Location data
        if person_data.get('current_location_public'):
            vulnerabilities.append(Vulnerability(
                vuln_type=VulnerabilityType.PUBLIC_LOCATION_DATA,
                severity=RiskLevel.MEDIUM,
                title="Current Location Publicly Available",
                description="Real-time location can be inferred from public posts/check-ins",
                remediation="Disable location sharing on social media and smartphones",
                remediation_effort="LOW"
            ))

        return vulnerabilities

    def _generate_recommendations(
        self,
        vulnerabilities: List[Vulnerability],
        privacy_score: float
    ) -> List[Dict]:
        """Generate remediation recommendations."""
        recommendations = []

        # Prioritize by severity
        for vuln in sorted(vulnerabilities, key=lambda v: self._severity_to_priority(v.severity)):
            recommendations.append({
                'priority': 'CRITICAL' if vuln.severity == RiskLevel.CRITICAL else 'HIGH' if vuln.severity == RiskLevel.HIGH else 'MEDIUM',
                'action': vuln.remediation,
                'effort': vuln.remediation_effort,
                'vulnerability': vuln.title,
                'impact_reduction': self._estimate_impact_reduction(vuln.vuln_type)
            })

        # Add privacy-specific recommendations
        if privacy_score > 70:
            recommendations.append({
                'priority': 'HIGH',
                'action': 'Review and restrict social media privacy settings',
                'effort': 'LOW',
                'impact_reduction': 20
            })

        if privacy_score > 50:
            recommendations.append({
                'priority': 'MEDIUM',
                'action': 'Request removal of personal data from data broker sites',
                'effort': 'MEDIUM',
                'impact_reduction': 15
            })

        return recommendations[:5]  # Top 5 recommendations

    # ==================== Helper Methods ====================

    @staticmethod
    def _score_to_level(score: float) -> RiskLevel:
        """Convert score to risk level."""
        if score >= 90:
            return RiskLevel.CRITICAL
        elif score >= 70:
            return RiskLevel.HIGH
        elif score >= 40:
            return RiskLevel.MEDIUM
        elif score >= 10:
            return RiskLevel.LOW
        else:
            return RiskLevel.MINIMAL

    @staticmethod
    def _severity_to_priority(severity: RiskLevel) -> int:
        """Convert severity to priority (lower is higher priority)."""
        priority_map = {
            RiskLevel.CRITICAL: 0,
            RiskLevel.HIGH: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 3,
            RiskLevel.MINIMAL: 4
        }
        return priority_map.get(severity, 4)

    @staticmethod
    def _estimate_impact_reduction(vuln_type: VulnerabilityType) -> int:
        """Estimate % risk reduction from fixing vulnerability."""
        impact_map = {
            VulnerabilityType.WEAK_PASSWORD: 15,
            VulnerabilityType.REUSED_PASSWORD: 20,
            VulnerabilityType.NO_2FA: 25,
            VulnerabilityType.EXPOSED_PERSONAL_DATA: 30,
            VulnerabilityType.PUBLIC_LOCATION_DATA: 10,
            VulnerabilityType.MISCONFIGURED_SERVICES: 20,
        }
        return impact_map.get(vuln_type, 10)

    @staticmethod
    def _extract_exposed_data_types(person_data: Dict) -> Set[str]:
        """Extract types of data exposed."""
        exposed = set()

        if person_data.get('emails_exposed'):
            exposed.add('email_addresses')
        if person_data.get('phones_exposed'):
            exposed.add('phone_numbers')
        if person_data.get('ssn_exposed'):
            exposed.add('social_security_number')
        if person_data.get('dob_exposed'):
            exposed.add('date_of_birth')
        if person_data.get('passwords_exposed'):
            exposed.add('passwords')
        if person_data.get('credit_card_exposed'):
            exposed.add('credit_card_numbers')
        if person_data.get('address_exposed'):
            exposed.add('home_address')

        return exposed

    @staticmethod
    async def _build_breach_timeline(person_data: Dict) -> Dict[str, int]:
        """Build timeline of breaches by year."""
        timeline = {}

        for breach in person_data.get('breaches', []):
            year = breach.get('year', 'unknown')
            timeline[str(year)] = timeline.get(str(year), 0) + 1

        return dict(sorted(timeline.items()))

    def _calculate_remediation_impact(
        self,
        vulnerabilities: List[Vulnerability]
    ) -> Dict[str, float]:
        """Calculate impact of fixing each vulnerability."""
        impact = {}

        for vuln in vulnerabilities:
            impact[vuln.title] = self._estimate_impact_reduction(vuln.vuln_type) / 100.0

        return impact

    # ==================== Export ====================

    def get_risk_summary(self, assessment: RiskAssessment) -> Dict[str, Any]:
        """Get executive summary of risk assessment."""
        return {
            'subject_id': assessment.subject_id,
            'overall_risk': {
                'score': assessment.overall_risk_score,
                'level': assessment.risk_level.value
            },
            'component_scores': {
                'privacy': assessment.privacy_exposure_score,
                'security': assessment.security_risk_score,
                'identity_theft': assessment.identity_theft_risk
            },
            'vulnerabilities_count': len(assessment.vulnerabilities),
            'top_vulnerabilities': [
                v.title for v in assessment.vulnerabilities[:3]
            ],
            'recommendations_count': len(assessment.recommendations),
            'top_recommendations': [
                r['action'] for r in assessment.recommendations[:3]
            ],
            'remediation_impact': assessment.remediation_impact
        }
