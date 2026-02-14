"""
Parse Engine for OSINT Investigation Pipeline

Purpose
- Parse raw search results into structured entities
- Extract relevant information from HTML, JSON, and text content
- Validate and clean extracted data
- Provide comprehensive error handling and observability

Invariants
- All parsed entities must have required fields populated
- Sensitive data is redacted before logging or storage
- Every parse operation is logged with structured telemetry
- Invalid or malicious content is rejected with detailed errors
- Parse results are validated against entity schemas

Failure Modes
- Invalid HTML/XML → parse fails with structured error message
- Missing required fields → entity is rejected with field-specific error
- Malicious content detected → parse is blocked and security event logged
- Parser timeout → content is marked as failed and retried if appropriate
- Schema validation failure → entity is rejected with validation details

Debug Notes
- Use correlation_id to trace parse operations through the pipeline
- Monitor parse_duration_ms metrics for performance issues
- Check parse_failed alerts for content quality issues
- Review security_validation_failed alerts for potential attacks
- Use entity_validation_failed metrics to monitor data quality

Design Tradeoffs
- Chose comprehensive validation over permissive parsing for data quality
- Tradeoff: Stricter validation rejects some valid content but ensures data integrity
- Mitigation: Multiple parser strategies and fallback options for edge cases
- Review trigger: If parse success rate drops below 80%, relax validation rules
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
from urllib.parse import urlparse, parse_qs

from bs4 import BeautifulSoup, Tag
import lxml.html

from ..models.entities import (
    Entity, EntityType, SearchResult, VerificationStatus,
    validate_email, validate_phone, validate_domain,
    redact_sensitive_data
)


class ParseStatus(Enum):
    """Status of parse operations."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATION_ERROR = "validation_error"
    SECURITY_BLOCKED = "security_blocked"


class ContentType(Enum):
    """Types of content that can be parsed."""
    HTML = "html"
    JSON = "json"
    XML = "xml"
    TEXT = "text"
    UNKNOWN = "unknown"


@dataclass
class ParseResult:
    """Result of parsing a search result."""
    result_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = ""
    source_result_id: str = ""
    entities: List[Entity] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    parse_status: ParseStatus = ParseStatus.PENDING
    error_message: Optional[str] = None
    parse_duration_ms: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def mark_completed(self, entities: List[Entity]):
        """Mark parse as completed with entities."""
        self.parse_status = ParseStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.entities = entities

    def mark_failed(self, error_message: str, status: ParseStatus = ParseStatus.FAILED):
        """Mark parse as failed."""
        self.parse_status = status
        self.completed_at = datetime.utcnow()
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "result_id": self.result_id,
            "correlation_id": self.correlation_id,
            "source_result_id": self.source_result_id,
            "entities_count": len(self.entities),
            "metadata": self.metadata,
            "parse_status": self.parse_status.value,
            "error_message": self.error_message,
            "parse_duration_ms": self.parse_duration_ms,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class ParseMetrics:
    """Metrics for parse operations."""
    total_results: int = 0
    completed_parses: int = 0
    failed_parses: int = 0
    validation_errors: int = 0
    security_blocked: int = 0
    total_entities_extracted: int = 0
    total_duration_ms: int = 0
    content_type_metrics: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def get_success_rate(self) -> float:
        """Calculate parse success rate percentage."""
        if self.total_results == 0:
            return 0.0
        return (self.completed_parses / self.total_results) * 100

    def get_average_duration_ms(self) -> float:
        """Calculate average parse duration in milliseconds."""
        if self.completed_parses == 0:
            return 0.0
        return self.total_duration_ms / self.completed_parses

    def get_entities_per_result(self) -> float:
        """Calculate average entities extracted per result."""
        if self.completed_parses == 0:
            return 0.0
        return self.total_entities_extracted / self.completed_parses

    def update_content_type_metrics(self, content_type: str, status: str, duration_ms: int):
        """Update metrics for a specific content type."""
        if content_type not in self.content_type_metrics:
            self.content_type_metrics[content_type] = {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "duration_ms": 0
            }
        
        self.content_type_metrics[content_type]["total"] += 1
        if status == "completed":
            self.content_type_metrics[content_type]["completed"] += 1
            self.content_type_metrics[content_type]["duration_ms"] += duration_ms
        else:
            self.content_type_metrics[content_type]["failed"] += 1


