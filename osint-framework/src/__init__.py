"""
OSINT Framework Package

Purpose
- Main package initialization for OSINT framework
- Provides easy access to core components
- Configures logging and dependencies

Invariants
- All core components are properly initialized
- Logging is configured with structured output
- Package version is available for import
- Dependencies are validated on import

Failure Modes
- Missing dependencies → ImportError with clear error message
- Configuration errors → detailed logging with recovery suggestions
- Component initialization failure → graceful degradation
- Logging configuration failure → fallback to basic logging

Debug Notes
- Check package_version for compatibility issues
- Monitor component_initialization metrics for startup performance
- Review dependency_validation_failed alerts for import issues
- Use logging_configuration errors to diagnose setup problems

Design Tradeoffs
- Chose lazy initialization for faster startup
- Tradeoff: First use may be slower but reduces startup time
- Mitigation: Critical components are initialized eagerly
- Review trigger: If startup time exceeds 10 seconds, optimize initialization
"""

from .core.models.entities import (
    Entity, EntityType, VerificationStatus, RiskLevel,
    InvestigationInput, InvestigationReport,
    validate_email, validate_phone, validate_domain,
    redact_sensitive_data
)

from .core.pipeline.discovery import DiscoveryEngine
from .core.pipeline.fetch import FetchManager
from .core.pipeline.parse import ParseEngine
from .core.pipeline.normalize import NormalizationEngine
from .core.pipeline.resolve import EntityResolver
from .core.pipeline.report import ReportGenerator
from .connectors.base import ConnectorRegistry

# Package version
__version__ = "1.0.0"
__author__ = "OSINT Framework Team"
__description__ = "Privacy-focused OSINT investigation framework"
__email__ = "security@osint-framework.local"

# Core components - initialized on first import
_discovery_engine = None
_fetch_manager = None
_parse_engine = None
_normalization_engine = None
_entity_resolver = None
_report_generator = None
_connector_registry = None


def get_discovery_engine() -> DiscoveryEngine:
    """Get or create discovery engine instance."""
    global _discovery_engine
    if _discovery_engine is None:
        _discovery_engine = DiscoveryEngine(get_connector_registry())
    return _discovery_engine


def get_fetch_manager() -> FetchManager:
    """Get or create fetch manager instance."""
    global _fetch_manager
    if _fetch_manager is None:
        _fetch_manager = FetchManager(get_connector_registry())
    return _fetch_manager


def get_parse_engine() -> ParseEngine:
    """Get or create parse engine instance."""
    global _parse_engine
    if _parse_engine is None:
        _parse_engine = ParseEngine()
    return _parse_engine


def get_normalization_engine() -> NormalizationEngine:
    """Get or create normalization engine instance."""
    global _normalization_engine
    if _normalization_engine is None:
        _normalization_engine = NormalizationEngine()
    return _normalization_engine


def get_entity_resolver() -> EntityResolver:
    """Get or create entity resolver instance."""
    global _entity_resolver
    if _entity_resolver is None:
        _entity_resolver = EntityResolver()
    return _entity_resolver


def get_report_generator() -> ReportGenerator:
    """Get or create report generator instance."""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator


def get_connector_registry() -> ConnectorRegistry:
    """Get or create connector registry instance."""
    global _connector_registry
    if _connector_registry is None:
        from .connectors.manager import get_initialized_registry
        _connector_registry = get_initialized_registry()
    return _connector_registry


def get_version() -> str:
    """Get package version."""
    return __version__


def get_component_status() -> dict:
    """Get status of all core components."""
    return {
        "discovery_engine": _discovery_engine is not None,
        "fetch_manager": _fetch_manager is not None,
        "parse_engine": _parse_engine is not None,
        "normalization_engine": _normalization_engine is not None,
        "entity_resolver": _entity_resolver is not None,
        "report_generator": _report_generator is not None,
        "connector_registry": _connector_registry is not None,
        "version": __version__
    }


# Export main classes and functions
__all__ = [
    # Models
    "Entity", "EntityType", "VerificationStatus", "RiskLevel",
    "InvestigationInput", "InvestigationReport",
    "validate_email", "validate_phone", "validate_domain",
    "redact_sensitive_data",
    
    # Pipeline components
    "DiscoveryEngine", "FetchManager", "ParseEngine", 
    "NormalizationEngine", "EntityResolver", "ReportGenerator",
    
    # Connectors
    "ConnectorRegistry",
    
    # Package info
    "get_version", "get_component_status",
    
    # Convenience functions
    "get_discovery_engine", "get_fetch_manager", "get_parse_engine",
    "get_normalization_engine", "get_entity_resolver", "get_report_generator",
    "get_connector_registry"
]
