"""
Integration tests for OSINT Framework

Tests:
- Discovery engine query generation
- Basic pipeline operations
- Data model validation
"""

import pytest
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src import (
    get_discovery_engine,
    get_normalization_engine,
    get_entity_resolver,
    InvestigationInput,
    Entity,
    EntityType,
    VerificationStatus,
    validate_email,
    validate_phone
)
from src.core.models.entities import SubjectIdentifiers


class TestDataValidation:
    """Test data model validation."""
    
    def test_validate_email_valid(self):
        """Test email validation with valid email."""
        assert validate_email("test@example.com") == True
        print("✓ Valid email validation passed")
    
    def test_validate_email_invalid(self):
        """Test email validation with invalid email."""
        assert validate_email("not-an-email") == False
        print("✓ Invalid email validation passed")
    
    def test_validate_phone_valid(self):
        """Test phone validation with valid phone."""
        assert validate_phone("+12345678901") == True
        print("✓ Valid phone validation passed")
    
    def test_validate_phone_invalid(self):
        """Test phone validation with invalid phone."""
        assert validate_phone("not-a-phone") == False
        print("✓ Invalid phone validation passed")


class TestEntityCreation:
    """Test Entity model creation."""
    
    def test_entity_basic_creation(self):
        """Test basic entity creation."""
        entity = Entity(
            entity_id="test-001",
            entity_type=EntityType.PERSON,
            data={"name": "John Doe"},
            source="test_source",
            confidence=0.95
        )
        assert entity.entity_id == "test-001"
        assert entity.entity_type == EntityType.PERSON
        assert entity.confidence == 0.95
        print("✓ Entity creation passed")
    
    def test_entity_verification_status(self):
        """Test entity verification status."""
        entity = Entity(
            entity_id="test-002",
            entity_type=EntityType.EMAIL,
            data={"email": "test@example.com"},
            source="test_source",
            confidence=0.85,
            verification_status=VerificationStatus.VERIFIED
        )
        assert entity.verification_status == VerificationStatus.VERIFIED
        print("✓ Entity verification status passed")


class TestInvestigationInput:
    """Test InvestigationInput model."""
    
    def test_investigation_input_creation(self):
        """Test basic investigation input creation."""
        input_data = InvestigationInput(
            investigation_id="inv-001",
            subject_identifiers=SubjectIdentifiers(full_name="Jane Doe")
        )
        assert input_data.investigation_id == "inv-001"
        assert input_data.subject_identifiers.full_name == "Jane Doe"
        print("✓ InvestigationInput creation passed")
    
    def test_investigation_input_with_identifiers(self):
        """Test investigation input with multiple identifiers."""
        input_data = InvestigationInput(
            investigation_id="inv-002",
            subject_identifiers=SubjectIdentifiers(
                full_name="John Smith",
                known_usernames=["jsmith", "john.smith"],
                email_addresses=["john@example.com"]
            )
        )
        assert len(input_data.subject_identifiers.known_usernames) == 2
        assert len(input_data.subject_identifiers.email_addresses) == 1
        print("✓ InvestigationInput with multiple identifiers passed")


class TestDiscoveryEngineIntegration:
    """Test DiscoveryEngine integration."""
    
    def test_discovery_engine_query_plan_generation(self):
        """Test query plan generation."""
        engine = get_discovery_engine()
        
        # Create investigation input
        inv_input = InvestigationInput(
            investigation_id="test-inv-001",
            subject_identifiers=SubjectIdentifiers(
                full_name="Test User",
                known_usernames=["testuser"]
            )
        )
        
        # Generate query plan
        query_plan = engine.generate_query_plan(inv_input)
        
        assert query_plan is not None
        assert "queries" in query_plan
        print("✓ Query plan generation passed")
    
    def test_discovery_engine_status(self):
        """Test engine status retrieval."""
        engine = get_discovery_engine()
        status = engine.get_engine_status()
        
        assert status is not None
        print(f"✓ Engine status retrieved: {status}")


class TestNormalizationEngine:
    """Test NormalizationEngine."""
    
    def test_normalization_engine_exists(self):
        """Test normalization engine can be created."""
        engine = get_normalization_engine()
        assert engine is not None
        print("✓ NormalizationEngine created successfully")
    
    def test_normalization_normalize_entities(self):
        """Test entity normalization."""
        engine = get_normalization_engine()
        
        # Create test entities
        entities = [
            Entity(
                entity_id="e1",
                entity_type=EntityType.PERSON,
                data={"name": "John Doe"},
                source="test"
            ),
            Entity(
                entity_id="e2",
                entity_type=EntityType.EMAIL,
                data={"email": "john@example.com"},
                source="test"
            )
        ]
        
        # Normalize entities
        normalized = engine.normalize_entities(entities)
        assert normalized is not None
        assert len(normalized) > 0
        print(f"✓ Entity normalization passed, normalized {len(normalized)} entities")


class TestEntityResolver:
    """Test EntityResolver."""
    
    def test_entity_resolver_exists(self):
        """Test entity resolver can be created."""
        resolver = get_entity_resolver()
        assert resolver is not None
        print("✓ EntityResolver created successfully")
    
    def test_entity_resolver_resolve_entities(self):
        """Test entity resolution."""
        resolver = get_entity_resolver()
        
        # Create test entities
        entities = [
            Entity(
                entity_id="e1",
                entity_type=EntityType.PERSON,
                data={"name": "john doe", "email": "john@example.com"},
                source="source1",
                confidence=0.9
            ),
            Entity(
                entity_id="e2",
                entity_type=EntityType.PERSON,
                data={"name": "John Doe", "email": "john@example.com"},
                source="source2",
                confidence=0.85
            )
        ]
        
        # Resolve entities
        resolved = resolver.resolve_entities(entities)
        assert resolved is not None
        print(f"✓ Entity resolution passed, resolved to {len(resolved)} unique entities")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
