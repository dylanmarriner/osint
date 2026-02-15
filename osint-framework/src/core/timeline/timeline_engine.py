"""
Timeline Engine for OSINT Framework

Comprehensive timeline construction and analysis:
- Event extraction from multiple sources
- Chronological sequencing
- Lifespan reconstruction
- Activity pattern analysis
- Milestone detection
- Temporal confidence scoring
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set
from uuid import uuid4
import re

import structlog

logger = structlog.get_logger(__name__)


class EventType(Enum):
    """Types of life events."""
    # Birth & Identity
    BIRTH = "birth"
    NAME_CHANGE = "name_change"
    
    # Education
    SCHOOL_ENROLLMENT = "school_enrollment"
    SCHOOL_GRADUATION = "school_graduation"
    UNIVERSITY_ENROLLMENT = "university_enrollment"
    UNIVERSITY_GRADUATION = "university_graduation"
    CERTIFICATION = "certification"
    
    # Professional
    JOB_START = "job_start"
    JOB_END = "job_end"
    PROMOTION = "promotion"
    COMPANY_FOUNDED = "company_founded"
    BUSINESS_EVENT = "business_event"
    
    # Financial
    ACCOUNT_CREATED = "account_created"
    INVESTMENT = "investment"
    DONATION = "donation"
    PURCHASE = "purchase"
    
    # Social
    RELATIONSHIP_START = "relationship_start"
    RELATIONSHIP_END = "relationship_end"
    MARRIAGE = "marriage"
    DIVORCE = "divorce"
    CHILD_BIRTH = "child_birth"
    
    # Location
    MOVE = "move"
    TRAVEL = "travel"
    RESIDENCE = "residence"
    
    # Digital
    ACCOUNT_REGISTRATION = "account_registration"
    POST = "post"
    PUBLICATION = "publication"
    COMMIT = "commit"
    MEDIA_UPLOAD = "media_upload"
    
    # Other
    ARREST = "arrest"
    CONVICTION = "conviction"
    LAWSUIT = "lawsuit"
    AWARD = "award"
    EVENT_APPEARANCE = "event_appearance"
    MEDIA_MENTION = "media_mention"


class DatePrecision(Enum):
    """Precision level of a date."""
    EXACT_TIME = "exact_time"  # YYYY-MM-DD HH:MM:SS
    EXACT_DATE = "exact_date"  # YYYY-MM-DD
    MONTH = "month"  # YYYY-MM
    YEAR = "year"  # YYYY
    APPROX_YEAR = "approx_year"  # ~YYYY
    UNKNOWN = "unknown"


@dataclass
class TimelineEvent:
    """An event in a person's timeline."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: EventType = EventType.POST
    subject_id: str = ""  # Person/entity this event is about
    title: str = ""
    description: str = ""
    
    # Date information
    date: Optional[datetime] = None
    date_precision: DatePrecision = DatePrecision.EXACT_DATE
    
    # Event details
    location: Optional[str] = None
    related_entities: List[str] = field(default_factory=list)  # Other entities involved
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Evidence
    confidence: float = 0.5  # 0-1
    sources: List[str] = field(default_factory=list)  # Source names that reported this
    urls: List[str] = field(default_factory=list)  # Source URLs
    
    # Temporal properties
    created_at: datetime = field(default_factory=datetime.utcnow)
    verified: bool = False
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'subject_id': self.subject_id,
            'title': self.title,
            'description': self.description,
            'date': self.date.isoformat() if self.date else None,
            'date_precision': self.date_precision.value,
            'location': self.location,
            'related_entities': self.related_entities,
            'metadata': self.metadata,
            'confidence': self.confidence,
            'sources': self.sources,
            'urls': self.urls,
            'verified': self.verified,
            'notes': self.notes
        }