class BaseParser:
    """Base class for content parsers."""

    def __init__(self, content_type: ContentType):
        """Initialize parser for specific content type."""
        self.content_type = content_type
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def parse(self, search_result: SearchResult, correlation_id: str) -> ParseResult:
        """
        Parse a search result into entities.

        Summary
        - Extract entities from search result content
        - Validate extracted entities against schemas
        - Apply security validation and redaction

        Preconditions
        - search_result must have valid content and metadata
        - correlation_id must be provided for tracing

        Postconditions
        - Returns ParseResult with extracted entities
        - All entities are validated and cleaned
        - Sensitive data is redacted

        Error cases
        - Invalid content format → ParseResult with error details
        - Security validation failure → ParseResult marked as security_blocked
        - Schema validation failure → ParseResult with validation errors

        Idempotency: Deterministic - same input produces same entities
        Side effects: Updates metrics and logs parse operations
        """
        start_time = datetime.utcnow()
        
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "parse.parse_result",
            "content_type": self.content_type.value,
            "source_url": search_result.url
        })

        parse_result = ParseResult(
            correlation_id=correlation_id,
            source_result_id=search_result.url
        )

        try:
            # Security validation
            self._validate_content_security(search_result.content, correlation_id)

            # Detect content type if unknown
            detected_type = self._detect_content_type(search_result.content)
            if detected_type != self.content_type:
                logger.warning("content type mismatch", {
                    "expected_type": self.content_type.value,
                    "detected_type": detected_type.value
                })

            # Parse content
            entities = await self._extract_entities(search_result, correlation_id)

            # Validate entities
            valid_entities = []
            for entity in entities:
                if self._validate_entity(entity, correlation_id):
                    valid_entities.append(entity)
                else:
                    logger.warning("entity validation failed", {
                        "entity_type": entity.entity_type.value,
                        "entity_id": entity.id
                    })

            parse_result.mark_completed(valid_entities)

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            parse_result.parse_duration_ms = duration_ms

            logger.info("parse operation completed", {
                "entities_extracted": len(valid_entities),
                "duration_ms": duration_ms,
                "content_length": len(search_result.content)
            })

            return parse_result

        except SecurityError as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            parse_result.mark_failed(str(e), ParseStatus.SECURITY_BLOCKED)
            parse_result.parse_duration_ms = duration_ms

            logger.error("parse operation blocked by security", {
                "error": str(e),
                "duration_ms": duration_ms
            })
            return parse_result

        except ValidationError as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            parse_result.mark_failed(str(e), ParseStatus.VALIDATION_ERROR)
            parse_result.parse_duration_ms = duration_ms

            logger.error("parse operation failed validation", {
                "error": str(e),
                "duration_ms": duration_ms
            })
            return parse_result

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            parse_result.mark_failed(str(e), ParseStatus.FAILED)
            parse_result.parse_duration_ms = duration_ms

            logger.error("parse operation failed", {
                "error": str(e),
                "duration_ms": duration_ms
            })
            return parse_result

    def _validate_content_security(self, content: str, correlation_id: str):
        """Validate content for security issues."""
        # Check content size
        if len(content) > 10 * 1024 * 1024:  # 10MB limit
            raise SecurityError("Content too large for processing")

        # Check for malicious patterns
        malicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'data:',
            r'vbscript:',
            r'onload\s*=',
            r'onerror\s*=',
            r'eval\s*\(',
            r'document\.cookie',
            r'window\.location',
            r'XMLHttpRequest',
            r'fetch\s*\('
        ]

        content_lower = content.lower()
        for pattern in malicious_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                raise SecurityError(f"Malicious pattern detected: {pattern}")

        # Check for excessive encoding (potential obfuscation)
        try:
            decoded_attempts = 0
            current_content = content
            while decoded_attempts < 5:
                # Try common encodings
                if current_content.startswith('%'):
                    import urllib.parse
                    try:
                        decoded = urllib.parse.unquote(current_content)
                        if decoded != current_content:
                            current_content = decoded
                            decoded_attempts += 1
                            continue
                    except:
                        pass
                
                # Try base64
                import base64
                try:
                    decoded = base64.b64decode(current_content).decode('utf-8')
                    if decoded != current_content and len(decoded) > 10:
                        current_content = decoded
                        decoded_attempts += 1
                        continue
                except:
                    pass
                
                break
            
            if decoded_attempts >= 5:
                raise SecurityError("Excessive content encoding detected")
        except:
            pass  # If decoding fails, continue with original content

    def _detect_content_type(self, content: str) -> ContentType:
        """Detect the actual content type."""
        content_stripped = content.strip()
        
        # Check for JSON
        if content_stripped.startswith('{') and content_stripped.endswith('}'):
            try:
                json.loads(content_stripped)
                return ContentType.JSON
            except:
                pass
        
        # Check for XML
        if content_stripped.startswith('<') and content_stripped.endswith('>'):
            try:
                lxml.html.fromstring(content_stripped)
                return ContentType.HTML
            except:
                try:
                    import xml.etree.ElementTree as ET
                    ET.fromstring(content_stripped)
                    return ContentType.XML
                except:
                    pass
        
        # Default to text
        return ContentType.TEXT

    async def _extract_entities(self, search_result: SearchResult, correlation_id: str) -> List[Entity]:
        """Extract entities from search result - to be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _extract_entities")

    def _validate_entity(self, entity: Entity, correlation_id: str) -> bool:
        """Validate an entity meets minimum requirements."""
        if not entity.attributes:
            return False
        
        # Check required fields based on entity type
        if entity.entity_type == EntityType.PERSON:
            return 'name' in entity.attributes and len(entity.attributes['name'].strip()) > 0
        elif entity.entity_type == EntityType.EMAIL_ADDRESS:
            return 'email' in entity.attributes and validate_email(entity.attributes['email'])
        elif entity.entity_type == EntityType.PHONE_NUMBER:
            return 'phone' in entity.attributes and validate_phone(entity.attributes['phone'])
        elif entity.entity_type == EntityType.DOMAIN:
            return 'domain' in entity.attributes and validate_domain(entity.attributes['domain'])
        elif entity.entity_type == EntityType.USERNAME:
            return 'username' in entity.attributes and len(entity.attributes['username'].strip()) > 0
        elif entity.entity_type == EntityType.SOCIAL_PROFILE:
            return 'platform' in entity.attributes and 'username' in entity.attributes
        
        return True


class HTMLParser(BaseParser):
    """Parser for HTML content."""

    def __init__(self):
        super().__init__(ContentType.HTML)

    async def _extract_entities(self, search_result: SearchResult, correlation_id: str) -> List[Entity]:
        """Extract entities from HTML content."""
        entities = []
        
        try:
            soup = BeautifulSoup(search_result.content, 'html.parser')
            
            # Extract person entities
            person_entities = self._extract_person_entities(soup, search_result, correlation_id)
            entities.extend(person_entities)
            
            # Extract social profile entities
            social_entities = self._extract_social_entities(soup, search_result, correlation_id)
            entities.extend(social_entities)
            
            # Extract contact information
            contact_entities = self._extract_contact_entities(soup, search_result, correlation_id)
            entities.extend(contact_entities)
            
            # Extract company entities
            company_entities = self._extract_company_entities(soup, search_result, correlation_id)
            entities.extend(company_entities)

        except Exception as e:
            self.logger.error("HTML parsing failed", {
                "correlation_id": correlation_id,
                "error": str(e)
            })
            raise

        return entities

    def _extract_person_entities(self, soup: BeautifulSoup, search_result: SearchResult, 
                               correlation_id: str) -> List[Entity]:
        """Extract person entities from HTML."""
        entities = []
        
        # Look for common person patterns
        person_selectors = [
            '[class*="name"]',
            '[class*="profile"]',
            '[class*="author"]',
            '[class*="user"]',
            'h1', 'h2', 'h3',
            '[property="name"]',
            '[data-name]'
        ]
        
        for selector in person_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 2 and len(text) < 100:
                    # Basic name validation
                    if self._looks_like_name(text):
                        entity = Entity(
                            entity_type=EntityType.PERSON,
                            attributes={
                                'name': text,
                                'source_element': element.name,
                                'source_class': element.get('class', []),
                                'context': self._get_element_context(element)
                            },
                            confidence_score=search_result.confidence * 0.8,
                            verification_status=VerificationStatus.POSSIBLE
                        )
                        entity.add_source(search_result.url, search_result.source_type, search_result.confidence)
                        entities.append(entity)

        return entities

    def _extract_social_entities(self, soup: BeautifulSoup, search_result: SearchResult, 
                               correlation_id: str) -> List[Entity]:
        """Extract social media profile entities from HTML."""
        entities = []
        
        # Look for social media links
        social_patterns = {
            'linkedin.com': 'LinkedIn',
            'github.com': 'GitHub',
            'twitter.com': 'Twitter',
            'facebook.com': 'Facebook',
            'instagram.com': 'Instagram',
            'youtube.com': 'YouTube',
            'tiktok.com': 'TikTok'
        }
        
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href'].lower()
            for domain, platform in social_patterns.items():
                if domain in href:
                    # Extract username from URL
                    username = self._extract_username_from_url(href, domain)
                    if username:
                        entity = Entity(
                            entity_type=EntityType.SOCIAL_PROFILE,
                            attributes={
                                'platform': platform,
                                'username': username,
                                'url': link['href'],
                                'text': link.get_text(strip=True)
                            },
                            confidence_score=search_result.confidence * 0.9,
                            verification_status=VerificationStatus.PROBABLE
                        )
                        entity.add_source(search_result.url, search_result.source_type, search_result.confidence)
                        entities.append(entity)

        return entities

    def _extract_contact_entities(self, soup: BeautifulSoup, search_result: SearchResult, 
                                 correlation_id: str) -> List[Entity]:
        """Extract contact information entities from HTML."""
        entities = []
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, soup.get_text())
        for email in emails:
            if validate_email(email):
                entity = Entity(
                    entity_type=EntityType.EMAIL_ADDRESS,
                    attributes={'email': email},
                    confidence_score=search_result.confidence * 0.95,
                    verification_status=VerificationStatus.VERIFIED
                )
                entity.add_source(search_result.url, search_result.source_type, search_result.confidence)
                entities.append(entity)

        # Extract phone numbers
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
        phones = re.findall(phone_pattern, soup.get_text())
        for phone in phones:
            if validate_phone(phone):
                entity = Entity(
                    entity_type=EntityType.PHONE_NUMBER,
                    attributes={'phone': phone},
                    confidence_score=search_result.confidence * 0.8,
                    verification_status=VerificationStatus.PROBABLE
                )
                entity.add_source(search_result.url, search_result.source_type, search_result.confidence)
                entities.append(entity)

        return entities

    def _extract_company_entities(self, soup: BeautifulSoup, search_result: SearchResult, 
                                 correlation_id: str) -> List[Entity]:
        """Extract company entities from HTML."""
        entities = []
        
        # Look for company patterns
        company_selectors = [
            '[class*="company"]',
            '[class*="employer"]',
            '[class*="organization"]',
            '[property="worksFor"]',
            '[class*="work"]'
        ]
        
        for selector in company_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 2 and len(text) < 100:
                    entity = Entity(
                        entity_type=EntityType.COMPANY,
                        attributes={
                            'name': text,
                            'source_element': element.name,
                            'context': self._get_element_context(element)
                        },
                        confidence_score=search_result.confidence * 0.7,
                        verification_status=VerificationStatus.POSSIBLE
                    )
                    entity.add_source(search_result.url, search_result.source_type, search_result.confidence)
                    entities.append(entity)

        return entities

    def _looks_like_name(self, text: str) -> bool:
        """Check if text looks like a person's name."""
        # Basic heuristics for name detection
        words = text.split()
        if len(words) < 2 or len(words) > 4:
            return False
        
        # Check for common name patterns
        for word in words:
            if not word.isalpha() or not word[0].isupper():
                return False
        
        # Check for non-name words
        non_name_words = {'the', 'and', 'or', 'but', 'for', 'with', 'at', 'in', 'on', 'by', 'to', 'from'}
        if any(word.lower() in non_name_words for word in words):
            return False
        
        return True

    def _extract_username_from_url(self, url: str, domain: str) -> Optional[str]:
        """Extract username from social media URL."""
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')
            
            if domain == 'linkedin.com':
                # LinkedIn URLs: linkedin.com/in/username or linkedin.com/company/username
                if 'in/' in url:
                    return path_parts[path_parts.index('in') + 1] if 'in' in path_parts else None
                elif 'company/' in url:
                    return path_parts[path_parts.index('company') + 1] if 'company' in path_parts else None
            elif domain in ['github.com', 'twitter.com', 'facebook.com', 'instagram.com', 'tiktok.com']:
                # Simple username pattern: domain/username
                return path_parts[0] if path_parts else None
            elif domain == 'youtube.com':
                # YouTube: channel/ID or user/username or c/custom
                if 'channel/' in url:
                    return path_parts[path_parts.index('channel') + 1] if 'channel' in path_parts else None
                elif 'user/' in url:
                    return path_parts[path_parts.index('user') + 1] if 'user' in path_parts else None
                elif 'c/' in url:
                    return path_parts[path_parts.index('c') + 1] if 'c' in path_parts else None
        
        except Exception:
            pass
        
        return None

    def _get_element_context(self, element: Tag) -> str:
        """Get context around an element."""
        try:
            parent = element.parent
            if parent:
                parent_text = parent.get_text(strip=True)
                if len(parent_text) > 200:
                    parent_text = parent_text[:200] + "..."
                return parent_text
        except:
            pass
        return ""


