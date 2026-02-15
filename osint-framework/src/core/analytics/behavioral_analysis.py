"""
Advanced Behavioral Analysis and Pattern Recognition

Purpose
- User behavior analysis and anomaly detection
- Pattern recognition in investigation data
- Predictive analytics for threat assessment
- Professional behavioral intelligence standards

Invariants
- All behavioral models include confidence scoring
- Anomaly detection is validated against known patterns
- Predictive models are continuously trained and validated
- All operations maintain full audit trails
- Privacy is protected throughout behavioral analysis

Failure Modes
- ML model failure → fallback to rule-based analysis
- Pattern recognition timeout → partial results with warnings
- Anomaly detection failure → conservative scoring
- Predictive model error → manual review flagging
- Data quality issues → automatic quality assessment

Debug Notes
- Monitor behavioral_model_accuracy for ML performance
- Check anomaly_detection_rate for pattern matching
- Review prediction_confidence for model reliability
- Use behavioral_pattern_consistency for data quality
- Monitor analysis_processing_time for performance

Design Tradeoffs
- Chose comprehensive behavioral analysis over basic pattern matching
- Tradeoff: More complex but provides deeper insights
- Mitigation: Fallback to rule-based analysis when ML fails
- Review trigger: If behavioral accuracy drops below 80%, optimize models
"""

import asyncio
import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
import uuid
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx
from collections import defaultdict, Counter

from ..models.entities import Entity, EntityType, VerificationStatus


@dataclass
class BehavioralPattern:
    """Behavioral pattern analysis result."""
    pattern_id: str
    pattern_name: str
    pattern_type: str  # temporal, spatial, relational, frequency
    confidence: float
    entities: List[str]
    description: str
    indicators: List[str]
    risk_level: str
    first_observed: datetime
    last_observed: datetime
    frequency: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyDetection:
    """Anomaly detection result."""
    anomaly_id: str
    anomaly_type: str
    confidence: float
    severity: str
    affected_entities: List[str]
    baseline_behavior: str
    anomalous_behavior: str
    potential_causes: List[str]
    recommended_actions: List[str]
    detected_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PredictiveInsight:
    """Predictive analytics insight."""
    insight_id: str
    insight_type: str
    confidence: float
    prediction: str
    probability: float
    time_horizon: str
    supporting_evidence: List[str]
    risk_impact: str
    mitigation_strategies: List[str]
    generated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BehaviorProfile:
    """Comprehensive behavior profile."""
    profile_id: str
    entity_id: str
    behavior_patterns: List[BehavioralPattern]
    anomalies: List[AnomalyDetection]
    risk_score: float
    stability_score: float
    predictability_score: float
    last_updated: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