@dataclass
class LifespanMilestone:
    """Major milestone in a person's life."""
    milestone_id: str = field(default_factory=lambda: str(uuid4()))
    subject_id: str = ""
    milestone_type: str = ""  # birth, graduation, first_job, etc.
    
    date: Optional[datetime] = None
    estimated_date: Optional[datetime] = None  # If exact date is unknown
    confidence: float = 0.5
    
    title: str = ""
    description: str = ""
    supporting_events: List[str] = field(default_factory=list)  # Event IDs
    
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            'milestone_id': self.milestone_id,
            'subject_id': self.subject_id,
            'milestone_type': self.milestone_type,
            'date': self.date.isoformat() if self.date else None,
            'estimated_date': self.estimated_date.isoformat() if self.estimated_date else None,
            'confidence': self.confidence,
            'title': self.title,
            'description': self.description,
            'supporting_events': self.supporting_events
        }


class TimelineEngine:
    """Construct and analyze timelines from discovered data."""

    def __init__(self):
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        self.events: Dict[str, TimelineEvent] = {}
        self.milestones: Dict[str, LifespanMilestone] = {}

    # ==================== Event Management ====================

    def add_event(
        self,
        event_type: EventType,
        subject_id: str,
        title: str,
        date: Optional[datetime] = None,
        date_precision: DatePrecision = DatePrecision.EXACT_DATE,
        location: Optional[str] = None,
        confidence: float = 0.5,
        sources: Optional[List[str]] = None,
        urls: Optional[List[str]] = None,
        description: str = "",
        metadata: Optional[Dict] = None,
        related_entities: Optional[List[str]] = None
    ) -> TimelineEvent:
        """Add an event to the timeline."""
        event = TimelineEvent(
            event_type=event_type,
            subject_id=subject_id,
            title=title,
            date=date,
            date_precision=date_precision,
            location=location,
            confidence=confidence,
            sources=sources or [],
            urls=urls or [],
            description=description,
            metadata=metadata or {},
            related_entities=related_entities or []
        )

        self.events[event.event_id] = event
        self.logger.debug("Event added", event_id=event.event_id, event_type=event_type.value)
        return event

    def get_event(self, event_id: str) -> Optional[TimelineEvent]:
        """Retrieve an event."""
        return self.events.get(event_id)

    def get_events_for_subject(
        self,
        subject_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: Optional[Set[EventType]] = None
    ) -> List[TimelineEvent]:
        """Get events for a subject, optionally filtered."""
        events = [
            e for e in self.events.values()
            if e.subject_id == subject_id
        ]

        if start_date:
            events = [e for e in events if e.date and e.date >= start_date]

        if end_date:
            events = [e for e in events if e.date and e.date <= end_date]

        if event_types:
            events = [e for e in events if e.event_type in event_types]

        # Sort by date
        events.sort(key=lambda e: e.date or datetime.max)
        return events

    def merge_duplicate_events(self, event1_id: str, event2_id: str) -> Optional[TimelineEvent]:
        """Merge two duplicate events."""
        e1 = self.events.get(event1_id)
        e2 = self.events.get(event2_id)

        if not e1 or not e2:
            return None

        # Keep event with higher confidence
        if e1.confidence >= e2.confidence:
            e1.sources.extend(e2.sources)
            e1.urls.extend(e2.urls)
            e1.confidence = min(1.0, e1.confidence + 0.1)  # Slight boost
            del self.events[event2_id]
            return e1
        else:
            e2.sources.extend(e1.sources)
            e2.urls.extend(e1.urls)
            e2.confidence = min(1.0, e2.confidence + 0.1)
            del self.events[event1_id]
            return e2

    # ==================== Date Extraction & Parsing ====================

    def extract_dates_from_text(self, text: str) -> List[Tuple[str, DatePrecision]]:
        """
        Extract dates from text using regex patterns.
        Returns list of (date_string, precision).
        """
        dates = []

        # Exact date: YYYY-MM-DD or DD-MM-YYYY or MM/DD/YYYY
        pattern_exact = r'\b(?:\d{4}-\d{1,2}-\d{1,2}|(?:\d{1,2}[-/]){2}\d{4})\b'
        for match in re.finditer(pattern_exact, text):
            dates.append((match.group(), DatePrecision.EXACT_DATE))

        # Month and year: MM/YYYY, YYYY-MM, or "January 2023"
        pattern_month = r'\b(?:\d{1,2}[/-]\d{4}|\d{4}-\d{1,2}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\b'
        for match in re.finditer(pattern_month, text, re.IGNORECASE):
            dates.append((match.group(), DatePrecision.MONTH))

        # Year only: YYYY
        pattern_year = r'\b(?:19|20)\d{2}\b'
        for match in re.finditer(pattern_year, text):
            dates.append((match.group(), DatePrecision.YEAR))

        # Remove duplicates
        return list(set(dates))

    def parse_date_string(self, date_str: str) -> Optional[Tuple[datetime, DatePrecision]]:
        """
        Parse various date string formats.
        Returns (datetime, precision) or None.
        """
        date_str = date_str.strip()

        # Try exact date formats
        for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return (dt, DatePrecision.EXACT_DATE)
            except ValueError:
                continue

        # Try month/year formats
        for fmt in ['%m/%Y', '%Y-%m', '%B %Y', '%b %Y']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return (dt, DatePrecision.MONTH)
            except ValueError:
                continue

        # Try year only
        try:
            year = int(date_str)
            if 1900 <= year <= datetime.now().year:
                dt = datetime(year, 1, 1)
                return (dt, DatePrecision.YEAR)
        except ValueError:
            pass

        return None

    def infer_date_from_context(
        self,
        event_type: EventType,
        biographical_data: Dict[str, Any]
    ) -> Optional[datetime]:
        """
        Infer event date from biographical data.
        E.g., graduation year from age and current date.
        """
        current_year = datetime.now().year

        # Birth year inference
        if event_type == EventType.BIRTH:
            if 'age' in biographical_data:
                return datetime(current_year - biographical_data['age'], 1, 1)
            if 'birth_year' in biographical_data:
                return datetime(biographical_data['birth_year'], 1, 1)

        # Education timeline
        if 'birth_year' in biographical_data:
            birth_year = biographical_data['birth_year']

            if event_type == EventType.SCHOOL_GRADUATION:
                # Typically 18 years old
                return datetime(birth_year + 18, 6, 1)

            if event_type == EventType.UNIVERSITY_GRADUATION:
                # Typically 22 years old
                return datetime(birth_year + 22, 6, 1)

        return None

    # ==================== Lifespan Analysis ====================

    def detect_milestones(self, subject_id: str) -> List[LifespanMilestone]:
        """Detect major life milestones from events."""
        events = self.get_events_for_subject(subject_id)
        milestones = []

        # Birth milestone
        birth_events = [e for e in events if e.event_type == EventType.BIRTH]
        if birth_events:
            best = max(birth_events, key=lambda e: e.confidence)
            milestone = LifespanMilestone(
                subject_id=subject_id,
                milestone_type="birth",
                date=best.date,
                confidence=best.confidence,
                title="Birth",
                description=best.description,
                supporting_events=[best.event_id]
            )
            self.milestones[milestone.milestone_id] = milestone
            milestones.append(milestone)

        # Education milestones
        graduation_events = [
            e for e in events
            if e.event_type in [EventType.SCHOOL_GRADUATION, EventType.UNIVERSITY_GRADUATION]
        ]
        if graduation_events:
            events_by_type = {}
            for e in graduation_events:
                if e.event_type not in events_by_type:
                    events_by_type[e.event_type] = []
                events_by_type[e.event_type].append(e)

            for event_type, event_list in events_by_type.items():
                best = max(event_list, key=lambda e: e.confidence)
                label = "University Graduation" if event_type == EventType.UNIVERSITY_GRADUATION else "School Graduation"
                milestone = LifespanMilestone(
                    subject_id=subject_id,
                    milestone_type=event_type.value,
                    date=best.date,
                    confidence=best.confidence,
                    title=label,
                    description=best.description,
                    supporting_events=[e.event_id for e in event_list]
                )
                self.milestones[milestone.milestone_id] = milestone
                milestones.append(milestone)

        # First job
        job_starts = [e for e in events if e.event_type == EventType.JOB_START]
        if job_starts:
            first_job = min(job_starts, key=lambda e: e.date or datetime.max)
            milestone = LifespanMilestone(
                subject_id=subject_id,
                milestone_type="first_job",
                date=first_job.date,
                confidence=first_job.confidence,
                title="First Employment",
                description=first_job.description,
                supporting_events=[first_job.event_id]
            )
            self.milestones[milestone.milestone_id] = milestone
            milestones.append(milestone)

        # Marriage/relationship
        relationships = [
            e for e in events
            if e.event_type in [EventType.MARRIAGE, EventType.RELATIONSHIP_START]
        ]
        if relationships:
            best = max(relationships, key=lambda e: e.confidence)
            milestone = LifespanMilestone(
                subject_id=subject_id,
                milestone_type="major_relationship",
                date=best.date,
                confidence=best.confidence,
                title="Major Relationship/Marriage",
                description=best.description,
                supporting_events=[best.event_id]
            )
            self.milestones[milestone.milestone_id] = milestone
            milestones.append(milestone)

        return milestones

    def estimate_age(self, subject_id: str, as_of_date: Optional[datetime] = None) -> Optional[int]:
        """Estimate age based on birth events."""
        if as_of_date is None:
            as_of_date = datetime.now()

        birth_events = self.get_events_for_subject(
            subject_id,
            event_types={EventType.BIRTH}
        )

        if not birth_events:
            return None

        best = max(birth_events, key=lambda e: e.confidence)
        if not best.date:
            return None

        return as_of_date.year - best.date.year

    def get_lifespan_summary(self, subject_id: str) -> Dict[str, Any]:
        """Get comprehensive lifespan summary."""
        events = self.get_events_for_subject(subject_id)
        milestones = self.detect_milestones(subject_id)

        if not events:
            return {}

        earliest = min((e for e in events if e.date), key=lambda e: e.date, default=None)
        latest = max((e for e in events if e.date), key=lambda e: e.date, default=None)

        # Count events by type
        event_counts = {}
        for e in events:
            event_counts[e.event_type.value] = event_counts.get(e.event_type.value, 0) + 1

        return {
            'subject_id': subject_id,
            'total_events': len(events),
            'earliest_event': earliest.date.isoformat() if earliest else None,
            'latest_event': latest.date.isoformat() if latest else None,
            'timespan_years': (latest.date.year - earliest.date.year) if (earliest and latest) else None,
            'major_milestones': [m.to_dict() for m in milestones],
            'event_counts_by_type': event_counts,
            'estimated_age': self.estimate_age(subject_id),
            'average_event_confidence': sum(e.confidence for e in events) / len(events) if events else 0
        }

    # ==================== Activity Analysis ====================

    def get_activity_timeline(
        self,
        subject_id: str,
        bucket: str = 'month'  # 'day', 'week', 'month', 'year'
    ) -> Dict[str, int]:
        """
        Get activity counts bucketed by time period.
        Returns dict of {time_bucket: event_count}.
        """
        events = self.get_events_for_subject(subject_id)
        activity = {}

        for event in events:
            if not event.date:
                continue

            if bucket == 'day':
                key = event.date.date().isoformat()
            elif bucket == 'week':
                key = event.date.strftime('%Y-W%U')
            elif bucket == 'month':
                key = event.date.strftime('%Y-%m')
            elif bucket == 'year':
                key = str(event.date.year)
            else:
                continue

            activity[key] = activity.get(key, 0) + 1

        return dict(sorted(activity.items()))

    def get_most_active_periods(self, subject_id: str, top_n: int = 5) -> List[Tuple[str, int]]:
        """Get most active time periods."""
        activity = self.get_activity_timeline(subject_id, bucket='month')
        sorted_periods = sorted(activity.items(), key=lambda x: x[1], reverse=True)
        return sorted_periods[:top_n]

    # ==================== Export ====================

    def to_dict(self, subject_id: str) -> Dict[str, Any]:
        """Export timeline for a subject."""
        events = self.get_events_for_subject(subject_id)
        return {
            'subject_id': subject_id,
            'events': [e.to_dict() for e in events],
            'summary': self.get_lifespan_summary(subject_id)
        }