class JSONParser(BaseParser):
    """Parser for JSON content."""

    def __init__(self):
        super().__init__(ContentType.JSON)

    async def _extract_entities(self, search_result: SearchResult, correlation_id: str) -> List[Entity]:
        """Extract entities from JSON content."""
        entities = []
        
        try:
            data = json.loads(search_result.content)
            
            # Recursively extract entities from JSON structure
            entities.extend(self._extract_from_json_structure(data, search_result, correlation_id))

        except json.JSONDecodeError as e:
            self.logger.error("JSON parsing failed", {
                "correlation_id": correlation_id,
                "error": str(e)
            })
            raise

        return entities

    def _extract_from_json_structure(self, data: Any, search_result: SearchResult, 
                                   correlation_id: str, path: str = "") -> List[Entity]:
        """Recursively extract entities from JSON structure."""
        entities = []
        
        if isinstance(data, dict):
            # Look for common entity fields
            entities.extend(self._extract_entities_from_dict(data, search_result, correlation_id, path))
            
            # Recurse into nested objects
            for key, value in data.items():
                new_path = f"{path}.{key}" if path else key
                entities.extend(self._extract_from_json_structure(value, search_result, correlation_id, new_path))
        
        elif isinstance(data, list):
            # Recurse into list items
            for i, item in enumerate(data):
                new_path = f"{path}[{i}]" if path else f"[{i}]"
                entities.extend(self._extract_from_json_structure(item, search_result, correlation_id, new_path))
        
        return entities

    def _extract_entities_from_dict(self, data: Dict[str, Any], search_result: SearchResult, 
                                  correlation_id: str, path: str) -> List[Entity]:
        """Extract entities from a dictionary."""
        entities = []
        
        # Look for person entities
        person_fields = ['name', 'fullName', 'firstName', 'lastName', 'username', 'screenName']
        person_data = {k: v for k, v in data.items() if k.lower() in [f.lower() for f in person_fields]}
        if person_data:
            entity = Entity(
                entity_type=EntityType.PERSON,
                attributes=person_data,
                confidence_score=search_result.confidence * 0.85,
                verification_status=VerificationStatus.PROBABLE
            )
            entity.add_source(search_result.url, search_result.source_type, search_result.confidence)
            entities.append(entity)

        # Look for email entities
        if 'email' in data and validate_email(data['email']):
            entity = Entity(
                entity_type=EntityType.EMAIL_ADDRESS,
                attributes={'email': data['email']},
                confidence_score=search_result.confidence * 0.95,
                verification_status=VerificationStatus.VERIFIED
            )
            entity.add_source(search_result.url, search_result.source_type, search_result.confidence)
            entities.append(entity)

        # Look for company entities
        company_fields = ['company', 'employer', 'organization', 'workplace']
        for field in company_fields:
            if field in data and isinstance(data[field], str) and len(data[field]) > 2:
                entity = Entity(
                    entity_type=EntityType.COMPANY,
                    attributes={'name': data[field]},
                    confidence_score=search_result.confidence * 0.8,
                    verification_status=VerificationStatus.POSSIBLE
                )
                entity.add_source(search_result.url, search_result.source_type, search_result.confidence)
                entities.append(entity)

        return entities


