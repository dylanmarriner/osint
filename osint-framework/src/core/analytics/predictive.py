"""
Predictive Analytics Engine for OSINT Framework

Purpose:
- Predict likely future locations based on historical patterns
- Project career paths and likely next roles
- Estimate income/financial status
- Predict relationship formation and network expansion
- Forecast trends and emerging patterns

Features:
- Location prediction using geographic clustering
- Career path projection using professional history
- Income estimation from profile data
- Network growth forecasting
- Relationship formation probability analysis
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid
import numpy as np
from collections import Counter, defaultdict
import structlog

from ..models.entities import Entity, EntityType


@dataclass
class LocationPrediction:
    """Predicted location for a person."""
    prediction_id: str
    location: str
    latitude: float
    longitude: float
    confidence: float
    reasoning: List[str]
    time_frame: str
    supporting_evidence: List[str]


@dataclass
class CareerPrediction:
    """Predicted career path for a person."""
    prediction_id: str
    current_role: str
    industry: str
    predicted_next_roles: List[str]
    predicted_timeline: str
    confidence: float
    reasoning: List[str]
    skill_gaps: List[str]
    growth_trajectory: str


@dataclass
class IncomePrediction:
    """Estimated income for a person."""
    estimate_id: str
    estimated_annual_income: float
    income_range: Tuple[float, float]
    confidence: float
    factors: Dict[str, float]
    employment_status: str
    location_factor: float
    industry_factor: float


@dataclass
class NetworkGrowthForecast:
    """Forecasted network growth."""
    forecast_id: str
    current_network_size: int
    projected_network_size_3m: int
    projected_network_size_6m: int
    projected_network_size_12m: int
    growth_rate: float
    confidence: float
    influential_factors: List[str]


class PredictiveAnalytics:
    """Predictive analytics engine for OSINT investigations."""

    def __init__(self):
        """Initialize predictive analytics engine."""
        self.logger = structlog.get_logger(__name__)
        self.location_cluster_radius_km = 100  # Clustering radius for locations

    async def predict_location(
        self,
        person_entity: Entity,
        historical_locations: List[Dict[str, Any]],
        timeline_events: List[Dict[str, Any]]
    ) -> LocationPrediction:
        """
        Predict likely current/future location for a person.
        
        Considers:
        - Historical location patterns
        - Employment location
        - Family/social network locations
        - Recent activity patterns
        - Seasonal patterns
        
        Args:
            person_entity: The person entity
            historical_locations: List of historical locations with dates
            timeline_events: Timeline of events with location data
            
        Returns:
            LocationPrediction with confidence and reasoning
        """
        try:
            self.logger.info("Starting location prediction", person=person_entity.entity_id)
            
            # Extract unique locations with frequency
            location_frequency = defaultdict(int)
            location_coordinates = {}
            
            for loc in historical_locations:
                location_name = loc.get("location", "")
                if location_name:
                    location_frequency[location_name] += 1
                    if "latitude" in loc and "longitude" in loc:
                        location_coordinates[location_name] = (
                            loc["latitude"],
                            loc["longitude"]
                        )
            
            # Find most common historical location
            if location_frequency:
                most_common_location = max(location_frequency.items(), key=lambda x: x[1])[0]
            else:
                most_common_location = "Unknown"
            
            # Analyze recent activity patterns (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_locations = []
            
            for event in timeline_events:
                event_date = event.get("date")
                if isinstance(event_date, str):
                    try:
                        event_date = datetime.fromisoformat(event_date)
                    except:
                        continue
                
                if event_date and event_date > thirty_days_ago:
                    if "location" in event:
                        recent_locations.append(event["location"])
            
            # Determine prediction based on patterns
            if recent_locations:
                # Use most recent location pattern
                predicted_location = Counter(recent_locations).most_common(1)[0][0]
                confidence = 0.75
                reasoning = [
                    "Recent activity shows concentration in this location",
                    f"Last {len(recent_locations)} events in this area"
                ]
            else:
                # Fall back to historical pattern
                predicted_location = most_common_location
                confidence = 0.60
                reasoning = ["Historical pattern analysis"]
            
            # Get coordinates if available
            coords = location_coordinates.get(predicted_location, (0.0, 0.0))
            
            prediction = LocationPrediction(
                prediction_id=str(uuid.uuid4()),
                location=predicted_location,
                latitude=coords[0] if coords else 0.0,
                longitude=coords[1] if coords else 0.0,
                confidence=confidence,
                reasoning=reasoning,
                time_frame="Current (within 30 days)",
                supporting_evidence=[
                    f"Historical frequency: {location_frequency.get(predicted_location, 0)} mentions",
                    f"Recent activity: {len(recent_locations)} events in timeframe"
                ]
            )
            
            self.logger.info(
                "Location prediction completed",
                person=person_entity.entity_id,
                location=predicted_location,
                confidence=confidence
            )
            
            return prediction
            
        except Exception as e:
            self.logger.error("Location prediction failed", error=str(e))
            # Return default prediction
            return LocationPrediction(
                prediction_id=str(uuid.uuid4()),
                location="Unknown",
                latitude=0.0,
                longitude=0.0,
                confidence=0.0,
                reasoning=[f"Error: {str(e)}"],
                time_frame="Unknown",
                supporting_evidence=[]
            )

    async def predict_career_path(
        self,
        person_entity: Entity,
        employment_history: List[Dict[str, Any]],
        education: List[Dict[str, Any]],
        skills: List[str]
    ) -> CareerPrediction:
        """
        Predict likely career path for a person.
        
        Considers:
        - Employment history and progression
        - Industry experience
        - Skill development
        - Education background
        - Career trends
        
        Args:
            person_entity: The person entity
            employment_history: List of past employment
            education: Education history
            skills: List of skills
            
        Returns:
            CareerPrediction with next likely roles and timeline
        """
        try:
            self.logger.info("Starting career path prediction", person=person_entity.entity_id)
            
            # Extract industries and roles from history
            industries = []
            roles = []
            time_in_roles = []
            
            for job in employment_history:
                if "industry" in job:
                    industries.append(job["industry"])
                if "title" in job:
                    roles.append(job["title"])
                if "duration_months" in job:
                    time_in_roles.append(job["duration_months"])
            
            # Identify primary industry and current role
            primary_industry = Counter(industries).most_common(1)[0][0] if industries else "Unknown"
            current_role = roles[-1] if roles else "Unknown"
            
            # Calculate average job tenure
            avg_tenure_months = int(np.mean(time_in_roles)) if time_in_roles else 24
            
            # Predict next roles based on progression
            predicted_next_roles = self._predict_next_roles(
                current_role,
                primary_industry,
                skills
            )
            
            # Estimate timeline (typically 2-3 years in each role)
            timeline_months = int(avg_tenure_months * 1.2)  # 20% longer than average tenure
            
            confidence = 0.65 if len(employment_history) > 3 else 0.45
            
            prediction = CareerPrediction(
                prediction_id=str(uuid.uuid4()),
                current_role=current_role,
                industry=primary_industry,
                predicted_next_roles=predicted_next_roles[:3],
                predicted_timeline=f"{timeline_months} months",
                confidence=confidence,
                reasoning=[
                    f"Employment pattern: {len(employment_history)} previous roles",
                    f"Average tenure per role: {avg_tenure_months} months",
                    f"Skill trajectory suggests progression within {primary_industry}"
                ],
                skill_gaps=self._identify_skill_gaps(skills, predicted_next_roles[0] if predicted_next_roles else ""),
                growth_trajectory="Upward" if len(roles) > 0 else "Unclear"
            )
            
            self.logger.info(
                "Career prediction completed",
                person=person_entity.entity_id,
                predicted_role=predicted_next_roles[0] if predicted_next_roles else "Unknown"
            )
            
            return prediction
            
        except Exception as e:
            self.logger.error("Career prediction failed", error=str(e))
            return CareerPrediction(
                prediction_id=str(uuid.uuid4()),
                current_role="Unknown",
                industry="Unknown",
                predicted_next_roles=[],
                predicted_timeline="Unknown",
                confidence=0.0,
                reasoning=[f"Error: {str(e)}"],
                skill_gaps=[],
                growth_trajectory="Unknown"
            )

    async def estimate_income(
        self,
        person_entity: Entity,
        employment_history: List[Dict[str, Any]],
        education: List[Dict[str, Any]],
        location: str,
        industry: str
    ) -> IncomePrediction:
        """
        Estimate annual income based on profile data.
        
        Considers:
        - Job title and seniority
        - Industry standards
        - Geographic location
        - Education level
        - Company size/prestige
        
        Args:
            person_entity: The person entity
            employment_history: Employment history
            education: Education history
            location: Primary location
            industry: Primary industry
            
        Returns:
            IncomePrediction with estimated income range
        """
        try:
            self.logger.info("Starting income estimation", person=person_entity.entity_id)
            
            # Base income factors
            industry_multipliers = {
                "Technology": 1.4,
                "Finance": 1.5,
                "Consulting": 1.3,
                "Healthcare": 1.1,
                "Manufacturing": 0.95,
                "Retail": 0.75,
            }
            
            location_multipliers = {
                "San Francisco": 1.3,
                "New York": 1.25,
                "Seattle": 1.2,
                "Boston": 1.15,
                "Chicago": 1.0,
                "Other": 0.85,
            }
            
            # Base salary by role
            role_base_salaries = {
                "CEO": 150000,
                "CTO": 120000,
                "VP": 100000,
                "Director": 80000,
                "Manager": 60000,
                "Senior Engineer": 120000,
                "Engineer": 85000,
                "Analyst": 65000,
                "Associate": 50000,
                "Intern": 30000,
            }
            
            # Extract current role
            if employment_history:
                current_role = employment_history[-1].get("title", "Unknown")
            else:
                current_role = "Unknown"
            
            # Find base salary for role
            base_salary = role_base_salaries.get(current_role, 65000)
            
            # Apply industry multiplier
            industry_mult = industry_multipliers.get(industry, 1.0)
            
            # Apply location multiplier
            location_mult = location_multipliers.get(location, location_multipliers.get("Other", 0.85))
            
            # Education factor
            education_factor = 1.0
            for edu in education:
                if "advanced" in str(edu).lower() or "master" in str(edu).lower():
                    education_factor = 1.15
                elif "phd" in str(edu).lower():
                    education_factor = 1.25
            
            # Calculate estimated income
            estimated_income = int(base_salary * industry_mult * location_mult * education_factor)
            
            # Calculate range (±20%)
            lower_bound = int(estimated_income * 0.8)
            upper_bound = int(estimated_income * 1.2)
            
            # Determine employment status
            if employment_history:
                employment_status = "Employed"
            else:
                employment_status = "Unknown"
            
            confidence = 0.55 if employment_history else 0.30
            
            prediction = IncomePrediction(
                estimate_id=str(uuid.uuid4()),
                estimated_annual_income=estimated_income,
                income_range=(lower_bound, upper_bound),
                confidence=confidence,
                factors={
                    "role": current_role,
                    "industry_multiplier": industry_mult,
                    "location_multiplier": location_mult,
                    "education_factor": education_factor,
                    "base_salary": base_salary
                },
                employment_status=employment_status,
                location_factor=location_mult,
                industry_factor=industry_mult
            )
            
            self.logger.info(
                "Income estimation completed",
                person=person_entity.entity_id,
                estimated_income=estimated_income
            )
            
            return prediction
            
        except Exception as e:
            self.logger.error("Income estimation failed", error=str(e))
            return IncomePrediction(
                estimate_id=str(uuid.uuid4()),
                estimated_annual_income=0,
                income_range=(0, 0),
                confidence=0.0,
                factors={},
                employment_status="Unknown",
                location_factor=1.0,
                industry_factor=1.0
            )

    async def forecast_network_growth(
        self,
        person_entity: Entity,
        current_network_size: int,
        historical_growth: List[Tuple[datetime, int]]
    ) -> NetworkGrowthForecast:
        """
        Forecast network growth over time.
        
        Considers:
        - Current network size
        - Historical growth rate
        - Activity level
        - Professional trajectory
        
        Args:
            person_entity: The person entity
            current_network_size: Current network size
            historical_growth: List of (date, network_size) tuples
            
        Returns:
            NetworkGrowthForecast with projections
        """
        try:
            self.logger.info(
                "Starting network growth forecast",
                person=person_entity.entity_id,
                current_size=current_network_size
            )
            
            # Calculate growth rate
            if len(historical_growth) > 1:
                growth_rates = []
                for i in range(1, len(historical_growth)):
                    prev_date, prev_size = historical_growth[i-1]
                    curr_date, curr_size = historical_growth[i]
                    
                    days_diff = (curr_date - prev_date).days
                    if days_diff > 0:
                        daily_growth = (curr_size - prev_size) / days_diff
                        growth_rates.append(daily_growth)
                
                avg_daily_growth = np.mean(growth_rates) if growth_rates else 0.5
            else:
                avg_daily_growth = 0.5  # Default: 0.5 connections per day
            
            # Project forward
            growth_3m = int(current_network_size + (avg_daily_growth * 90))
            growth_6m = int(current_network_size + (avg_daily_growth * 180))
            growth_12m = int(current_network_size + (avg_daily_growth * 365))
            
            # Sanity check - limit growth to reasonable bounds
            growth_3m = min(growth_3m, int(current_network_size * 1.5))
            growth_6m = min(growth_6m, int(current_network_size * 2.0))
            growth_12m = min(growth_12m, int(current_network_size * 2.5))
            
            growth_rate = (avg_daily_growth * 365) / current_network_size if current_network_size > 0 else 0.0
            
            prediction = NetworkGrowthForecast(
                forecast_id=str(uuid.uuid4()),
                current_network_size=current_network_size,
                projected_network_size_3m=growth_3m,
                projected_network_size_6m=growth_6m,
                projected_network_size_12m=growth_12m,
                growth_rate=min(growth_rate, 1.0),  # Cap at 100% annual growth
                confidence=0.60,
                influential_factors=[
                    f"Historical daily growth: {avg_daily_growth:.2f} connections/day",
                    "Professional activity level",
                    "Platform engagement patterns"
                ]
            )
            
            self.logger.info(
                "Network growth forecast completed",
                person=person_entity.entity_id,
                projected_12m=growth_12m
            )
            
            return prediction
            
        except Exception as e:
            self.logger.error("Network growth forecast failed", error=str(e))
            return NetworkGrowthForecast(
                forecast_id=str(uuid.uuid4()),
                current_network_size=current_network_size,
                projected_network_size_3m=current_network_size,
                projected_network_size_6m=current_network_size,
                projected_network_size_12m=current_network_size,
                growth_rate=0.0,
                confidence=0.0,
                influential_factors=[f"Error: {str(e)}"]
            )

    def _predict_next_roles(self, current_role: str, industry: str, skills: List[str]) -> List[str]:
        """Predict likely next roles for a person."""
        # Career progression patterns
        progression_paths = {
            "Engineer": ["Senior Engineer", "Tech Lead", "Engineering Manager"],
            "Senior Engineer": ["Tech Lead", "Engineering Manager", "Architect"],
            "Manager": ["Senior Manager", "Director", "VP"],
            "Analyst": ["Senior Analyst", "Manager", "Director"],
            "Consultant": ["Senior Consultant", "Manager", "Partner"],
            "Associate": ["Senior Associate", "Manager", "Director"],
        }
        
        # Find matching progression
        for role_pattern, next_roles in progression_paths.items():
            if role_pattern.lower() in current_role.lower():
                return next_roles
        
        # Default progression
        return ["Manager", "Director", "Senior Leadership"]

    def _identify_skill_gaps(self, current_skills: List[str], target_role: str) -> List[str]:
        """Identify skill gaps for target role."""
        target_skills = {
            "CEO": ["Strategy", "P&L Management", "Board Relations", "Executive Leadership"],
            "CTO": ["Technical Vision", "Architecture", "Team Leadership", "Innovation"],
            "Engineering Manager": ["People Management", "Mentoring", "Project Leadership"],
            "Director": ["Strategic Planning", "Budget Management", "Stakeholder Management"],
            "Senior Engineer": ["System Design", "Mentoring", "Technical Expertise"],
        }
        
        # Get required skills for target role
        required = set(target_skills.get(target_role, []))
        current = set(skill.lower() for skill in current_skills)
        
        # Find gaps
        gaps = list(required - current)
        return gaps[:3]  # Top 3 skill gaps
