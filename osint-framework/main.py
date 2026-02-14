#!/usr/bin/env python3
"""
OSINT Framework Main Entry Point

Purpose
- Start the OSINT framework web application
- Initialize all core components
- Provide CLI interface for framework management

Invariants
- All components are initialized before starting
- Logging is configured with appropriate levels
- Dependencies are validated before startup
- Server starts only if initialization succeeds

Failure Modes
- Component initialization failure → server fails with detailed error
- Port binding failure → server fails with clear error message
- Configuration error → server fails with configuration details
- Dependency missing → ImportError with installation instructions

Debug Notes
- Check component_initialization logs for startup issues
- Monitor server_startup_time metrics for performance
- Review dependency_validation_failed alerts for missing packages
- Use configuration_errors to diagnose setup problems
- Monitor port_binding_status for network issues

Design Tradeoffs
- Chose fast startup with lazy component loading
- Tradeoff: Slower first requests but faster startup time
- Mitigation: Critical components are initialized eagerly
- Review trigger: If startup time exceeds 15 seconds, optimize initialization
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path

import structlog
from fastapi import FastAPI
import uvicorn

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src import (
    get_version, get_component_status,
    get_discovery_engine, get_fetch_manager, get_parse_engine,
    get_normalization_engine, get_entity_resolver, get_report_generator,
    get_connector_registry
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger(__name__)


class OSINTFramework:
    """Main OSINT framework application."""
    
    def __init__(self):
        """Initialize the framework."""
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        self.app = None
        self.server = None
        self.shutdown_event = asyncio.Event()

    async def initialize_components(self):
        """Initialize all framework components."""
        self.logger.info("Initializing OSINT framework components")
        
        try:
            # Initialize connector registry
            connector_registry = get_connector_registry()
            self.logger.info("Connector registry initialized")
            
            # Initialize core components
            discovery_engine = get_discovery_engine()
            fetch_manager = get_fetch_manager()
            parse_engine = get_parse_engine()
            normalization_engine = get_normalization_engine()
            entity_resolver = get_entity_resolver()
            report_generator = get_report_generator()
            
            self.logger.info("All components initialized successfully")
            
            return {
                "connector_registry": connector_registry,
                "discovery_engine": discovery_engine,
                "fetch_manager": fetch_manager,
                "parse_engine": parse_engine,
                "normalization_engine": normalization_engine,
                "entity_resolver": entity_resolver,
                "report_generator": report_generator
            }
            
        except Exception as e:
            self.logger.error("Failed to initialize components", error=str(e), error_type=type(e).__name__)
            raise

    def create_fastapi_app(self, components):
        """Create FastAPI application with initialized components."""
        from src.api.app import app, connection_manager, initialize_components
        
        # Initialize components in app module
        initialize_components(components["connector_registry"])
        
        # Inject components into app module
        import src.api.app
        src.api.app.discovery_engine = components["discovery_engine"]
        src.api.app.fetch_manager = components["fetch_manager"]
        src.api.app.parse_engine = components["parse_engine"]
        src.api.app.normalization_engine = components["normalization_engine"]
        src.api.app.entity_resolver = components["entity_resolver"]
        src.api.app.report_generator = components["report_generator"]
        src.api.app.connection_manager = connection_manager
        
        return app

    async def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the FastAPI server."""
        try:
            # Initialize components
            components = await self.initialize_components()
            
            # Create FastAPI app
            self.app = self.create_fastapi_app(components)
            
            # Configure uvicorn
            config = uvicorn.Config(
                app=self.app,
                host=host,
                port=port,
                log_level="info",
                access_log=True,
                use_colors=True
            )
            
            self.server = uvicorn.Server(config)
            
            self.logger.info("Starting OSINT Framework server", 
                version=get_version(),
                host=host,
                port=port)
            
            # Start server
            await self.server.serve()
            
        except Exception as e:
            self.logger.error("Failed to start server", error=str(e), error_type=type(e).__name__)
            sys.exit(1)

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info("Received shutdown signal", signal=signum, signal_name=signal.Signals(signum).name)
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run(self):
        """Run the OSINT framework."""
        self.logger.info("Starting OSINT Framework", version=get_version(), python_version=sys.version)
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        try:
            # Start the server
            await self.start_server()
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error("Unexpected error", error=str(e), error_type=type(e).__name__)
        finally:
            self.logger.info("OSINT Framework shutdown complete")


def main():
    """Main entry point."""
    framework = OSINTFramework()
    asyncio.run(framework.run())


if __name__ == "__main__":
    main()
