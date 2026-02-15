"""
OSINT Framework Connectors Package

This package contains all connector implementations for various OSINT sources.

Connectors:
- Google Search: Web search results
- LinkedIn: Professional profiles
- GitHub: Developer profiles and repositories
- Twitter: Social media profiles and posts
- WHOIS/RDAP: Domain registration data
- Certificate Transparency: SSL/TLS certificate logs
"""

from .base import (
    SourceConnector, ConnectorRegistry, ConnectorStatus,
    RateLimitInfo, register_connector, get_registry
)
from .google import GoogleSearchConnector
from .linkedin import LinkedInConnector
from .github import GitHubConnector
from .twitter import TwitterConnector
from .whois import WhoisConnector
from .certificate_transparency import CertificateTransparencyConnector
from .reddit import RedditConnector
from .stackoverflow import StackOverflowConnector


__all__ = [
    # Base classes
    "SourceConnector", "ConnectorRegistry", "ConnectorStatus", "RateLimitInfo",
    
    # Utility functions
    "register_connector", "get_registry",
    
    # Connectors
    "GoogleSearchConnector",
    "LinkedInConnector",
    "GitHubConnector",
    "TwitterConnector",
    "WhoisConnector",
    "CertificateTransparencyConnector",
    "RedditConnector",
    "StackOverflowConnector"
]
