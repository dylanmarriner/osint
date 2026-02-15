"""
Trend Analysis Engine for OSINT Framework

Purpose:
- Track sentiment and opinion evolution over time
- Monitor skill and technology trend adoption
- Calculate network growth rates and patterns
- Analyze content performance and engagement
- Extract topic evolution and shifting interests

Features:
- Sentiment tracking over time periods
- Skill popularity trending
- Network growth rate analysis
- Content engagement metrics
- Topic modeling and evolution
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import uuid
import numpy as np
import structlog

from ..models.entities import Entity, EntityType


@dataclass
class SentimentTrend:
    """Sentiment trend analysis result."""
    trend_id: str
    entity_id: str
    metric: str
    time_periods: List[Tuple[datetime, float]]
    overall_trend: str  # increasing, decreasing, stable
    current_value: float
    average_value: float
    volatility: float
    confidence: float
    analysis_date: datetime


@dataclass
class TopicEvolution:
    """Topic evolution analysis."""
    evolution_id: str
    entity_id: str
    topic: str
    introduction_date: datetime
    peak_interest_date: datetime
    current_interest: float
    engagement_trend: str
    associated_keywords: List[str]
    mentions_over_time: List[Tuple[datetime, int]]


@dataclass
class SkillTrend:
    """Skill adoption and trending analysis."""
    trend_id: str
    entity_id: str
    skill: str
    adoption_date: datetime
    proficiency_level: str
    trending_position: str  # emerging, growing, peak, declining
    adoption_rate: float
    related_skills: List[str]
    market_demand: float


@dataclass
class NetworkGrowthTrend:
    """Network growth trend analysis."""
    trend_id: str
    entity_id: str
    time_period: str
    network_size_snapshots: List[Tuple[datetime, int]]
    growth_rate_monthly: float
    growth_acceleration: float
    largest_growth_period: str
    seasonal_patterns: Dict[str, float]
    confidence: float


class TrendAnalyzer:
    """Trend analysis engine for OSINT investigations."""

    def __init__(self):
        """Initialize trend analyzer."""
        self.logger = structlog.get_logger(__name__)

    async def track_sentiment(
        self,
        entity_id: str,
        posts_over_time: List[Dict[str, Any]],
        lookback_days: int = 365
    ) -> SentimentTrend:
        """
        Track sentiment evolution over time.
        
        Analyzes:
        - Opinion changes on key topics
        - Emotional tone of communications
        - Positive/negative ratio trends
        - Major sentiment shifts
        
        Args:
            entity_id: The entity being analyzed
            posts_over_time: List of posts with dates and content
            lookback_days: Number of days to analyze
            
        Returns:
            SentimentTrend with temporal sentiment data
        """
        try:
            self.logger.info(
                "Starting sentiment trend analysis",
                entity=entity_id,
                posts=len(posts_over_time)
            )
            
            # Group posts by time period (monthly)
            sentiment_by_period = defaultdict(list)
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            for post in posts_over_time:
                post_date = post.get("date")
                if isinstance(post_date, str):
                    try:
                        post_date = datetime.fromisoformat(post_date)
                    except:
                        continue
                
                if post_date and post_date > cutoff_date:
                    # Get sentiment score (simplified)
                    sentiment_score = self._calculate_sentiment(post.get("content", ""))
                    
                    # Group by month
                    period_key = post_date.strftime("%Y-%m")
                    sentiment_by_period[period_key].append(sentiment_score)
            
            # Calculate monthly averages
            time_periods = []
            sentiment_scores = []
            
            for period in sorted(sentiment_by_period.keys()):
                scores = sentiment_by_period[period]
                avg_sentiment = np.mean(scores) if scores else 0.0
                period_date = datetime.strptime(period, "%Y-%m")
                time_periods.append((period_date, avg_sentiment))
                sentiment_scores.append(avg_sentiment)
            
            # Determine trend direction
            if len(sentiment_scores) > 2:
                recent_avg = np.mean(sentiment_scores[-3:])
                older_avg = np.mean(sentiment_scores[:3])
                
                if recent_avg > older_avg + 0.1:
                    overall_trend = "increasing"
                elif recent_avg < older_avg - 0.1:
                    overall_trend = "decreasing"
                else:
                    overall_trend = "stable"
            else:
                overall_trend = "insufficient_data"
            
            # Calculate statistics
            current_value = sentiment_scores[-1] if sentiment_scores else 0.0
            average_value = np.mean(sentiment_scores) if sentiment_scores else 0.0
            volatility = np.std(sentiment_scores) if len(sentiment_scores) > 1 else 0.0
            
            trend = SentimentTrend(
                trend_id=str(uuid.uuid4()),
                entity_id=entity_id,
                metric="sentiment_score",
                time_periods=time_periods,
                overall_trend=overall_trend,
                current_value=current_value,
                average_value=average_value,
                volatility=volatility,
                confidence=min(len(sentiment_scores) / 12.0, 1.0),  # Higher confidence with more months
                analysis_date=datetime.utcnow()
            )
            
            self.logger.info(
                "Sentiment trend analysis completed",
                entity=entity_id,
                trend=overall_trend,
                current_sentiment=current_value
            )
            
            return trend
            
        except Exception as e:
            self.logger.error("Sentiment analysis failed", error=str(e))
            return SentimentTrend(
                trend_id=str(uuid.uuid4()),
                entity_id=entity_id,
                metric="sentiment_score",
                time_periods=[],
                overall_trend="error",
                current_value=0.0,
                average_value=0.0,
                volatility=0.0,
                confidence=0.0,
                analysis_date=datetime.utcnow()
            )

    async def extract_topic_trends(
        self,
        entity_id: str,
        content_timeline: List[Dict[str, Any]],
        lookback_days: int = 365
    ) -> List[TopicEvolution]:
        """
        Extract topic evolution from content timeline.
        
        Identifies:
        - When topics were introduced
        - Peak interest periods
        - Topic fading patterns
        - Topic persistence
        
        Args:
            entity_id: The entity being analyzed
            content_timeline: List of content items with dates
            lookback_days: Number of days to analyze
            
        Returns:
            List of TopicEvolution for discovered topics
        """
        try:
            self.logger.info(
                "Starting topic trend extraction",
                entity=entity_id,
                items=len(content_timeline)
            )
            
            # Extract keywords/topics from content
            topic_mentions = defaultdict(lambda: defaultdict(int))
            topic_first_seen = {}
            topic_peak_date = {}
            
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            for item in content_timeline:
                item_date = item.get("date")
                if isinstance(item_date, str):
                    try:
                        item_date = datetime.fromisoformat(item_date)
                    except:
                        continue
                
                if item_date and item_date > cutoff_date:
                    content = item.get("content", "")
                    topics = self._extract_topics(content)
                    
                    period_key = item_date.strftime("%Y-%m")
                    
                    for topic in topics:
                        topic_mentions[topic][period_key] += 1
                        
                        if topic not in topic_first_seen:
                            topic_first_seen[topic] = item_date
            
            # Analyze each topic
            evolutions = []
            
            for topic, mentions_by_period in topic_mentions.items():
                if not mentions_by_period:
                    continue
                
                # Find peak period
                peak_period = max(mentions_by_period.items(), key=lambda x: x[1])[0]
                peak_date = datetime.strptime(peak_period, "%Y-%m")
                
                # Create mention timeline
                mentions_timeline = []
                for period in sorted(mentions_by_period.keys()):
                    period_date = datetime.strptime(period, "%Y-%m")
                    mentions_timeline.append((period_date, mentions_by_period[period]))
                
                # Determine engagement trend
                if len(mentions_timeline) > 1:
                    recent_mentions = sum(mentions_by_period[p] for p in sorted(mentions_by_period.keys())[-3:])
                    older_mentions = sum(mentions_by_period[p] for p in sorted(mentions_by_period.keys())[:3])
                    
                    if recent_mentions > older_mentions:
                        engagement_trend = "growing"
                    elif recent_mentions < older_mentions * 0.5:
                        engagement_trend = "declining"
                    else:
                        engagement_trend = "stable"
                else:
                    engagement_trend = "emerging"
                
                current_mentions = sum(mentions_by_period[p] for p in sorted(mentions_by_period.keys())[-1:])
                peak_mentions = max(mentions_by_period.values())
                current_interest = current_mentions / peak_mentions if peak_mentions > 0 else 0.0
                
                evolution = TopicEvolution(
                    evolution_id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    topic=topic,
                    introduction_date=topic_first_seen[topic],
                    peak_interest_date=peak_date,
                    current_interest=current_interest,
                    engagement_trend=engagement_trend,
                    associated_keywords=[topic],  # Could be expanded with related keywords
                    mentions_over_time=mentions_timeline
                )
                
                evolutions.append(evolution)
            
            # Sort by recency
            evolutions.sort(key=lambda x: x.peak_interest_date, reverse=True)
            
            self.logger.info(
                "Topic trend extraction completed",
                entity=entity_id,
                topics_found=len(evolutions)
            )
            
            return evolutions
            
        except Exception as e:
            self.logger.error("Topic extraction failed", error=str(e))
            return []

    async def calculate_network_growth_rate(
        self,
        entity_id: str,
        graph_snapshots: List[Tuple[datetime, int]]
    ) -> NetworkGrowthTrend:
        """
        Calculate network growth rate from historical snapshots.
        
        Measures:
        - Monthly growth rate
        - Growth acceleration/deceleration
        - Seasonal patterns
        - Largest growth periods
        
        Args:
            entity_id: The entity being analyzed
            graph_snapshots: List of (date, network_size) tuples
            
        Returns:
            NetworkGrowthTrend with growth metrics
        """
        try:
            self.logger.info(
                "Starting network growth rate calculation",
                entity=entity_id,
                snapshots=len(graph_snapshots)
            )
            
            if len(graph_snapshots) < 2:
                return NetworkGrowthTrend(
                    trend_id=str(uuid.uuid4()),
                    entity_id=entity_id,
                    time_period="insufficient_data",
                    network_size_snapshots=graph_snapshots,
                    growth_rate_monthly=0.0,
                    growth_acceleration=0.0,
                    largest_growth_period="unknown",
                    seasonal_patterns={},
                    confidence=0.0
                )
            
            # Sort snapshots by date
            sorted_snapshots = sorted(graph_snapshots, key=lambda x: x[0])
            
            # Calculate monthly growth rates
            monthly_growth_rates = []
            growth_periods = []
            
            for i in range(1, len(sorted_snapshots)):
                prev_date, prev_size = sorted_snapshots[i-1]
                curr_date, curr_size = sorted_snapshots[i]
                
                days_diff = (curr_date - prev_date).days
                if days_diff > 0:
                    growth = curr_size - prev_size
                    monthly_growth = (growth / prev_size * 100) if prev_size > 0 else 0.0
                    monthly_growth_rates.append(monthly_growth)
                    growth_periods.append((curr_date.strftime("%Y-%m"), growth))
            
            # Calculate average monthly growth rate
            avg_monthly_growth = np.mean(monthly_growth_rates) if monthly_growth_rates else 0.0
            
            # Calculate growth acceleration (trend of growth rates)
            if len(monthly_growth_rates) > 2:
                recent_growth = np.mean(monthly_growth_rates[-3:])
                older_growth = np.mean(monthly_growth_rates[:3])
                growth_acceleration = recent_growth - older_growth
            else:
                growth_acceleration = 0.0
            
            # Find largest growth period
            if growth_periods:
                largest_period = max(growth_periods, key=lambda x: x[1])
                largest_growth_period = largest_period[0]
            else:
                largest_growth_period = "unknown"
            
            # Analyze seasonal patterns
            seasonal_patterns = self._analyze_seasonal_patterns(growth_periods)
            
            trend = NetworkGrowthTrend(
                trend_id=str(uuid.uuid4()),
                entity_id=entity_id,
                time_period=f"{sorted_snapshots[0][0].strftime('%Y-%m')} to {sorted_snapshots[-1][0].strftime('%Y-%m')}",
                network_size_snapshots=sorted_snapshots,
                growth_rate_monthly=avg_monthly_growth,
                growth_acceleration=growth_acceleration,
                largest_growth_period=largest_growth_period,
                seasonal_patterns=seasonal_patterns,
                confidence=min(len(sorted_snapshots) / 12.0, 1.0)
            )
            
            self.logger.info(
                "Network growth rate calculation completed",
                entity=entity_id,
                monthly_growth=avg_monthly_growth,
                acceleration=growth_acceleration
            )
            
            return trend
            
        except Exception as e:
            self.logger.error("Network growth calculation failed", error=str(e))
            return NetworkGrowthTrend(
                trend_id=str(uuid.uuid4()),
                entity_id=entity_id,
                time_period="error",
                network_size_snapshots=graph_snapshots,
                growth_rate_monthly=0.0,
                growth_acceleration=0.0,
                largest_growth_period="unknown",
                seasonal_patterns={},
                confidence=0.0
            )

    def _calculate_sentiment(self, text: str) -> float:
        """
        Calculate sentiment score for text (simplified).
        Returns value between -1.0 (negative) and 1.0 (positive).
        """
        positive_words = [
            "great", "good", "excellent", "amazing", "wonderful", "happy",
            "love", "perfect", "awesome", "beautiful", "fantastic"
        ]
        negative_words = [
            "bad", "terrible", "awful", "horrible", "hate", "worst",
            "disappointing", "fail", "broken", "stupid", "ugly"
        ]
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        
        return (positive_count - negative_count) / total

    def _extract_topics(self, content: str) -> List[str]:
        """Extract topics from content (simplified)."""
        # Common tech topics
        tech_topics = ["AI", "ML", "blockchain", "cloud", "DevOps", "security"]
        business_topics = ["startup", "growth", "revenue", "fundraising", "IPO"]
        
        topics = []
        content_lower = content.lower()
        
        for topic in tech_topics + business_topics:
            if topic.lower() in content_lower:
                topics.append(topic)
        
        return topics

    def _analyze_seasonal_patterns(
        self,
        growth_periods: List[Tuple[str, int]]
    ) -> Dict[str, float]:
        """Analyze seasonal patterns in growth data."""
        seasonal = defaultdict(list)
        
        for period, growth in growth_periods:
            # Extract month
            try:
                month = int(period.split("-")[1])
                seasonal[f"month_{month}"].append(growth)
            except:
                pass
        
        # Calculate average growth per month
        pattern = {}
        for month_key, values in seasonal.items():
            if values:
                pattern[month_key] = np.mean(values)
        
        return pattern
