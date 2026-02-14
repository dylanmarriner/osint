"""
Basic unit tests for OSINT Framework

Tests:
- Component initialization
- Basic functionality of core components
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src import (
    get_connector_registry, 
    get_discovery_engine, 
    get_fetch_manager,
    get_parse_engine,
    get_normalization_engine,
    get_entity_resolver,
    get_report_generator
)


class TestComponentInitialization:
    """Test that all core components can be initialized."""
    
    def test_connector_registry_initialization(self):
        """Test ConnectorRegistry can be initialized."""
        registry = get_connector_registry()
        assert registry is not None
        print("✓ ConnectorRegistry initialized")
    
    def test_discovery_engine_initialization(self):
        """Test DiscoveryEngine can be initialized."""
        engine = get_discovery_engine()
        assert engine is not None
        print("✓ DiscoveryEngine initialized")
    
    def test_fetch_manager_initialization(self):
        """Test FetchManager can be initialized."""
        manager = get_fetch_manager()
        assert manager is not None
        print("✓ FetchManager initialized")
    
    def test_parse_engine_initialization(self):
        """Test ParseEngine can be initialized."""
        engine = get_parse_engine()
        assert engine is not None
        print("✓ ParseEngine initialized")
    
    def test_normalization_engine_initialization(self):
        """Test NormalizationEngine can be initialized."""
        engine = get_normalization_engine()
        assert engine is not None
        print("✓ NormalizationEngine initialized")
    
    def test_entity_resolver_initialization(self):
        """Test EntityResolver can be initialized."""
        resolver = get_entity_resolver()
        assert resolver is not None
        print("✓ EntityResolver initialized")
    
    def test_report_generator_initialization(self):
        """Test ReportGenerator can be initialized."""
        generator = get_report_generator()
        assert generator is not None
        print("✓ ReportGenerator initialized")
    
    def test_all_components_available(self):
        """Test all components can be retrieved."""
        components = [
            get_connector_registry(),
            get_discovery_engine(),
            get_fetch_manager(),
            get_parse_engine(),
            get_normalization_engine(),
            get_entity_resolver(),
            get_report_generator()
        ]
        assert all(c is not None for c in components)
        print(f"✓ All {len(components)} components initialized successfully")


class TestDiscoveryEngine:
    """Test DiscoveryEngine functionality."""
    
    def test_discovery_engine_has_generate_query_plan(self):
        """Test DiscoveryEngine has generate_query_plan method."""
        engine = get_discovery_engine()
        assert hasattr(engine, 'generate_query_plan')
        print("✓ DiscoveryEngine.generate_query_plan method exists")
    
    def test_discovery_engine_has_status(self):
        """Test DiscoveryEngine has get_engine_status method."""
        engine = get_discovery_engine()
        assert hasattr(engine, 'get_engine_status')
        print("✓ DiscoveryEngine.get_engine_status method exists")


class TestParseEngine:
    """Test ParseEngine functionality."""
    
    def test_parse_engine_has_parse_results(self):
        """Test ParseEngine has parse_results method."""
        engine = get_parse_engine()
        assert hasattr(engine, 'parse_results')
        print("✓ ParseEngine.parse_results method exists")
    
    def test_parse_engine_has_health_check(self):
        """Test ParseEngine has health_check method."""
        engine = get_parse_engine()
        assert hasattr(engine, 'health_check')
        print("✓ ParseEngine.health_check method exists")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
