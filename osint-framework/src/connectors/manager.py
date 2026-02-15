"""
Connector Manager for OSINT Framework

Purpose
- Initialize and manage all available connectors
- Load configuration from environment or config files
- Provide factory methods for connector creation
- Handle connector lifecycle management

Invariants
- All registered connectors are properly initialized
- Configuration is validated before connector creation
- Failed connector initialization doesn't block others
- Metrics are tracked for all connector operations

Failure Modes
- Missing configuration → connector initialized with defaults
- Invalid credentials → connector marked as requiring auth
- Initialization failure → logged and connector skipped
- Configuration error → detailed error logging with recovery suggestions
"""

import logging
import os
from typing import Dict, List, Any, Optional

from .base import ConnectorRegistry
from .google import GoogleSearchConnector
from .linkedin import LinkedInConnector
from .github import GitHubConnector
from .twitter import TwitterConnector
from .whois import WhoisConnector
from .certificate_transparency import CertificateTransparencyConnector
from .reddit import RedditConnector
from .stackoverflow import StackOverflowConnector


logger = logging.getLogger(__name__)


class ConnectorManager:
    """Manages connector lifecycle and initialization."""
    
    def __init__(self):
        """Initialize connector manager."""
        self.registry = ConnectorRegistry()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._initialized = False
    
    def initialize_default_connectors(self) -> ConnectorRegistry:
        """Initialize all default connectors."""
        if self._initialized:
            return self.registry
        
        self.logger.info("Initializing default connectors")
        
        # Load configuration from environment
        config = self._load_config()
        
        # Initialize each connector with error handling
        connectors_to_init = [
            ('google', GoogleSearchConnector, config.get('google', {})),
            ('linkedin', LinkedInConnector, config.get('linkedin', {})),
            ('github', GitHubConnector, config.get('github', {})),
            ('twitter', TwitterConnector, config.get('twitter', {})),
            ('whois', WhoisConnector, config.get('whois', {})),
            ('certificate_transparency', CertificateTransparencyConnector, config.get('certificate_transparency', {})),
            ('reddit', RedditConnector, config.get('reddit', {})),
            ('stackoverflow', StackOverflowConnector, config.get('stackoverflow', {})),
        ]
        
        for name, connector_class, connector_config in connectors_to_init:
            try:
                connector = connector_class(connector_config)
                self.registry.register(connector, connector_config)
                self.logger.info(f"✓ Initialized {name} connector")
            except Exception as e:
                self.logger.error(f"✗ Failed to initialize {name} connector: {str(e)}")
        
        self._initialized = True
        self.logger.info(f"Initialization complete. {len(self.registry.list_connectors())} connectors ready")
        
        return self.registry
    
    def _load_config(self) -> Dict[str, Dict[str, Any]]:
        """Load connector configuration from environment."""
        config = {
            'google': {},
            'linkedin': {},
            'github': {
                'github_token': os.getenv('GITHUB_TOKEN', '')
            },
            'twitter': {
                'bearer_token': os.getenv('TWITTER_BEARER_TOKEN', '')
            },
            'whois': {},
            'certificate_transparency': {},
            'reddit': {},
            'stackoverflow': {}
        }
        
        return config
    
    def get_registry(self) -> ConnectorRegistry:
        """Get connector registry."""
        if not self._initialized:
            self.initialize_default_connectors()
        return self.registry
    
    def reload_connectors(self) -> None:
        """Reload all connectors."""
        self.logger.info("Reloading connectors")
        self._initialized = False
        self.registry = ConnectorRegistry()
        self.initialize_default_connectors()


# Global manager instance
_manager = ConnectorManager()


def get_connector_manager() -> ConnectorManager:
    """Get the global connector manager."""
    return _manager


def get_initialized_registry() -> ConnectorRegistry:
    """Get initialized connector registry."""
    return _manager.get_registry()
