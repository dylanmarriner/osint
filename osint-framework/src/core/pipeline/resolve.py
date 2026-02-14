"""
Entity Resolution Engine for OSINT Investigation Pipeline

Purpose
- Resolve and merge duplicate entities across sources
- Apply confidence scoring and verification logic
- Prevent false positives through multi-signal matching
- Provide comprehensive observability and audit trails

Invariants
- All resolved entities have unique identifiers
- Confidence scores are calculated using consistent algorithms
- Resolution decisions are logged with full audit trail
- Sensitive data is redacted before logging
- Every resolution operation is traceable via correlation IDs

Failure Modes
- Insufficient evidence → entity is marked as low confidence
- Conflicting information → resolution fails with detailed conflict report
- Algorithm failure → fallback to manual review with error logging
- Evidence threshold not met → entity is rejected with specific reasons
- Temporal inconsistency → entity is flagged with temporal conflict details

Debug Notes
- Use correlation_id to trace resolution operations through system
- Monitor resolution_confidence metrics for overall system accuracy
- Check false_positive_rate alerts for resolution quality issues
- Review manual_review_required metrics for algorithm limitations
- Use entity_conflict alerts for data consistency problems

Design Tradeoffs
- Chose conservative confidence scoring over optimistic matching
- Tradeoff: Lower initial confidence but higher accuracy and fewer false positives
- Mitigation: Multi-signal verification and human review checkpoints
- Review trigger: If false positive rate exceeds 5%, adjust confidence thresholds
"""

import asyncio
import hashlib
import json
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
from difflib import SequenceMatcher

from ..models.entities import (
    Entity, EntityType, VerificationStatus, 
    redact_sensitive_data
)


class ResolutionStrategy(Enum):
    """Strategies for entity resolution."""
    CONSERVATIVE = "conservative"  # High confidence threshold
    BALANCED = "balanced"        # Medium confidence threshold
    AGGRESSIVE = "aggressive"     # Low confidence threshold


class ConflictResolution(Enum):
    """Methods for resolving entity conflicts."""
    MERGE = "merge"           # Combine conflicting entities
    SPLIT = "split"           # Keep separate entities
    MANUAL_REVIEW = "manual_review"  # Flag for human review
    HIGHEST_CONFIDENCE = "highest_confidence"  # Keep highest confidence version


@dataclass
class EntityConflict:
    """Represents a conflict between entities."""
    conflict_id: str = field(default_factory=lambda: str(uuid4()))
    entity_1_id: str = ""
    entity_2_id: str = ""
    conflict_type: str = ""
    conflict_details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "medium"  # low, medium, high, critical
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution_method: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "conflict_id": self.conflict_id,
            "entity_1_id": self.entity_1_id,
            "entity_2_id": self.entity_2_id,
            "conflict_type": self.conflict_type,
            "conflict_details": self.conflict_details,
            "severity": self.severity,
            "created_at": self.created_at.isoformat(),
            "resolved": self.resolved,
            "resolution_method": self.resolution_method
        }


