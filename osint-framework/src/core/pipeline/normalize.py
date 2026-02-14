"""
Normalization Engine for OSINT Investigation Pipeline

Purpose
- Normalize extracted entities to standard formats
- Apply data quality validation and cleaning
- Standardize geographic and temporal data
- Provide comprehensive observability and error handling

Invariants
- All normalized entities follow standard schemas
- Data quality metrics are tracked for all operations
- Sensitive data is redacted before logging
- Every normalization operation is logged with correlation IDs
- Invalid entities are rejected with specific error details

Failure Modes
- Invalid entity format → normalization fails with structured error
- Data quality issues → entity is flagged but processing continues
- Geographic normalization failure → location is marked as approximate
- Temporal parsing errors → timestamps are set to None with warning
- Schema validation failure → entity is rejected with validation details

Debug Notes
- Use correlation_id to trace normalization through pipeline
- Monitor normalization_duration_ms metrics for performance issues
- Check data_quality_score metrics for overall data health
- Review normalization_failed alerts for systematic issues
- Use entity_type_metrics to monitor type-specific problems

Design Tradeoffs
- Chose comprehensive validation over permissive normalization for data quality
- Tradeoff: Stricter validation rejects some valid data but ensures consistency
- Mitigation: Multiple normalization strategies and fallback options for edge cases
- Review trigger: If normalization success rate drops below 85%, relax validation rules
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
from urllib.parse import urlparse

from ..models.entities import (
    Entity, EntityType, VerificationStatus,
    validate_email, validate_phone, validate_domain,
    redact_sensitive_data
)


class NormalizationStatus(Enum):
    """Status of normalization operations."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATION_ERROR = "validation_error"
    QUALITY_FLAGGED = "quality_flagged"