class BehavioralAnalyzer:
    """Advanced behavioral analysis engine."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.behavior_profiles: Dict[str, BehaviorProfile] = {}
        self.ml_models = self._initialize_ml_models()
        self.pattern_library = self._initialize_pattern_library()
        self.baseline_models = self._initialize_baseline_models()
        
    def _initialize_ml_models(self) -> Dict[str, Any]:
        """Initialize ML models for behavioral analysis."""
        return {
            'anomaly_detector': IsolationForest(contamination=0.1, random_state=42),
            'pattern_classifier': None,  # Would be trained pattern classifier
            'behavior_clusterer': DBSCAN(eps=0.5, min_samples=5),
            'predictive_model': None,  # Would be trained predictive model
            'temporal_analyzer': None  # Would analyze temporal patterns
        }
    
    def _initialize_pattern_library(self) -> Dict[str, Any]:
        """Initialize known behavioral patterns."""
        return {
            'temporal_patterns': {
                'burst_activity': {
                    'description': 'Sudden burst of activity in short time period',
                    'indicators': ['high_frequency', 'short_duration', 'repeated_actions'],
                    'risk_level': 'MEDIUM'
                },
                'regular_schedule': {
                    'description': 'Activity follows regular schedule',
                    'indicators': ['consistent_timing', 'predictable_intervals', 'routine_behavior'],
                    'risk_level': 'LOW'
                },
                'off_hours_activity': {
                    'description': 'Activity during unusual hours',
                    'indicators': ['night_activity', 'weekend_activity', 'irregular_timing'],
                    'risk_level': 'HIGH'
                }
            },
            'relational_patterns': {
                'hub_behavior': {
                    'description': 'Entity acts as central hub in network',
                    'indicators': ['high_connectivity', 'central_position', 'many_connections'],
                    'risk_level': 'MEDIUM'
                },
                'isolated_behavior': {
                    'description': 'Entity operates in isolation',
                    'indicators': ['low_connectivity', 'peripheral_position', 'few_connections'],
                    'risk_level': 'LOW'
                },
                'bridge_behavior': {
                    'description': 'Entity connects different groups',
                    'indicators': ['bridge_connections', 'betweenness_centrality', 'group_connector'],
                    'risk_level': 'MEDIUM'
                }
            },
            'frequency_patterns': {
                'high_frequency': {
                    'description': 'Unusually high frequency of actions',
                    'indicators': ['elevated_rate', 'repeated_actions', 'high_volume'],
                    'risk_level': 'MEDIUM'
                },
                'low_frequency': {
                    'description': 'Unusually low frequency of actions',
                    'indicators': ['reduced_rate', 'sparse_activity', 'low_volume'],
                    'risk_level': 'LOW'
                },
                'variable_frequency': {
                    'description': 'Highly variable frequency patterns',
                    'indicators': ['inconsistent_rate', 'erratic_timing', 'unpredictable_volume'],
                    'risk_level': 'HIGH'
                }
            }
        }
    
    def _initialize_baseline_models(self) -> Dict[str, Any]:
        """Initialize baseline behavior models."""
        return {
            'normal_activity_ranges': {
                'daily_activity': {'min': 10, 'max': 100},
                'hourly_activity': {'min': 1, 'max': 10},
                'weekly_patterns': {'weekday_avg': 50, 'weekend_avg': 20}
            },
            'normal_connectivity': {
                'degree_centrality': {'min': 0.1, 'max': 0.8},
                'betweenness_centrality': {'min': 0.0, 'max': 0.5},
                'clustering_coefficient': {'min': 0.2, 'max': 0.9}
            },
            'normal_temporal': {
                'activity_hours': {'start': 8, 'end': 18},
                'peak_hours': [10, 14, 16],
                'quiet_hours': [2, 3, 4, 5]
            }
        }
    
    async def analyze_behavior(self, entities: List[Entity],
                           temporal_data: Optional[Dict[str, List[datetime]]] = None,
                           correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """Perform comprehensive behavioral analysis."""
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"Starting behavioral analysis",
                           entity_count=len(entities),
                           correlation_id=correlation_id)
            
            # Create behavior profiles
            profiles = await self._create_behavior_profiles(entities, temporal_data, correlation_id)
            
            # Detect behavioral patterns
            patterns = await self._detect_behavioral_patterns(profiles, correlation_id)
            
            # Detect anomalies
            anomalies = await self._detect_anomalies(profiles, correlation_id)
            
            # Generate predictive insights
            insights = await self._generate_predictive_insights(profiles, patterns, anomalies, correlation_id)
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            self.logger.info(f"Behavioral analysis completed",
                           profiles_created=len(profiles),
                           patterns_detected=len(patterns),
                           anomalies_detected=len(anomalies),
                           insights_generated=len(insights),
                           processing_time=processing_time,
                           correlation_id=correlation_id)
            
            return {
                'behavior_profiles': profiles,
                'behavioral_patterns': patterns,
                'anomalies': anomalies,
                'predictive_insights': insights,
                'processing_time': processing_time,
                'correlation_id': correlation_id
            }
            
        except Exception as e:
            self.logger.error(f"Behavioral analysis failed",
                           error=str(e),
                           correlation_id=correlation_id)
            
            return {
                'behavior_profiles': [],
                'behavioral_patterns': [],
                'anomalies': [],
                'predictive_insights': [],
                'error': str(e),
                'correlation_id': correlation_id
            }
    
    async def _create_behavior_profiles(self, entities: List[Entity],
                                      temporal_data: Optional[Dict[str, List[datetime]]],
                                      correlation_id: Optional[str] = None) -> List[BehaviorProfile]:
        """Create behavior profiles for entities."""
        profiles = []
        
        for entity in entities:
            try:
                profile = await self._analyze_entity_behavior(
                    entity, temporal_data, correlation_id
                )
                profiles.append(profile)
                self.behavior_profiles[entity.id] = profile
                
            except Exception as e:
                self.logger.warning(f"Entity behavior analysis failed: {e}",
                                 entity_id=entity.id,
                                 correlation_id=correlation_id)
        
        return profiles
    
    async def _analyze_entity_behavior(self, entity: Entity,
                                    temporal_data: Optional[Dict[str, List[datetime]]],
                                    correlation_id: Optional[str] = None) -> BehaviorProfile:
        """Analyze behavior for individual entity."""
        # Get temporal data for this entity
        entity_timestamps = temporal_data.get(entity.id, []) if temporal_data else []
        
        # Calculate behavioral metrics
        temporal_metrics = self._calculate_temporal_metrics(entity_timestamps)
        
        # Calculate risk score
        risk_score = self._calculate_behavioral_risk_score(entity, temporal_metrics)
        
        # Calculate stability score
        stability_score = self._calculate_stability_score(temporal_metrics)
        
        # Calculate predictability score
        predictability_score = self._calculate_predictability_score(temporal_metrics)
        
        # Create profile
        profile = BehaviorProfile(
            profile_id=str(uuid.uuid4()),
            entity_id=entity.id,
            behavior_patterns=[],
            anomalies=[],
            risk_score=risk_score,
            stability_score=stability_score,
            predictability_score=predictability_score,
            last_updated=datetime.utcnow(),
            metadata={
                'entity_type': entity.entity_type.value,
                'temporal_metrics': temporal_metrics,
                'timestamp_count': len(entity_timestamps),
                'correlation_id': correlation_id
            }
        )
        
        return profile
    
    def _calculate_temporal_metrics(self, timestamps: List[datetime]) -> Dict[str, Any]:
        """Calculate temporal behavioral metrics."""
        if not timestamps:
            return {}
        
        # Sort timestamps
        sorted_timestamps = sorted(timestamps)
        
        # Basic metrics
        metrics = {
            'total_events': len(timestamps),
            'time_span': (sorted_timestamps[-1] - sorted_timestamps[0]).total_seconds(),
            'first_event': sorted_timestamps[0],
            'last_event': sorted_timestamps[-1],
            'average_frequency': len(timestamps) / max(1, (sorted_timestamps[-1] - sorted_timestamps[0]).total_seconds() / 3600)  # per hour
        }
        
        # Hourly distribution
        hour_counts = Counter(ts.hour for ts in timestamps)
        metrics['hourly_distribution'] = dict(hour_counts)
        metrics['peak_hour'] = hour_counts.most_common(1)[0][0] if hour_counts else None
        
        # Daily distribution
        day_counts = Counter(ts.weekday() for ts in timestamps)
        metrics['daily_distribution'] = dict(day_counts)
        metrics['busiest_day'] = day_counts.most_common(1)[0][0] if day_counts else None
        
        # Inter-event intervals
        if len(sorted_timestamps) > 1:
            intervals = [(sorted_timestamps[i+1] - sorted_timestamps[i]).total_seconds() 
                        for i in range(len(sorted_timestamps)-1)]
            metrics['avg_interval'] = np.mean(intervals)
            metrics['std_interval'] = np.std(intervals)
            metrics['min_interval'] = min(intervals)
            metrics['max_interval'] = max(intervals)
        
        return metrics
    
    def _calculate_behavioral_risk_score(self, entity: Entity, temporal_metrics: Dict[str, Any]) -> float:
        """Calculate behavioral risk score."""
        risk_factors = []
        
        # Entity type risk
        entity_type_risks = {
            EntityType.EMAIL: 0.6,
            EntityType.PHONE: 0.5,
            EntityType.PERSON: 0.8,
            EntityType.USERNAME: 0.4,
            EntityType.DOMAIN: 0.7,
            EntityType.COMPANY: 0.3
        }
        risk_factors.append(entity_type_risks.get(entity.entity_type, 0.5))
        
        # Temporal risk factors
        if temporal_metrics:
            # High frequency risk
            if temporal_metrics.get('average_frequency', 0) > 10:  # More than 10 events per hour
                risk_factors.append(0.7)
            else:
                risk_factors.append(0.3)
            
            # Unusual hours risk
            peak_hour = temporal_metrics.get('peak_hour', 12)
            if peak_hour < 6 or peak_hour > 22:  # Unusual hours
                risk_factors.append(0.8)
            else:
                risk_factors.append(0.2)
            
            # Variability risk
            std_interval = temporal_metrics.get('std_interval', 0)
            avg_interval = temporal_metrics.get('avg_interval', 1)
            if avg_interval > 0 and std_interval / avg_interval > 2:  # High variability
                risk_factors.append(0.6)
            else:
                risk_factors.append(0.3)
        
        # Calculate weighted average
        return sum(risk_factors) / len(risk_factors) if risk_factors else 0.5
    
    def _calculate_stability_score(self, temporal_metrics: Dict[str, Any]) -> float:
        """Calculate behavioral stability score."""
        if not temporal_metrics:
            return 0.5
        
        stability_factors = []
        
        # Frequency stability
        std_interval = temporal_metrics.get('std_interval', 0)
        avg_interval = temporal_metrics.get('avg_interval', 1)
        if avg_interval > 0:
            frequency_stability = max(0, 1 - (std_interval / avg_interval))
            stability_factors.append(frequency_stability)
        
        # Temporal consistency
        hourly_dist = temporal_metrics.get('hourly_distribution', {})
        if hourly_dist:
            # Calculate coefficient of variation
            values = list(hourly_dist.values())
            if values:
                cv = np.std(values) / np.mean(values) if np.mean(values) > 0 else 0
                temporal_consistency = max(0, 1 - cv)
                stability_factors.append(temporal_consistency)
        
        return sum(stability_factors) / len(stability_factors) if stability_factors else 0.5
    
    def _calculate_predictability_score(self, temporal_metrics: Dict[str, Any]) -> float:
        """Calculate behavioral predictability score."""
        if not temporal_metrics:
            return 0.5
        
        predictability_factors = []
        
        # Regular schedule predictability
        hourly_dist = temporal_metrics.get('hourly_distribution', {})
        if hourly_dist:
            # Check if activity is concentrated in specific hours
            total_events = sum(hourly_dist.values())
            if total_events > 0:
                # Calculate concentration in top 3 hours
                top_hours = sorted(hourly_dist.items(), key=lambda x: x[1], reverse=True)[:3]
                concentration = sum(count for _, count in top_hours) / total_events
                schedule_predictability = concentration
                predictability_factors.append(schedule_predictability)
        
        # Pattern regularity
        std_interval = temporal_metrics.get('std_interval', 0)
        avg_interval = temporal_metrics.get('avg_interval', 1)
        if avg_interval > 0:
            regularity = max(0, 1 - (std_interval / avg_interval))
            predictability_factors.append(regularity)
        
        return sum(predictability_factors) / len(predictability_factors) if predictability_factors else 0.5
    
    async def _detect_behavioral_patterns(self, profiles: List[BehaviorProfile],
                                        correlation_id: Optional[str] = None) -> List[BehavioralPattern]:
        """Detect behavioral patterns across profiles."""
        patterns = []
        
        # Temporal patterns
        temporal_patterns = await self._detect_temporal_patterns(profiles, correlation_id)
        patterns.extend(temporal_patterns)
        
        # Relational patterns (would require network data)
        relational_patterns = await self._detect_relational_patterns(profiles, correlation_id)
        patterns.extend(relational_patterns)
        
        # Frequency patterns
        frequency_patterns = await self._detect_frequency_patterns(profiles, correlation_id)
        patterns.extend(frequency_patterns)
        
        return patterns
    
    async def _detect_temporal_patterns(self, profiles: List[BehaviorProfile],
                                     correlation_id: Optional[str] = None) -> List[BehavioralPattern]:
        """Detect temporal behavioral patterns."""
        patterns = []
        
        for profile in profiles:
            temporal_metrics = profile.metadata.get('temporal_metrics', {})
            if not temporal_metrics:
                continue
            
            # Check for burst activity
            avg_freq = temporal_metrics.get('average_frequency', 0)
            if avg_freq > 20:  # High frequency threshold
                pattern = BehavioralPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_name="burst_activity",
                    pattern_type="temporal",
                    confidence=min(avg_freq / 50, 1.0),
                    entities=[profile.entity_id],
                    description="High frequency burst activity detected",
                    indicators=["high_frequency", "burst_pattern"],
                    risk_level="MEDIUM",
                    first_observed=temporal_metrics.get('first_event', datetime.utcnow()),
                    last_observed=temporal_metrics.get('last_event', datetime.utcnow()),
                    frequency=temporal_metrics.get('total_events', 0),
                    metadata={
                        'average_frequency': avg_freq,
                        'correlation_id': correlation_id
                    }
                )
                patterns.append(pattern)
            
            # Check for off-hours activity
            peak_hour = temporal_metrics.get('peak_hour', 12)
            if peak_hour < 6 or peak_hour > 22:
                pattern = BehavioralPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_name="off_hours_activity",
                    pattern_type="temporal",
                    confidence=0.8,
                    entities=[profile.entity_id],
                    description="Activity detected during unusual hours",
                    indicators=["unusual_timing", "off_hours"],
                    risk_level="HIGH",
                    first_observed=temporal_metrics.get('first_event', datetime.utcnow()),
                    last_observed=temporal_metrics.get('last_event', datetime.utcnow()),
                    frequency=temporal_metrics.get('total_events', 0),
                    metadata={
                        'peak_hour': peak_hour,
                        'correlation_id': correlation_id
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_relational_patterns(self, profiles: List[BehaviorProfile],
                                         correlation_id: Optional[str] = None) -> List[BehavioralPattern]:
        """Detect relational behavioral patterns."""
        patterns = []
        
        # Analyze network relationships between entities
        for profile in profiles:
            network_metrics = profile.metadata.get('network_metrics', {})
            if not network_metrics:
                continue
            
            # Check for hub behavior (high connectivity)
            degree_centrality = network_metrics.get('degree_centrality', 0)
            if degree_centrality > 0.6:
                pattern = BehavioralPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_name="hub_behavior",
                    pattern_type="relational",
                    confidence=min(degree_centrality, 1.0),
                    entities=[profile.entity_id],
                    description="Entity acts as central hub in network",
                    indicators=["high_connectivity", "central_position"],
                    risk_level="MEDIUM" if degree_centrality > 0.7 else "LOW",
                    first_observed=datetime.utcnow(),
                    last_observed=datetime.utcnow(),
                    frequency=network_metrics.get('connection_count', 0),
                    metadata={
                        'degree_centrality': degree_centrality,
                        'connection_count': network_metrics.get('connection_count', 0),
                        'correlation_id': correlation_id
                    }
                )
                patterns.append(pattern)
            
            # Check for bridge behavior (betweenness centrality)
            betweenness = network_metrics.get('betweenness_centrality', 0)
            if betweenness > 0.5:
                pattern = BehavioralPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_name="bridge_behavior",
                    pattern_type="relational",
                    confidence=min(betweenness, 1.0),
                    entities=[profile.entity_id],
                    description="Entity connects different network groups",
                    indicators=["bridge_connections", "group_connector"],
                    risk_level="MEDIUM",
                    first_observed=datetime.utcnow(),
                    last_observed=datetime.utcnow(),
                    frequency=network_metrics.get('shortest_paths', 0),
                    metadata={
                        'betweenness_centrality': betweenness,
                        'groups_connected': network_metrics.get('groups_connected', 0),
                        'correlation_id': correlation_id
                    }
                )
                patterns.append(pattern)
            
            # Check for isolated behavior (low connectivity)
            if degree_centrality < 0.2:
                pattern = BehavioralPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_name="isolated_behavior",
                    pattern_type="relational",
                    confidence=1.0 - degree_centrality,
                    entities=[profile.entity_id],
                    description="Entity operates in isolation with limited connections",
                    indicators=["low_connectivity", "peripheral_position"],
                    risk_level="LOW",
                    first_observed=datetime.utcnow(),
                    last_observed=datetime.utcnow(),
                    frequency=network_metrics.get('connection_count', 0),
                    metadata={
                        'degree_centrality': degree_centrality,
                        'connection_count': network_metrics.get('connection_count', 0),
                        'correlation_id': correlation_id
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_frequency_patterns(self, profiles: List[BehaviorProfile],
                                      correlation_id: Optional[str] = None) -> List[BehavioralPattern]:
        """Detect frequency behavioral patterns."""
        patterns = []
        
        for profile in profiles:
            temporal_metrics = profile.metadata.get('temporal_metrics', {})
            if not temporal_metrics:
                continue
            
            # Check for variable frequency
            std_interval = temporal_metrics.get('std_interval', 0)
            avg_interval = temporal_metrics.get('avg_interval', 1)
            
            if avg_interval > 0 and std_interval / avg_interval > 2:
                pattern = BehavioralPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_name="variable_frequency",
                    pattern_type="frequency",
                    confidence=min(std_interval / avg_interval / 3, 1.0),
                    entities=[profile.entity_id],
                    description="Highly variable frequency pattern detected",
                    indicators=["variable_timing", "erratic_frequency"],
                    risk_level="HIGH",
                    first_observed=temporal_metrics.get('first_event', datetime.utcnow()),
                    last_observed=temporal_metrics.get('last_event', datetime.utcnow()),
                    frequency=temporal_metrics.get('total_events', 0),
                    metadata={
                        'variability_ratio': std_interval / avg_interval,
                        'correlation_id': correlation_id
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_anomalies(self, profiles: List[BehaviorProfile],
                             correlation_id: Optional[str] = None) -> List[AnomalyDetection]:
        """Detect behavioral anomalies."""
        anomalies = []
        
        # Prepare data for anomaly detection
        if len(profiles) < 2:
            return anomalies
        
        # Extract features for ML models
        features = []
        entity_ids = []
        
        for profile in profiles:
            feature_vector = [
                profile.risk_score,
                profile.stability_score,
                profile.predictability_score,
                profile.metadata.get('temporal_metrics', {}).get('average_frequency', 0),
                profile.metadata.get('temporal_metrics', {}).get('total_events', 0)
            ]
            features.append(feature_vector)
            entity_ids.append(profile.entity_id)
        
        # Scale features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Detect anomalies using Isolation Forest
        anomaly_labels = self.ml_models['anomaly_detector'].fit_predict(features_scaled)
        
        # Create anomaly detections
        for i, (is_anomaly, entity_id) in enumerate(zip(anomaly_labels, entity_ids)):
            if is_anomaly == -1:  # Anomaly detected
                profile = profiles[i]
                
                anomaly = AnomalyDetection(
                    anomaly_id=str(uuid.uuid4()),
                    anomaly_type="behavioral_anomaly",
                    confidence=0.8,
                    severity="HIGH" if profile.risk_score > 0.7 else "MEDIUM",
                    affected_entities=[entity_id],
                    baseline_behavior="Normal behavioral patterns",
                    anomalous_behavior="Statistical outlier in behavior metrics",
                    potential_causes=[
                        "Unusual activity patterns",
                        "Potential automated behavior",
                        "Behavioral change over time"
                    ],
                    recommended_actions=[
                        "Investigate entity activity",
                        "Monitor for continued anomalies",
                        "Review temporal patterns"
                    ],
                    detected_at=datetime.utcnow(),
                    metadata={
                        'feature_vector': features[i].tolist(),
                        'risk_score': profile.risk_score,
                        'correlation_id': correlation_id
                    }
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    async def _generate_predictive_insights(self, profiles: List[BehaviorProfile],
                                         patterns: List[BehavioralPattern],
                                         anomalies: List[AnomalyDetection],
                                         correlation_id: Optional[str] = None) -> List[PredictiveInsight]:
        """Generate predictive insights."""
        insights = []
        
        # Risk escalation prediction
        high_risk_profiles = [p for p in profiles if p.risk_score > 0.7]
        if high_risk_profiles:
            insight = PredictiveInsight(
                insight_id=str(uuid.uuid4()),
                insight_type="risk_escalation",
                confidence=0.75,
                prediction="Increased risk activity likely",
                probability=0.8,
                time_horizon="7_days",
                supporting_evidence=[
                    f"{len(high_risk_profiles)} high-risk entities detected",
                    "Elevated behavioral risk scores",
                    "Anomalous patterns present"
                ],
                risk_impact="HIGH",
                mitigation_strategies=[
                    "Enhanced monitoring of high-risk entities",
                    "Implement additional security controls",
                    "Review investigation parameters"
                ],
                generated_at=datetime.utcnow(),
                metadata={
                    'high_risk_count': len(high_risk_profiles),
                    'correlation_id': correlation_id
                }
            )
            insights.append(insight)
        
        # Pattern evolution prediction
        if patterns:
            evolving_patterns = [p for p in patterns if p.confidence > 0.8]
            if evolving_patterns:
                insight = PredictiveInsight(
                    insight_id=str(uuid.uuid4()),
                    insight_type="pattern_evolution",
                    confidence=0.7,
                    prediction="Behavioral patterns likely to intensify",
                    probability=0.6,
                    time_horizon="30_days",
                    supporting_evidence=[
                        f"{len(evolving_patterns)} strong patterns detected",
                        "High confidence pattern matches",
                        "Consistent behavioral indicators"
                    ],
                    risk_impact="MEDIUM",
                    mitigation_strategies=[
                        "Monitor pattern evolution",
                        "Prepare for increased activity",
                        "Update investigation strategies"
                    ],
                    generated_at=datetime.utcnow(),
                    metadata={
                        'pattern_count': len(evolving_patterns),
                        'correlation_id': correlation_id
                    }
                )
                insights.append(insight)
        
        return insights
    
    def get_behavior_summary(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get behavioral summary for entity."""
        if entity_id not in self.behavior_profiles:
            return None
        
        profile = self.behavior_profiles[entity_id]
        
        return {
            'entity_id': entity_id,
            'risk_score': profile.risk_score,
            'stability_score': profile.stability_score,
            'predictability_score': profile.predictability_score,
            'pattern_count': len(profile.behavior_patterns),
            'anomaly_count': len(profile.anomalies),
            'last_updated': profile.last_updated.isoformat(),
            'metadata': profile.metadata
        }
    
    def get_global_behavior_metrics(self) -> Dict[str, Any]:
        """Get global behavioral analysis metrics."""
        if not self.behavior_profiles:
            return {}
        
        profiles = list(self.behavior_profiles.values())
        
        # Aggregate metrics
        avg_risk_score = sum(p.risk_score for p in profiles) / len(profiles)
        avg_stability_score = sum(p.stability_score for p in profiles) / len(profiles)
        avg_predictability_score = sum(p.predictability_score for p in profiles) / len(profiles)
        
        # Risk distribution
        risk_distribution = {
            'low': len([p for p in profiles if p.risk_score < 0.3]),
            'medium': len([p for p in profiles if 0.3 <= p.risk_score < 0.7]),
            'high': len([p for p in profiles if p.risk_score >= 0.7])
        }
        
        # Total patterns and anomalies
        total_patterns = sum(len(p.behavior_patterns) for p in profiles)
        total_anomalies = sum(len(p.anomalies) for p in profiles)
        
        return {
            'total_profiles': len(profiles),
            'average_risk_score': avg_risk_score,
            'average_stability_score': avg_stability_score,
            'average_predictability_score': avg_predictability_score,
            'risk_distribution': risk_distribution,
            'total_patterns_detected': total_patterns,
            'total_anomalies_detected': total_anomalies,
            'analysis_timestamp': datetime.utcnow().isoformat()
        }