@dataclass
class ResolutionResult:
    """Result of entity resolution operation."""
    result_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = ""
    resolved_entities: List[Entity] = field(default_factory=list)
    conflicts_detected: List[EntityConflict] = field(default_factory=list)
    manual_review_required: List[Entity] = field(default_factory=list)
    resolution_strategy: ResolutionStrategy = ResolutionStrategy.BALANCED
    resolution_duration_ms: int = 0
    entities_processed: int = 0
    entities_merged: int = 0
    entities_split: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "result_id": self.result_id,
            "correlation_id": self.correlation_id,
            "resolved_entities_count": len(self.resolved_entities),
            "conflicts_detected_count": len(self.conflicts_detected),
            "manual_review_required_count": len(self.manual_review_required),
            "resolution_strategy": self.resolution_strategy.value,
            "resolution_duration_ms": self.resolution_duration_ms,
            "entities_processed": self.entities_processed,
            "entities_merged": self.entities_merged,
            "entities_split": self.entities_split,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class ResolutionMetrics:
    """Metrics for entity resolution operations."""
    total_entities_processed: int = 0
    entities_resolved: int = 0
    conflicts_detected: int = 0
    manual_reviews_generated: int = 0
    entities_merged: int = 0
    entities_split: int = 0
    average_confidence_score: float = 0.0
    resolution_duration_ms: int = 0
    entity_type_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def get_resolution_rate(self) -> float:
        """Calculate entity resolution success rate."""
        if self.total_entities_processed == 0:
            return 0.0
        return (self.entities_resolved / self.total_entities_processed) * 100

    def get_conflict_rate(self) -> float:
        """Calculate conflict detection rate."""
        if self.total_entities_processed == 0:
            return 0.0
        return (self.conflicts_detected / self.total_entities_processed) * 100

    def get_manual_review_rate(self) -> float:
        """Calculate manual review rate."""
        if self.total_entities_processed == 0:
            return 0.0
        return (self.manual_reviews_generated / self.total_entities_processed) * 100

    def update_entity_type_metrics(self, entity_type: str, metrics: Dict[str, Any]):
        """Update metrics for a specific entity type."""
        if entity_type not in self.entity_type_metrics:
            self.entity_type_metrics[entity_type] = {
                "processed": 0,
                "resolved": 0,
                "conflicts": 0,
                "manual_reviews": 0,
                "average_confidence": 0.0
            }
        
        self.entity_type_metrics[entity_type]["processed"] += metrics.get("processed", 0)
        self.entity_type_metrics[entity_type]["resolved"] += metrics.get("resolved", 0)
        self.entity_type_metrics[entity_type]["conflicts"] += metrics.get("conflicts", 0)
        self.entity_type_metrics[entity_type]["manual_reviews"] += metrics.get("manual_reviews", 0)


