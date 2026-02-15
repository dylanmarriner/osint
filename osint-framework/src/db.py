"""
Database models and session management for OSINT Framework.

Provides SQLAlchemy ORM models and database session management.
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

from sqlalchemy import create_engine, Column, String, DateTime, JSON, Float, Text, Integer, Enum, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool

from src.config import get_config

logger = logging.getLogger(__name__)

config = get_config()

# Create database engine
if config.DATABASE_URL.startswith("sqlite"):
    # Use StaticPool for SQLite to avoid threading issues
    engine = create_engine(
        config.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=config.DATABASE_ECHO
    )
else:
    engine = create_engine(
        config.DATABASE_URL,
        echo=config.DATABASE_ECHO,
        pool_pre_ping=True,
        pool_recycle=3600
    )

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()


class Investigation(Base):
    """Investigation record."""
    __tablename__ = "investigations"
    
    investigation_id = Column(String(36), primary_key=True, index=True)
    correlation_id = Column(String(36), unique=True, index=True)
    status = Column(String(20), index=True)  # pending, running, completed, failed
    subject_identifiers = Column(JSON)
    investigation_constraints = Column(JSON, nullable=True)
    confidence_thresholds = Column(JSON, nullable=True)
    progress_percentage = Column(Float, default=0.0)
    current_stage = Column(String(100), default="pending")
    entities_found = Column(Integer, default=0)
    queries_executed = Column(Integer, default=0)
    errors = Column(JSON, default=list)
    started_at = Column(DateTime, default=datetime.utcnow)
    estimated_completion = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reports = relationship("InvestigationReport", back_populates="investigation", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "investigation_id": self.investigation_id,
            "correlation_id": self.correlation_id,
            "status": self.status,
            "progress_percentage": self.progress_percentage,
            "current_stage": self.current_stage,
            "entities_found": self.entities_found,
            "queries_executed": self.queries_executed,
            "errors": self.errors or [],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
        }


class InvestigationReport(Base):
    """Investigation report record."""
    __tablename__ = "investigation_reports"
    
    report_id = Column(String(36), primary_key=True, index=True)
    investigation_id = Column(String(36), ForeignKey("investigations.investigation_id"), index=True)
    executive_summary = Column(Text)
    identity_inventory = Column(JSON)
    exposure_analysis = Column(JSON)
    activity_timeline = Column(JSON)
    remediation_recommendations = Column(JSON)
    detailed_findings = Column(JSON)
    confidence_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    investigation = relationship("Investigation", back_populates="reports")
    
    __table_args__ = (
        Index('idx_investigation_id_created', 'investigation_id', 'created_at'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "investigation_id": self.investigation_id,
            "executive_summary": self.executive_summary,
            "identity_inventory": self.identity_inventory or {},
            "exposure_analysis": self.exposure_analysis or {},
            "activity_timeline": self.activity_timeline or [],
            "remediation_recommendations": self.remediation_recommendations or [],
            "detailed_findings": self.detailed_findings or [],
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SearchQueryCache(Base):
    """Cache for search queries."""
    __tablename__ = "search_query_cache"
    
    query_hash = Column(String(64), primary_key=True, index=True)
    query_type = Column(String(50))
    query_string = Column(String(1000))
    results = Column(JSON)
    source_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_source_created', 'source_name', 'created_at'),
    )


class EntityCache(Base):
    """Cache for normalized entities."""
    __tablename__ = "entity_cache"
    
    entity_hash = Column(String(64), primary_key=True, index=True)
    entity_type = Column(String(50), index=True)
    entity_value = Column(String(500))
    normalized_entity = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)


def get_db() -> Session:
    """Get database session."""
    return SessionLocal()


def init_db():
    """Initialize database tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_investigation(investigation_id: str, db: Session = None) -> Optional[Investigation]:
    """Get investigation by ID."""
    if db is None:
        db = get_db()
    
    try:
        return db.query(Investigation).filter(
            Investigation.investigation_id == investigation_id
        ).first()
    finally:
        if db:
            db.close()


def save_investigation(investigation: Investigation, db: Session = None) -> Investigation:
    """Save investigation to database."""
    close_session = False
    if db is None:
        db = get_db()
        close_session = True
    
    try:
        db.add(investigation)
        db.commit()
        db.refresh(investigation)
        return investigation
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save investigation: {e}")
        raise
    finally:
        if close_session:
            db.close()


def save_investigation_report(report: InvestigationReport, db: Session = None) -> InvestigationReport:
    """Save investigation report to database."""
    close_session = False
    if db is None:
        db = get_db()
        close_session = True
    
    try:
        db.add(report)
        db.commit()
        db.refresh(report)
        return report
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save investigation report: {e}")
        raise
    finally:
        if close_session:
            db.close()


def get_investigation_report(investigation_id: str, db: Session = None) -> Optional[InvestigationReport]:
    """Get latest report for investigation."""
    close_session = False
    if db is None:
        db = get_db()
        close_session = True
    
    try:
        return db.query(InvestigationReport).filter(
            InvestigationReport.investigation_id == investigation_id
        ).order_by(InvestigationReport.created_at.desc()).first()
    finally:
        if close_session:
            db.close()


def list_investigations(limit: int = 50, offset: int = 0, db: Session = None) -> List[Investigation]:
    """List investigations."""
    close_session = False
    if db is None:
        db = get_db()
        close_session = True
    
    try:
        return db.query(Investigation).order_by(
            Investigation.created_at.desc()
        ).offset(offset).limit(limit).all()
    finally:
        if close_session:
            db.close()


def delete_investigation(investigation_id: str, db: Session = None) -> bool:
    """Delete investigation and its reports."""
    close_session = False
    if db is None:
        db = get_db()
        close_session = True
    
    try:
        investigation = db.query(Investigation).filter(
            Investigation.investigation_id == investigation_id
        ).first()
        
        if investigation:
            db.delete(investigation)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete investigation: {e}")
        raise
    finally:
        if close_session:
            db.close()