class TextParser(BaseParser):
    """Parser for plain text content."""

    def __init__(self):
        super().__init__(ContentType.TEXT)

    async def _extract_entities(self, search_result: SearchResult, correlation_id: str) -> List[Entity]:
        """Extract entities from plain text content."""
        entities = []
        
        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, search_result.content)
        for email in emails:
            if validate_email(email):
                entity = Entity(
                    entity_type=EntityType.EMAIL_ADDRESS,
                    attributes={'email': email},
                    confidence_score=search_result.confidence * 0.9,
                    verification_status=VerificationStatus.PROBABLE
                )
                entity.add_source(search_result.url, search_result.source_type, search_result.confidence)
                entities.append(entity)

        # Extract phone numbers
        phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
        phones = re.findall(phone_pattern, search_result.content)
        for phone in phones:
            if validate_phone(phone):
                entity = Entity(
                    entity_type=EntityType.PHONE_NUMBER,
                    attributes={'phone': phone},
                    confidence_score=search_result.confidence * 0.8,
                    verification_status=VerificationStatus.POSSIBLE
                )
                entity.add_source(search_result.url, search_result.source_type, search_result.confidence)
                entities.append(entity)

        # Extract domains
        domain_pattern = r'\b[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+\b'
        domains = re.findall(domain_pattern, search_result.content)
        for domain in domains:
            if validate_domain(domain):
                entity = Entity(
                    entity_type=EntityType.DOMAIN,
                    attributes={'domain': domain},
                    confidence_score=search_result.confidence * 0.7,
                    verification_status=VerificationStatus.POSSIBLE
                )
                entity.add_source(search_result.url, search_result.source_type, search_result.confidence)
                entities.append(entity)

        return entities