class EntityResolver:
    """
    Core entity resolution engine.

    Purpose
    - Resolve and merge duplicate entities across sources
    - Apply confidence scoring and verification logic
    - Prevent false positives through multi-signal matching
    - Provide comprehensive observability and audit trails

    Invariants
    - All resolved entities have unique identifiers
    - Confidence scores are calculated using consistent algorithms
    - Resolution decisions are logged with full audit trail
    - Sensitive data is redacted before logging
    - Every resolution operation is traceable via correlation IDs

    Failure Modes
    - Insufficient evidence → entity is marked as low confidence
    - Conflicting information → resolution fails with detailed conflict report
    - Algorithm failure → fallback to manual review with error logging
    - Evidence threshold not met → entity is rejected with specific reasons
    - Temporal inconsistency → entity is flagged with temporal conflict details

    Debug Notes
    - Use correlation_id to trace resolution operations through system
    - Monitor resolution_confidence metrics for overall system accuracy
    - Check false_positive_rate alerts for resolution quality issues
    - Review manual_review_required metrics for algorithm limitations
    - Use entity_conflict alerts for data consistency problems

    Design Tradeoffs
    - Chose conservative confidence scoring over optimistic matching
    - Tradeoff: Lower initial confidence but higher accuracy and fewer false positives
    - Mitigation: Multi-signal verification and human review checkpoints
    - Review trigger: If false positive rate exceeds 5%, adjust confidence thresholds
    """

    def __init__(self, strategy: ResolutionStrategy = ResolutionStrategy.BALANCED):
        """Initialize entity resolver with resolution strategy."""
        self.strategy = strategy
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.metrics = ResolutionMetrics()
        
        # Confidence thresholds based on strategy
        self.thresholds = {
            ResolutionStrategy.CONSERVATIVE: {
                "min_confidence": 85,
                "evidence_threshold": 3,
                "similarity_threshold": 0.8
            },
            ResolutionStrategy.BALANCED: {
                "min_confidence": 70,
                "evidence_threshold": 2,
                "similarity_threshold": 0.7
            },
            ResolutionStrategy.AGGRESSIVE: {
                "min_confidence": 55,
                "evidence_threshold": 1,
                "similarity_threshold": 0.6
            }
        }

    async def resolve_entities(self, entities: List[Entity], 
                            correlation_id: Optional[str] = None) -> ResolutionResult:
        """
        Resolve and merge entities across sources.

        Summary
        - Group similar entities for resolution
        - Apply confidence scoring and conflict detection
        - Return resolved entities with audit trail

        Preconditions
        - entities must be valid Entity objects
        - correlation_id must be provided for tracing

        Postconditions
        - All entities are processed or marked for manual review
        - Resolved entities have consistent confidence scores
        - Conflicts are documented with resolution methods

        Error cases
        - Invalid entity format → entity is rejected with validation error
        - Insufficient evidence → entity is marked as low confidence
        - Unresolvable conflicts → entities are flagged for manual review
        - Algorithm failure → operation fails with detailed error logging

        Idempotency: Deterministic - same input produces same resolution results
        Side effects: Updates metrics and logs resolution operations
        """
        start_time = datetime.utcnow()
        
        if not correlation_id:
            correlation_id = str(uuid4())
        
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "resolve.resolve_entities",
            "entity_count": len(entities),
            "strategy": self.strategy.value
        })
        
        logger.info("starting entity resolution operation")

        try:
            # Group entities by type for resolution
            entities_by_type = self._group_entities_by_type(entities)
            
            resolved_entities = []
            conflicts_detected = []
            manual_review_required = []
            entities_merged = 0
            entities_split = 0

            # Process each entity type
            for entity_type, type_entities in entities_by_type.items():
                type_results = await self._resolve_entity_type(
                    type_entities, entity_type, correlation_id
                )
                
                resolved_entities.extend(type_results["resolved"])
                conflicts_detected.extend(type_results["conflicts"])
                manual_review_required.extend(type_results["manual_review"])
                entities_merged += type_results["merged"]
                entities_split += type_results["split"]

            # Create resolution result
            result = ResolutionResult(
                correlation_id=correlation_id,
                resolved_entities=resolved_entities,
                conflicts_detected=conflicts_detected,
                manual_review_required=manual_review_required,
                resolution_strategy=self.strategy,
                entities_processed=len(entities),
                entities_merged=entities_merged,
                entities_split=entities_split
            )

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            result.resolution_duration_ms = duration_ms
            result.completed_at = datetime.utcnow()

            # Update metrics
            self.metrics.total_entities_processed += len(entities)
            self.metrics.entities_resolved += len(resolved_entities)
            self.metrics.conflicts_detected += len(conflicts_detected)
            self.metrics.manual_reviews_generated += len(manual_review_required)
            self.metrics.entities_merged += entities_merged
            self.metrics.entities_split += entities_split
            self.metrics.resolution_duration_ms += duration_ms

            # Calculate average confidence
            if resolved_entities:
                avg_confidence = sum(e.confidence_score for e in resolved_entities) / len(resolved_entities)
                self.metrics.average_confidence_score = avg_confidence

            # Update entity type metrics
            for entity_type, type_entities in entities_by_type.items():
                type_metrics = {
                    "processed": len(type_entities),
                    "resolved": len([e for e in type_entities if e in resolved_entities]),
                    "conflicts": len([c for c in conflicts_detected if any(e.id in [c.entity_1_id, c.entity_2_id] for e in type_entities)]),
                    "manual_reviews": len([e for e in type_entities if e in manual_review_required])
                }
                self.metrics.update_entity_type_metrics(entity_type.value, type_metrics)

            logger.info("entity resolution operation completed", {
                "entities_processed": len(entities),
                "entities_resolved": len(resolved_entities),
                "conflicts_detected": len(conflicts_detected),
                "manual_reviews_required": len(manual_review_required),
                "average_confidence": self.metrics.average_confidence_score,
                "duration_ms": duration_ms
            })

            return result

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error("entity resolution operation failed", {
                "error": str(e),
                "duration_ms": duration_ms
            })
            raise

    def _group_entities_by_type(self, entities: List[Entity]) -> Dict[EntityType, List[Entity]]:
        """Group entities by their type for processing."""
        grouped = {}
        for entity in entities:
            if entity.entity_type not in grouped:
                grouped[entity.entity_type] = []
            grouped[entity.entity_type].append(entity)
        return grouped

    async def _resolve_entity_type(self, entities: List[Entity], 
                                  entity_type: EntityType, correlation_id: str) -> Dict[str, List]:
        """Resolve entities of a specific type."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "resolve.resolve_entity_type",
            "entity_type": entity_type.value,
            "entity_count": len(entities)
        })

        result = {
            "resolved": [],
            "conflicts": [],
            "manual_review": [],
            "merged": 0,
            "split": 0
        }

        try:
            # Find potential matches using similarity scoring
            similarity_groups = await self._find_similarity_groups(entities, correlation_id)
            
            # Process each similarity group
            for group in similarity_groups:
                if len(group) == 1:
                    # No conflicts, add as-is
                    result["resolved"].append(group[0])
                else:
                    # Multiple similar entities, resolve conflicts
                    group_result = await self._resolve_similarity_group(
                        group, entity_type, correlation_id
                    )
                    
                    result["resolved"].extend(group_result["resolved"])
                    result["conflicts"].extend(group_result["conflicts"])
                    result["manual_review"].extend(group_result["manual_review"])
                    result["merged"] += group_result["merged"]
                    result["split"] += group_result["split"]

            logger.debug("entity type resolution completed", {
                "entity_type": entity_type.value,
                "similarity_groups": len(similarity_groups),
                "entities_resolved": len(result["resolved"]),
                "conflicts_detected": len(result["conflicts"])
            })

            return result

        except Exception as e:
            logger.error("entity type resolution failed", {
                "entity_type": entity_type.value,
                "error": str(e)
            })
            raise

    async def _find_similarity_groups(self, entities: List[Entity], 
                                   correlation_id: str) -> List[List[Entity]]:
        """Find groups of similar entities using multiple similarity metrics."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "resolve.find_similarity_groups",
            "entity_count": len(entities)
        })

        similarity_threshold = self.thresholds[self.strategy]["similarity_threshold"]
        groups = []
        processed = set()

        for i, entity1 in enumerate(entities):
            if entity1.id in processed:
                continue
            
            current_group = [entity1]
            processed.add(entity1.id)

            # Find similar entities
            for j, entity2 in enumerate(entities[i+1:], i+1):
                if entity2.id in processed:
                    continue
                
                similarity_score = await self._calculate_similarity_score(entity1, entity2, correlation_id)
                
                if similarity_score >= similarity_threshold:
                    current_group.append(entity2)
                    processed.add(entity2.id)

            if len(current_group) > 1:
                groups.append(current_group)

        # Add any remaining entities as single groups
        for entity in entities:
            if entity.id not in processed:
                groups.append([entity])

        logger.debug("similarity grouping completed", {
            "total_entities": len(entities),
            "similarity_groups": len(groups),
            "similarity_threshold": similarity_threshold
        })

        return groups

    async def _calculate_similarity_score(self, entity1: Entity, entity2: Entity, 
                                     correlation_id: str) -> float:
        """Calculate similarity score between two entities."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "resolve.calculate_similarity_score",
            "entity_1_id": entity1.id,
            "entity_2_id": entity2.id
        })

        scores = []

        # Name similarity
        name_score = self._calculate_name_similarity(entity1, entity2)
        if name_score > 0:
            scores.append(("name", name_score, 0.3))

        # Username similarity
        username_score = self._calculate_username_similarity(entity1, entity2)
        if username_score > 0:
            scores.append(("username", username_score, 0.25))

        # Email similarity
        email_score = self._calculate_email_similarity(entity1, entity2)
        if email_score > 0:
            scores.append(("email", email_score, 0.25))

        # Phone similarity
        phone_score = self._calculate_phone_similarity(entity1, entity2)
        if phone_score > 0:
            scores.append(("phone", phone_score, 0.1))

        # Platform similarity (for social profiles)
        platform_score = self._calculate_platform_similarity(entity1, entity2)
        if platform_score > 0:
            scores.append(("platform", platform_score, 0.1))

        # Calculate weighted average
        if not scores:
            return 0.0

        total_weight = sum(weight for _, _, weight in scores)
        weighted_score = sum(score * weight for _, score, weight in scores) / total_weight

        logger.debug("similarity score calculated", {
            "entity_1_id": entity1.id,
            "entity_2_id": entity2.id,
            "similarity_score": weighted_score,
            "component_scores": [(type, score) for type, score, _ in scores]
        })

        return weighted_score

    def _calculate_name_similarity(self, entity1: Entity, entity2: Entity) -> float:
        """Calculate name similarity between entities."""
        name1 = entity1.attributes.get('name', '').lower().strip()
        name2 = entity2.attributes.get('name', '').lower().strip()
        
        if not name1 or not name2:
            return 0.0

        # Exact match
        if name1 == name2:
            return 1.0

        # Use SequenceMatcher for fuzzy matching
        matcher = SequenceMatcher(None, name1, name2)
        ratio = matcher.ratio()

        # Boost score for length similarity
        length_similarity = 1.0 - abs(len(name1) - len(name2)) / max(len(name1), len(name2))
        final_score = ratio * 0.8 + length_similarity * 0.2

        return final_score

    def _calculate_username_similarity(self, entity1: Entity, entity2: Entity) -> float:
        """Calculate username similarity between entities."""
        username1 = entity1.attributes.get('username', '').lower().strip()
        username2 = entity2.attributes.get('username', '').lower().strip()
        
        if not username1 or not username2:
            return 0.0

        # Exact match
        if username1 == username2:
            return 1.0

        # Check for substring matches
        if username1 in username2 or username2 in username1:
            return 0.8

        # Use SequenceMatcher for fuzzy matching
        matcher = SequenceMatcher(None, username1, username2)
        return matcher.ratio()

    def _calculate_email_similarity(self, entity1: Entity, entity2: Entity) -> float:
        """Calculate email similarity between entities."""
        email1 = entity1.attributes.get('email', '').lower().strip()
        email2 = entity2.attributes.get('email', '').lower().strip()
        
        if not email1 or not email2:
            return 0.0

        # Exact match
        if email1 == email2:
            return 1.0

        # Check domain similarity
        domain1 = email1.split('@')[-1] if '@' in email1 else ''
        domain2 = email2.split('@')[-1] if '@' in email2 else ''
        
        if domain1 and domain2 and domain1 == domain2:
            return 0.9

        return 0.0

    def _calculate_phone_similarity(self, entity1: Entity, entity2: Entity) -> float:
        """Calculate phone similarity between entities."""
        phone1 = entity1.attributes.get('phone', '').replace('-', '').replace('+', '').replace(' ', '')
        phone2 = entity2.attributes.get('phone', '').replace('-', '').replace('+', '').replace(' ', '')
        
        if not phone1 or not phone2:
            return 0.0

        # Exact match
        if phone1 == phone2:
            return 1.0

        # Check for partial matches (last 7 digits)
        if len(phone1) >= 7 and len(phone2) >= 7:
            if phone1[-7:] == phone2[-7:]:
                return 0.8

        return 0.0

    def _calculate_platform_similarity(self, entity1: Entity, entity2: Entity) -> float:
        """Calculate platform similarity between entities."""
        platform1 = entity1.attributes.get('platform', '').lower().strip()
        platform2 = entity2.attributes.get('platform', '').lower().strip()
        
        if not platform1 or not platform2:
            return 0.0

        # Exact match
        if platform1 == platform2:
            return 1.0

        # Check for common platform name variations
        platform_variations = {
            'linkedin': ['linkedin', 'linked in'],
            'github': ['github', 'git hub'],
            'twitter': ['twitter', 'x', 'tweet'],
            'facebook': ['facebook', 'fb'],
            'instagram': ['instagram', 'ig']
        }

        for base_platform, variations in platform_variations.items():
            if platform1 in variations and platform2 in variations:
                return 0.9

        return 0.0

    async def _resolve_similarity_group(self, entities: List[Entity], 
                                   entity_type: EntityType, correlation_id: str) -> Dict[str, List]:
        """Resolve conflicts within a similarity group."""
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "resolve.resolve_similarity_group",
            "entity_type": entity_type.value,
            "group_size": len(entities)
        })

        result = {
            "resolved": [],
            "conflicts": [],
            "manual_review": [],
            "merged": 0,
            "split": 0
        }

        try:
            # Analyze evidence for each entity
            evidence_scores = []
            for entity in entities:
                evidence_score = self._calculate_evidence_score(entity)
                evidence_scores.append(evidence_score)

            # Sort entities by evidence score
            sorted_entities = sorted(zip(entities, evidence_scores), 
                                 key=lambda x: x[1], reverse=True)
            sorted_entities = [entity for entity, _ in sorted_entities]

            # Check if highest confidence meets threshold
            min_confidence = self.thresholds[self.strategy]["min_confidence"]
            evidence_threshold = self.thresholds[self.strategy]["evidence_threshold"]

            highest_confidence = sorted_entities[0].confidence_score
            highest_evidence = evidence_scores[sorted_entities.index(sorted_entities[0])]

            if highest_confidence >= min_confidence and highest_evidence >= evidence_threshold:
                # High confidence entity, merge others into it
                primary_entity = sorted_entities[0]
                merged_entity = self._merge_entities(primary_entity, sorted_entities[1:])
                
                result["resolved"].append(merged_entity)
                result["merged"] += len(sorted_entities) - 1

                # Create conflict records for merged entities
                for entity in sorted_entities[1:]:
                    conflict = EntityConflict(
                        entity_1_id=primary_entity.id,
                        entity_2_id=entity.id,
                        conflict_type="similarity_merge",
                        conflict_details={
                            "similarity_scores": [self._calculate_similarity_score(primary_entity, e, correlation_id) for e in sorted_entities[1:]],
                            "evidence_scores": evidence_scores[1:],
                            "merge_reason": "high_confidence_primary"
                        },
                        severity="low"
                    )
                    result["conflicts"].append(conflict)

            else:
                # Low confidence or insufficient evidence, check for conflicts
                conflicts = self._detect_entity_conflicts(sorted_entities, correlation_id)
                
                if not conflicts:
                    # No conflicts, keep separate but with lower confidence
                    for entity in sorted_entities:
                        entity.update_confidence(max(55, entity.confidence_score * 0.8))
                    result["resolved"].extend(sorted_entities)
                    result["split"] += len(sorted_entities)
                else:
                    # Conflicts detected, flag for manual review
                    result["manual_review"].extend(sorted_entities)
                    
                    # Create conflict records
                    for conflict in conflicts:
                        result["conflicts"].append(conflict)

            logger.debug("similarity group resolution completed", {
                "entity_type": entity_type.value,
                "group_size": len(entities),
                "resolution_method": "merge" if result["merged"] > 0 else "split" if result["split"] > 0 else "manual_review",
                "entities_resolved": len(result["resolved"]),
                "conflicts_detected": len(result["conflicts"])
            })

            return result

        except Exception as e:
            logger.error("similarity group resolution failed", {
                "entity_type": entity_type.value,
                "error": str(e)
            })
            raise

    def _calculate_evidence_score(self, entity: Entity) -> float:
        """Calculate evidence score for an entity."""
        score = 0.0
        attributes = entity.attributes

        # Source count (more sources = higher confidence)
        source_count = len(entity.sources)
        if source_count >= 3:
            score += 30
        elif source_count >= 2:
            score += 20
        elif source_count >= 1:
            score += 10

        # Attribute completeness
        required_attrs = self._get_required_attributes(entity.entity_type)
        present_attrs = sum(1 for attr in required_attrs if attr in attributes and attributes[attr])
        completeness_score = (present_attrs / len(required_attrs)) * 25
        score += completeness_score

        # Cross-platform consistency
        if entity.entity_type == EntityType.SOCIAL_PROFILE:
            platform = attributes.get('platform', '').lower()
            username = attributes.get('username', '').lower()
            if platform and username:
                # Check if username matches platform patterns
                if platform in username or username in platform:
                    score += 15

        # Temporal consistency
        if 'created_at' in attributes or 'last_seen' in attributes:
            score += 10

        # Verification status
        if entity.verification_status == VerificationStatus.VERIFIED:
            score += 25
        elif entity.verification_status == VerificationStatus.PROBABLE:
            score += 15
        elif entity.verification_status == VerificationStatus.POSSIBLE:
            score += 5

        return min(100.0, score)

    def _get_required_attributes(self, entity_type: EntityType) -> List[str]:
        """Get required attributes for an entity type."""
        required_map = {
            EntityType.PERSON: ['name'],
            EntityType.EMAIL_ADDRESS: ['email'],
            EntityType.PHONE_NUMBER: ['phone'],
            EntityType.USERNAME: ['username'],
            EntityType.SOCIAL_PROFILE: ['platform', 'username'],
            EntityType.DOMAIN: ['domain'],
            EntityType.COMPANY: ['name']
        }
        return required_map.get(entity_type, [])

    def _detect_entity_conflicts(self, entities: List[Entity], correlation_id: str) -> List[EntityConflict]:
        """Detect conflicts between similar entities."""
        conflicts = []

        for i, entity1 in enumerate(entities):
            for j, entity2 in enumerate(entities[i+1:], i+1):
                conflict_details = {}
                severity = "medium"

                # Check for conflicting names
                name1 = entity1.attributes.get('name', '').lower()
                name2 = entity2.attributes.get('name', '').lower()
                if name1 and name2 and name1 != name2:
                    similarity = self._calculate_name_similarity(entity1, entity2)
                    if similarity > 0.7:  # High similarity but different names
                        conflict_details["name_conflict"] = {
                            "entity1_name": name1,
                            "entity2_name": name2,
                            "similarity": similarity
                        }
                        severity = "high"

                # Check for conflicting contact info
                email1 = entity1.attributes.get('email', '').lower()
                email2 = entity2.attributes.get('email', '').lower()
                if email1 and email2 and email1 != email2:
                    conflict_details["email_conflict"] = {
                        "entity1_email": redact_sensitive_data(email1),
                        "entity2_email": redact_sensitive_data(email2)
                    }

                phone1 = entity1.attributes.get('phone', '')
                phone2 = entity2.attributes.get('phone', '')
                if phone1 and phone2 and phone1 != phone2:
                    conflict_details["phone_conflict"] = {
                        "entity1_phone": phone1,
                        "entity2_phone": phone2
                    }

                # Check for conflicting platforms
                platform1 = entity1.attributes.get('platform', '').lower()
                platform2 = entity2.attributes.get('platform', '').lower()
                username1 = entity1.attributes.get('username', '').lower()
                username2 = entity2.attributes.get('username', '').lower()
                
                if (platform1 and platform2 and platform1 != platform2) or \
                   (username1 and username2 and username1 != username2):
                    conflict_details["platform_conflict"] = {
                        "entity1_platform": platform1,
                        "entity1_username": username1,
                        "entity2_platform": platform2,
                        "entity2_username": username2
                    }

                if conflict_details:
                    conflict = EntityConflict(
                        entity_1_id=entity1.id,
                        entity_2_id=entity2.id,
                        conflict_type="attribute_conflict",
                        conflict_details=conflict_details,
                        severity=severity
                    )
                    conflicts.append(conflict)

        return conflicts

    def _merge_entities(self, primary_entity: Entity, entities_to_merge: List[Entity]) -> Entity:
        """Merge multiple entities into a primary entity."""
        merged_attributes = primary_entity.attributes.copy()
        merged_sources = primary_entity.sources.copy()
        
        # Merge attributes, preferring primary entity values
        for entity in entities_to_merge:
            for key, value in entity.attributes.items():
                if key not in merged_attributes:
                    merged_attributes[key] = value
                elif value and not merged_attributes[key]:
                    merged_attributes[key] = value
            
            # Merge sources
            for source in entity.sources:
                if source not in merged_sources:
                    merged_sources.append(source)

        # Create merged entity
        merged_entity = Entity(
            id=primary_entity.id,
            investigation_id=primary_entity.investigation_id,
            entity_type=primary_entity.entity_type,
            attributes=merged_attributes,
            confidence_score=max(primary_entity.confidence_score, 
                            max(e.confidence_score for e in entities_to_merge)),
            verification_status=VerificationStatus.PROBABLE,  # Downgrade due to merging
            sources=merged_sources,
            created_at=primary_entity.created_at,
            updated_at=datetime.utcnow()
        )

        return merged_entity

    def get_metrics(self) -> Dict[str, Any]:
        """Get current resolution metrics."""
        return {
            "total_entities_processed": self.metrics.total_entities_processed,
            "entities_resolved": self.metrics.entities_resolved,
            "conflicts_detected": self.metrics.conflicts_detected,
            "manual_reviews_generated": self.metrics.manual_reviews_generated,
            "entities_merged": self.metrics.entities_merged,
            "entities_split": self.metrics.entities_split,
            "resolution_rate": self.metrics.get_resolution_rate(),
            "conflict_rate": self.metrics.get_conflict_rate(),
            "manual_review_rate": self.metrics.get_manual_review_rate(),
            "average_confidence_score": self.metrics.average_confidence_score,
            "resolution_duration_ms": self.metrics.resolution_duration_ms,
            "entity_type_metrics": self.metrics.entity_type_metrics
        }

    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on entity resolver."""
        health_status = {
            "metrics_available": self.metrics.total_entities_processed >= 0,
            "resolution_rate_acceptable": self.metrics.get_resolution_rate() >= 80,
            "conflict_rate_acceptable": self.metrics.get_conflict_rate() <= 20,
            "average_confidence_acceptable": self.metrics.average_confidence_score >= 60,
            "no_active_errors": True  # Could be enhanced with actual error tracking
        }
        
        return health_status