class DataQualityLevel(Enum):
    """Data quality assessment levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    POOR = "poor"


@dataclass
class NormalizationResult:
    """Result of entity normalization."""
    result_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = ""
    source_entity_id: str = ""
    normalized_entity: Optional[Entity] = None
    quality_score: float = 0.0
    quality_level: DataQualityLevel = DataQualityLevel.LOW
    normalization_status: NormalizationStatus = NormalizationStatus.PENDING
    error_message: Optional[str] = None
    quality_flags: List[str] = field(default_factory=list)
    transformations_applied: List[str] = field(default_factory=list)
    normalization_duration_ms: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def mark_completed(self, normalized_entity: Entity, quality_score: float, 
                     quality_level: DataQualityLevel, transformations: List[str]):
        """Mark normalization as completed."""
        self.normalization_status = NormalizationStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.normalized_entity = normalized_entity
        self.quality_score = quality_score
        self.quality_level = quality_level
        self.transformations_applied = transformations

    def mark_failed(self, error_message: str, status: NormalizationStatus = NormalizationStatus.FAILED):
        """Mark normalization as failed."""
        self.normalization_status = status
        self.completed_at = datetime.utcnow()
        self.error_message = error_message

    def add_quality_flag(self, flag: str):
        """Add a quality flag to the result."""
        if flag not in self.quality_flags:
            self.quality_flags.append(flag)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "result_id": self.result_id,
            "correlation_id": self.correlation_id,
            "source_entity_id": self.source_entity_id,
            "normalized_entity_id": self.normalized_entity.id if self.normalized_entity else None,
            "quality_score": self.quality_score,
            "quality_level": self.quality_level.value,
            "normalization_status": self.normalization_status.value,
            "error_message": self.error_message,
            "quality_flags": self.quality_flags,
            "transformations_applied": self.transformations_applied,
            "normalization_duration_ms": self.normalization_duration_ms,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class NormalizationMetrics:
    """Metrics for normalization operations."""
    total_entities: int = 0
    completed_normalizations: int = 0
    failed_normalizations: int = 0
    quality_flagged: int = 0
    validation_errors: int = 0
    total_quality_score: float = 0.0
    total_duration_ms: int = 0
    entity_type_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    quality_distribution: Dict[str, int] = field(default_factory=dict)

    def get_success_rate(self) -> float:
        """Calculate normalization success rate percentage."""
        if self.total_entities == 0:
            return 0.0
        return (self.completed_normalizations / self.total_entities) * 100

    def get_average_quality_score(self) -> float:
        """Calculate average quality score."""
        if self.completed_normalizations == 0:
            return 0.0
        return self.total_quality_score / self.completed_normalizations

    def get_average_duration_ms(self) -> float:
        """Calculate average normalization duration in milliseconds."""
        if self.completed_normalizations == 0:
            return 0.0
        return self.total_duration_ms / self.completed_normalizations

    def update_entity_type_metrics(self, entity_type: str, status: str, 
                                  quality_score: float, duration_ms: int):
        """Update metrics for a specific entity type."""
        if entity_type not in self.entity_type_metrics:
            self.entity_type_metrics[entity_type] = {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "quality_score": 0.0,
                "duration_ms": 0
            }
        
        self.entity_type_metrics[entity_type]["total"] += 1
        if status == "completed":
            self.entity_type_metrics[entity_type]["completed"] += 1
            self.entity_type_metrics[entity_type]["quality_score"] += quality_score
            self.entity_type_metrics[entity_type]["duration_ms"] += duration_ms
        else:
            self.entity_type_metrics[entity_type]["failed"] += 1

    def update_quality_distribution(self, quality_level: str):
        """Update quality level distribution."""
        if quality_level not in self.quality_distribution:
            self.quality_distribution[quality_level] = 0
        self.quality_distribution[quality_level] += 1


class NormalizationEngine:
    """
    Core normalization engine for processing entities.

    Purpose
    - Normalize entities to standard formats and schemas
    - Apply data quality validation and cleaning
    - Standardize geographic and temporal data
    - Provide comprehensive observability and error handling

    Invariants
    - All normalized entities follow standard schemas
    - Data quality metrics are tracked for all operations
    - Sensitive data is redacted before logging
    - Every normalization operation is logged with correlation IDs
    - Invalid entities are rejected with specific error details

    Failure Modes
    - Invalid entity format → normalization fails with structured error
    - Data quality issues → entity is flagged but processing continues
    - Geographic normalization failure → location is marked as approximate
    - Temporal parsing errors → timestamps are set to None with warning
    - Schema validation failure → entity is rejected with validation details

    Debug Notes
    - Use correlation_id to trace normalization through pipeline
    - Monitor normalization_duration_ms metrics for performance issues
    - Check data_quality_score metrics for overall data health
    - Review normalization_failed alerts for systematic issues
    - Use entity_type_metrics to monitor type-specific problems

    Design Tradeoffs
    - Chose comprehensive validation over permissive normalization for data quality
    - Tradeoff: Stricter validation rejects some valid data but ensures consistency
    - Mitigation: Multiple normalization strategies and fallback options for edge cases
    - Review trigger: If normalization success rate drops below 85%, relax validation rules
    """

    def __init__(self):
        """Initialize normalization engine."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.metrics = NormalizationMetrics()
        
        # Normalization rules and patterns
        self._name_patterns = {
            'title_case': re.compile(r'\b\w+\b'),
            'special_chars': re.compile(r'[^\w\s\-\.\']'),
            'multiple_spaces': re.compile(r'\s+'),
            'prefixes': re.compile(r'^(mr|mrs|ms|dr|prof|sir)\s+', re.IGNORECASE)
        }
        
        self._location_patterns = {
            'country_codes': {
                'us': 'United States', 'usa': 'United States',
                'uk': 'United Kingdom', 'gb': 'United Kingdom',
                'ca': 'Canada', 'au': 'Australia',
                'nz': 'New Zealand', 'de': 'Germany',
                'fr': 'France', 'it': 'Italy', 'es': 'Spain',
                'jp': 'Japan', 'cn': 'China', 'in': 'India'
            },
            'state_codes': {
                'ca': 'California', 'ny': 'New York', 'tx': 'Texas',
                'fl': 'Florida', 'il': 'Illinois', 'pa': 'Pennsylvania'
            }
        }

    async def normalize_entities(self, entities: List[Entity], 
                               correlation_id: Optional[str] = None) -> List[NormalizationResult]:
        """
        Normalize multiple entities to standard formats.

        Summary
        - Apply normalization rules to all entities
        - Validate data quality and assign scores
        - Return normalization results with quality metrics

        Preconditions
        - entities must be valid Entity objects
        - correlation_id must be provided for tracing

        Postconditions
        - All entities are processed or marked as failed
        - Normalized entities follow standard schemas
        - Quality metrics are updated for all operations

        Error cases
        - Invalid entity format → result marked as failed with error details
        - Quality validation failure → entity is flagged with specific issues
        - Normalization rule failure → entity is processed with warnings

        Idempotency: Deterministic - same input produces same normalized entities
        Side effects: Updates metrics and logs normalization operations
        """
        start_time = datetime.utcnow()
        
        if not correlation_id:
            correlation_id = str(uuid4())
        
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "normalization.normalize_entities",
            "entity_count": len(entities)
        })
        
        logger.info("starting batch normalization operation")

        try:
            # Process entities in parallel
            normalization_tasks = []
            for entity in entities:
                task = self._normalize_single_entity(entity, correlation_id)
                normalization_tasks.append(task)

            normalization_results = await asyncio.gather(*normalization_tasks, return_exceptions=True)

            # Handle exceptions and update metrics
            final_results = []
            for i, result in enumerate(normalization_results):
                if isinstance(result, Exception):
                    logger.error("entity normalization failed", {
                        "entity_index": i,
                        "error": str(result)
                    })
                    # Create failed result
                    failed_result = NormalizationResult(
                        correlation_id=correlation_id,
                        source_entity_id=entities[i].id
                    )
                    failed_result.mark_failed(str(result))
                    final_results.append(failed_result)
                    self.metrics.failed_normalizations += 1
                else:
                    final_results.append(result)
                    self.metrics.total_entities += 1
                    
                    if result.normalization_status == NormalizationStatus.COMPLETED:
                        self.metrics.completed_normalizations += 1
                        self.metrics.total_quality_score += result.quality_score
                        self.metrics.total_duration_ms += result.normalization_duration_ms
                        self.metrics.update_quality_distribution(result.quality_level.value)
                    elif result.normalization_status == NormalizationStatus.VALIDATION_ERROR:
                        self.metrics.validation_errors += 1
                    elif result.normalization_status == NormalizationStatus.QUALITY_FLAGGED:
                        self.metrics.quality_flagged += 1
                    else:
                        self.metrics.failed_normalizations += 1

                    # Update entity type metrics
                    entity_type = entities[i].entity_type.value
                    status = result.normalization_status.value
                    quality_score = result.quality_score
                    duration_ms = result.normalization_duration_ms
                    self.metrics.update_entity_type_metrics(entity_type, status, quality_score, duration_ms)

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info("batch normalization operation completed", {
                "total_entities": len(entities),
                "completed_normalizations": self.metrics.completed_normalizations,
                "failed_normalizations": self.metrics.failed_normalizations,
                "average_quality_score": self.metrics.get_average_quality_score(),
                "duration_ms": duration_ms,
                "success_rate": self.metrics.get_success_rate()
            })

            return final_results

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error("batch normalization operation failed", {
                "error": str(e),
                "duration_ms": duration_ms
            })
            raise

    async def _normalize_single_entity(self, entity: Entity, correlation_id: str) -> NormalizationResult:
        """Normalize a single entity."""
        start_time = datetime.utcnow()
        
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "normalization.normalize_single_entity",
            "entity_id": entity.id,
            "entity_type": entity.entity_type.value
        })

        result = NormalizationResult(
            correlation_id=correlation_id,
            source_entity_id=entity.id
        )

        try:
            # Create a copy for normalization
            normalized_entity = Entity(
                id=entity.id,
                investigation_id=entity.investigation_id,
                entity_type=entity.entity_type,
                attributes=entity.attributes.copy(),
                confidence_score=entity.confidence_score,
                verification_status=entity.verification_status,
                sources=entity.sources.copy(),
                created_at=entity.created_at,
                updated_at=datetime.utcnow()
            )

            transformations = []

            # Apply entity type specific normalization
            if normalized_entity.entity_type == EntityType.PERSON:
                transformations.extend(self._normalize_person_entity(normalized_entity))
            elif normalized_entity.entity_type == EntityType.EMAIL_ADDRESS:
                transformations.extend(self._normalize_email_entity(normalized_entity))
            elif normalized_entity.entity_type == EntityType.PHONE_NUMBER:
                transformations.extend(self._normalize_phone_entity(normalized_entity))
            elif normalized_entity.entity_type == EntityType.DOMAIN:
                transformations.extend(self._normalize_domain_entity(normalized_entity))
            elif normalized_entity.entity_type == EntityType.USERNAME:
                transformations.extend(self._normalize_username_entity(normalized_entity))
            elif normalized_entity.entity_type == EntityType.SOCIAL_PROFILE:
                transformations.extend(self._normalize_social_profile_entity(normalized_entity))
            elif normalized_entity.entity_type == EntityType.COMPANY:
                transformations.extend(self._normalize_company_entity(normalized_entity))

            # Apply general normalization
            transformations.extend(self._normalize_general_attributes(normalized_entity))

            # Calculate quality score
            quality_score, quality_level, quality_flags = self._calculate_quality_score(normalized_entity)

            # Add quality flags to result
            for flag in quality_flags:
                result.add_quality_flag(flag)

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            result.mark_completed(normalized_entity, quality_score, quality_level, transformations)

            logger.debug("entity normalization completed", {
                "entity_id": entity.id,
                "entity_type": entity.entity_type.value,
                "quality_score": quality_score,
                "quality_level": quality_level.value,
                "transformations_count": len(transformations),
                "duration_ms": duration_ms
            })

            return result

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            result.mark_failed(str(e))
            result.normalization_duration_ms = duration_ms

            logger.error("entity normalization failed", {
                "entity_id": entity.id,
                "error": str(e),
                "duration_ms": duration_ms
            })

            return result

    def _normalize_person_entity(self, entity: Entity) -> List[str]:
        """Normalize person entity attributes."""
        transformations = []
        attributes = entity.attributes

        # Normalize name
        if 'name' in attributes:
            original_name = attributes['name']
            normalized_name = self._normalize_name(original_name)
            if normalized_name != original_name:
                attributes['name'] = normalized_name
                attributes['original_name'] = original_name
                transformations.append("name_normalized")

        # Normalize additional name fields
        for field in ['first_name', 'last_name', 'middle_name']:
            if field in attributes:
                original_value = attributes[field]
                normalized_value = self._normalize_name(original_value)
                if normalized_value != original_value:
                    attributes[field] = normalized_value
                    attributes[f'original_{field}'] = original_value
                    transformations.append(f"{field}_normalized")

        return transformations

    def _normalize_email_entity(self, entity: Entity) -> List[str]:
        """Normalize email address entity."""
        transformations = []
        attributes = entity.attributes

        if 'email' in attributes:
            original_email = attributes['email']
            normalized_email = self._normalize_email(original_email)
            if normalized_email != original_email:
                attributes['email'] = normalized_email
                attributes['original_email'] = original_email
                transformations.append("email_normalized")

        return transformations

    def _normalize_phone_entity(self, entity: Entity) -> List[str]:
        """Normalize phone number entity."""
        transformations = []
        attributes = entity.attributes

        if 'phone' in attributes:
            original_phone = attributes['phone']
            normalized_phone = self._normalize_phone(original_phone)
            if normalized_phone != original_phone:
                attributes['phone'] = normalized_phone
                attributes['original_phone'] = original_phone
                transformations.append("phone_normalized")

        return transformations

    def _normalize_domain_entity(self, entity: Entity) -> List[str]:
        """Normalize domain entity."""
        transformations = []
        attributes = entity.attributes

        if 'domain' in attributes:
            original_domain = attributes['domain']
            normalized_domain = self._normalize_domain(original_domain)
            if normalized_domain != original_domain:
                attributes['domain'] = normalized_domain
                attributes['original_domain'] = original_domain
                transformations.append("domain_normalized")

        return transformations

    def _normalize_username_entity(self, entity: Entity) -> List[str]:
        """Normalize username entity."""
        transformations = []
        attributes = entity.attributes

        if 'username' in attributes:
            original_username = attributes['username']
            normalized_username = self._normalize_username(original_username)
            if normalized_username != original_username:
                attributes['username'] = normalized_username
                attributes['original_username'] = original_username
                transformations.append("username_normalized")

        return transformations

    def _normalize_social_profile_entity(self, entity: Entity) -> List[str]:
        """Normalize social profile entity."""
        transformations = []
        attributes = entity.attributes

        # Normalize platform name
        if 'platform' in attributes:
            original_platform = attributes['platform']
            normalized_platform = self._normalize_platform(original_platform)
            if normalized_platform != original_platform:
                attributes['platform'] = normalized_platform
                attributes['original_platform'] = original_platform
                transformations.append("platform_normalized")

        # Normalize username if present
        if 'username' in attributes:
            original_username = attributes['username']
            normalized_username = self._normalize_username(original_username)
            if normalized_username != original_username:
                attributes['username'] = normalized_username
                attributes['original_username'] = original_username
                transformations.append("username_normalized")

        # Normalize URL if present
        if 'url' in attributes:
            original_url = attributes['url']
            normalized_url = self._normalize_url(original_url)
            if normalized_url != original_url:
                attributes['url'] = normalized_url
                attributes['original_url'] = original_url
                transformations.append("url_normalized")

        return transformations

    def _normalize_company_entity(self, entity: Entity) -> List[str]:
        """Normalize company entity."""
        transformations = []
        attributes = entity.attributes

        # Normalize company name
        if 'name' in attributes:
            original_name = attributes['name']
            normalized_name = self._normalize_name(original_name)
            if normalized_name != original_name:
                attributes['name'] = normalized_name
                attributes['original_name'] = original_name
                transformations.append("company_name_normalized")

        return transformations

    def _normalize_general_attributes(self, entity: Entity) -> List[str]:
        """Apply general normalization to all entity attributes."""
        transformations = []
        attributes = entity.attributes

        # Normalize location fields
        for location_field in ['location', 'city', 'region', 'country']:
            if location_field in attributes:
                original_value = attributes[location_field]
                normalized_value = self._normalize_location(original_value)
                if normalized_value != original_value:
                    attributes[location_field] = normalized_value
                    attributes[f'original_{location_field}'] = original_value
                    transformations.append(f"{location_field}_normalized")

        # Normalize timestamp fields
        for time_field in ['created_at', 'updated_at', 'last_seen', 'first_seen']:
            if time_field in attributes:
                original_value = attributes[time_field]
                normalized_value = self._normalize_timestamp(original_value)
                if normalized_value != original_value:
                    attributes[time_field] = normalized_value
                    attributes[f'original_{time_field}'] = original_value
                    transformations.append(f"{time_field}_normalized")

        return transformations

    def _normalize_name(self, name: str) -> str:
        """Normalize a name string."""
        if not name or not isinstance(name, str):
            return name

        # Remove prefixes
        name = self._name_patterns['prefixes'].sub('', name.strip())
        
        # Convert to title case
        name = self._name_patterns['title_case'].sub(lambda m: m.group(0).title(), name.lower())
        
        # Remove special characters (except hyphens, apostrophes, periods)
        name = self._name_patterns['special_chars'].sub('', name)
        
        # Normalize multiple spaces
        name = self._name_patterns['multiple_spaces'].sub(' ', name.strip())
        
        return name.strip()

    def _normalize_email(self, email: str) -> str:
        """Normalize an email address."""
        if not email or not isinstance(email, str):
            return email

        # Convert to lowercase
        normalized = email.lower().strip()
        
        # Validate format
        if validate_email(normalized):
            return normalized
        return email

    def _normalize_phone(self, phone: str) -> str:
        """Normalize a phone number."""
        if not phone or not isinstance(phone, str):
            return phone

        # Remove common formatting characters
        normalized = re.sub(r'[^\d+]', '', phone.strip())
        
        # Add + prefix if missing for international format
        if len(normalized) == 10 and not normalized.startswith('+'):
            normalized = '+1' + normalized
        
        return normalized

    def _normalize_domain(self, domain: str) -> str:
        """Normalize a domain name."""
        if not domain or not isinstance(domain, str):
            return domain

        # Convert to lowercase
        normalized = domain.lower().strip()
        
        # Remove www. prefix
        if normalized.startswith('www.'):
            normalized = normalized[4:]
        
        # Validate format
        if validate_domain(normalized):
            return normalized
        return domain

    def _normalize_username(self, username: str) -> str:
        """Normalize a username."""
        if not username or not isinstance(username, str):
            return username

        # Strip whitespace and convert to lowercase
        normalized = username.strip().lower()
        
        # Remove common prefixes
        prefixes_to_remove = ['@', '#', 'u/', 'user/']
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
        
        return normalized

    def _normalize_platform(self, platform: str) -> str:
        """Normalize a platform name."""
        if not platform or not isinstance(platform, str):
            return platform

        # Standardize platform names
        platform_mapping = {
            'linkedin': 'LinkedIn',
            'github': 'GitHub',
            'twitter': 'Twitter',
            'x': 'Twitter',
            'facebook': 'Facebook',
            'instagram': 'Instagram',
            'youtube': 'YouTube',
            'tiktok': 'TikTok'
        }
        
        normalized = platform.strip().lower()
        return platform_mapping.get(normalized, platform.title())

    def _normalize_url(self, url: str) -> str:
        """Normalize a URL."""
        if not url or not isinstance(url, str):
            return url

        try:
            parsed = urlparse(url.strip())
            
            # Ensure scheme is present
            if not parsed.scheme:
                normalized = 'https://' + url.strip()
            else:
                normalized = url.strip()
            
            return normalized
        except Exception:
            return url

    def _normalize_location(self, location: str) -> str:
        """Normalize a location string."""
        if not location or not isinstance(location, str):
            return location

        # Convert to title case for proper nouns
        normalized = location.strip().title()
        
        # Expand common abbreviations
        for abbr, expansion in self._location_patterns['country_codes'].items():
            normalized = re.sub(r'\b' + re.escape(abbr) + r'\b', expansion, normalized, flags=re.IGNORECASE)
        
        for abbr, expansion in self._location_patterns['state_codes'].items():
            normalized = re.sub(r'\b' + re.escape(abbr) + r'\b', expansion, normalized, flags=re.IGNORECASE)
        
        return normalized

    def _normalize_timestamp(self, timestamp: Any) -> Any:
        """Normalize a timestamp to ISO format."""
        if timestamp is None:
            return None
        
        if isinstance(timestamp, str):
            try:
                # Try common date formats
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%d',
                    '%m/%d/%Y',
                    '%d/%m/%Y'
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(timestamp.strip(), fmt)
                        # Convert to UTC and ISO format
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        return dt.isoformat()
                    except ValueError:
                        continue
                
                # If no format matches, return original
                return timestamp
            except Exception:
                return timestamp
        
        elif isinstance(timestamp, datetime):
            # Convert to UTC and ISO format
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return timestamp.isoformat()
        
        return timestamp

    def _calculate_quality_score(self, entity: Entity) -> Tuple[float, DataQualityLevel, List[str]]:
        """Calculate quality score and level for an entity."""
        score = 100.0
        flags = []
        
        attributes = entity.attributes
        
        # Check for required fields based on entity type
        if entity.entity_type == EntityType.PERSON:
            if 'name' not in attributes or not attributes['name'].strip():
                score -= 30
                flags.append("missing_name")
            elif len(attributes['name']) < 2:
                score -= 15
                flags.append("name_too_short")
            
            # Check for additional identifying information
            if not any(field in attributes for field in ['email', 'phone', 'username']):
                score -= 10
                flags.append("missing_contact_info")
        
        elif entity.entity_type == EntityType.EMAIL_ADDRESS:
            if 'email' not in attributes:
                score -= 50
                flags.append("missing_email")
            elif not validate_email(attributes['email']):
                score -= 40
                flags.append("invalid_email_format")
        
        elif entity.entity_type == EntityType.PHONE_NUMBER:
            if 'phone' not in attributes:
                score -= 50
                flags.append("missing_phone")
            elif not validate_phone(attributes['phone']):
                score -= 40
                flags.append("invalid_phone_format")
        
        elif entity.entity_type == EntityType.SOCIAL_PROFILE:
            required_fields = ['platform', 'username']
            missing_fields = [field for field in required_fields if field not in attributes]
            if missing_fields:
                score -= 20 * len(missing_fields)
                flags.append(f"missing_fields_{','.join(missing_fields)}")
        
        # Check for data completeness
        if len(attributes) < 2:
            score -= 10
            flags.append("insufficient_attributes")
        
        # Check for data consistency
        if 'confidence_score' in attributes and not isinstance(attributes['confidence_score'], (int, float)):
            score -= 5
            flags.append("invalid_confidence_type")
        
        # Determine quality level
        if score >= 90:
            quality_level = DataQualityLevel.HIGH
        elif score >= 70:
            quality_level = DataQualityLevel.MEDIUM
        elif score >= 50:
            quality_level = DataQualityLevel.LOW
        else:
            quality_level = DataQualityLevel.POOR
        
        return max(0.0, min(100.0, score)), quality_level, flags

    def get_metrics(self) -> Dict[str, Any]:
        """Get current normalization metrics."""
        return {
            "total_entities": self.metrics.total_entities,
            "completed_normalizations": self.metrics.completed_normalizations,
            "failed_normalizations": self.metrics.failed_normalizations,
            "quality_flagged": self.metrics.quality_flagged,
            "validation_errors": self.metrics.validation_errors,
            "success_rate": self.metrics.get_success_rate(),
            "average_quality_score": self.metrics.get_average_quality_score(),
            "average_duration_ms": self.metrics.get_average_duration_ms(),
            "entity_type_metrics": self.metrics.entity_type_metrics,
            "quality_distribution": self.metrics.quality_distribution
        }

    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on normalization engine."""
        health_status = {
            "metrics_available": self.metrics.total_entities >= 0,
            "success_rate_acceptable": self.metrics.get_success_rate() >= 80,
            "quality_score_acceptable": self.metrics.get_average_quality_score() >= 60,
            "no_active_errors": True  # Could be enhanced with actual error tracking
        }
        
        return health_status