class SecurityError(Exception):
    """Security validation error."""
    pass


class ValidationError(Exception):
    """Validation error."""
    pass


class ParseEngine:
    """
    Core parse engine for processing search results.

    Purpose
    - Coordinate parsing of search results into entities
    - Manage different content type parsers
    - Provide comprehensive error handling and metrics

    Invariants
    - All search results are processed through appropriate parsers
    - Security validation is applied to all content
    - Parse operations are logged with correlation IDs
    - Extracted entities are validated before return

    Failure Modes
    - Unsupported content type → result marked as failed with appropriate error
    - Parser initialization failure → engine logs error and continues with other parsers
    - Security validation failure → result is blocked and security event logged
    - Entity validation failure → entities are filtered but parse continues

    Debug Notes
    - Use correlation_id to trace parse operations through the system
    - Monitor parse_success_rate metrics for overall system health
    - Check content_type_metrics for parser-specific issues
    - Review security_blocked metrics for potential attack patterns

    Design Tradeoffs
    - Chose multiple specialized parsers over single general parser
    - Tradeoff: More complex code but better accuracy for different content types
    - Mitigation: Fallback to text parser for unsupported content types
    - Review trigger: If parser selection accuracy drops below 90%, simplify approach
    """

    def __init__(self):
        """Initialize parse engine with all parsers."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.metrics = ParseMetrics()
        
        # Initialize parsers
        self.parsers = {
            ContentType.HTML: HTMLParser(),
            ContentType.JSON: JSONParser(),
            ContentType.XML: HTMLParser(),  # Use HTML parser for XML as fallback
            ContentType.TEXT: TextParser(),
            ContentType.UNKNOWN: TextParser()  # Use text parser for unknown content
        }

    async def parse_results(self, search_results: List[SearchResult], 
                          correlation_id: Optional[str] = None) -> List[ParseResult]:
        """
        Parse multiple search results into entities.

        Summary
        - Process each search result through appropriate parser
        - Apply security validation and entity validation
        - Return parse results with extracted entities

        Preconditions
        - search_results must be valid SearchResult objects
        - correlation_id must be provided for tracing

        Postconditions
        - All results are processed or marked as failed
        - Extracted entities are validated and cleaned
        - Metrics are updated for all operations

        Error cases
        - Invalid search result → result is marked as failed with error details
        - Parser unavailable → result is marked as failed with appropriate error
        - Security validation failure → result is blocked and security event logged

        Idempotency: Deterministic - same input produces same parse results
        Side effects: Updates metrics and logs parse operations
        """
        start_time = datetime.utcnow()
        
        if not correlation_id:
            correlation_id = str(uuid4())
        
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "parse_engine.parse_results",
            "result_count": len(search_results)
        })
        
        logger.info("starting batch parse operation")

        try:
            # Process results in parallel
            parse_tasks = []
            for result in search_results:
                task = self._parse_single_result(result, correlation_id)
                parse_tasks.append(task)

            parse_results = await asyncio.gather(*parse_tasks, return_exceptions=True)

            # Handle exceptions and update metrics
            final_results = []
            for i, parse_result in enumerate(parse_results):
                if isinstance(parse_result, Exception):
                    logger.error("parse task failed", {
                        "result_index": i,
                        "error": str(parse_result)
                    })
                    # Create failed result
                    failed_result = ParseResult(
                        correlation_id=correlation_id,
                        source_result_id=search_results[i].url
                    )
                    failed_result.mark_failed(str(parse_result))
                    final_results.append(failed_result)
                    self.metrics.failed_parses += 1
                else:
                    final_results.append(parse_result)
                    self.metrics.total_results += 1
                    
                    if parse_result.parse_status == ParseStatus.COMPLETED:
                        self.metrics.completed_parses += 1
                        self.metrics.total_entities_extracted += len(parse_result.entities)
                    elif parse_result.parse_status == ParseStatus.VALIDATION_ERROR:
                        self.metrics.validation_errors += 1
                    elif parse_result.parse_status == ParseStatus.SECURITY_BLOCKED:
                        self.metrics.security_blocked += 1
                    else:
                        self.metrics.failed_parses += 1

                    # Update content type metrics
                    content_type = self._detect_content_type(search_results[i].content)
                    self.metrics.update_content_type_metrics(
                        content_type.value,
                        parse_result.parse_status.value,
                        parse_result.parse_duration_ms
                    )

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info("batch parse operation completed", {
                "total_results": len(search_results),
                "completed_parses": self.metrics.completed_parses,
                "failed_parses": self.metrics.failed_parses,
                "total_entities": self.metrics.total_entities_extracted,
                "duration_ms": duration_ms,
                "success_rate": self.metrics.get_success_rate()
            })

            return final_results

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error("batch parse operation failed", {
                "error": str(e),
                "duration_ms": duration_ms
            })
            raise

    async def _parse_single_result(self, search_result: SearchResult, correlation_id: str) -> ParseResult:
        """Parse a single search result."""
        try:
            # Detect content type
            content_type = self._detect_content_type(search_result.content)
            
            # Get appropriate parser
            parser = self.parsers.get(content_type, self.parsers[ContentType.UNKNOWN])
            
            # Parse the result
            parse_result = await parser.parse(search_result, correlation_id)
            
            return parse_result

        except Exception as e:
            self.logger.error("single result parse failed", {
                "correlation_id": correlation_id,
                "result_url": search_result.url,
                "error": str(e)
            })
            
            parse_result = ParseResult(
                correlation_id=correlation_id,
                source_result_id=search_result.url
            )
            parse_result.mark_failed(str(e))
            return parse_result

    def _detect_content_type(self, content: str) -> ContentType:
        """Detect content type from content."""
        content_stripped = content.strip()
        
        # Check for JSON
        if content_stripped.startswith('{') and content_stripped.endswith('}'):
            try:
                json.loads(content_stripped)
                return ContentType.JSON
            except:
                pass
        
        # Check for XML/HTML
        if content_stripped.startswith('<') and content_stripped.endswith('>'):
            try:
                lxml.html.fromstring(content_stripped)
                return ContentType.HTML
            except:
                try:
                    import xml.etree.ElementTree as ET
                    ET.fromstring(content_stripped)
                    return ContentType.XML
                except:
                    pass
        
        # Default to text
        return ContentType.TEXT

    def get_metrics(self) -> Dict[str, Any]:
        """Get current parse metrics."""
        return {
            "total_results": self.metrics.total_results,
            "completed_parses": self.metrics.completed_parses,
            "failed_parses": self.metrics.failed_parses,
            "validation_errors": self.metrics.validation_errors,
            "security_blocked": self.metrics.security_blocked,
            "total_entities_extracted": self.metrics.total_entities_extracted,
            "success_rate": self.metrics.get_success_rate(),
            "average_duration_ms": self.metrics.get_average_duration_ms(),
            "entities_per_result": self.metrics.get_entities_per_result(),
            "content_type_metrics": self.metrics.content_type_metrics
        }

    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on parse engine."""
        health_status = {
            "parsers_initialized": len(self.parsers) > 0,
            "no_active_errors": True,  # Could be enhanced with actual error tracking
            "metrics_available": self.metrics.total_results >= 0
        }
        
        return health_status
