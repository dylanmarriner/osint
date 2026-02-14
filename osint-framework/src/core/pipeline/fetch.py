"""
Fetch Manager for OSINT Investigation Pipeline

Purpose
- Execute search queries across multiple source connectors
- Manage rate limiting, retries, and error handling
- Cache results to prevent duplicate requests
- Provide comprehensive observability and security

Invariants
- All HTTP requests must include correlation IDs
- Rate limits are never exceeded for any connector
- Sensitive data is never logged or cached
- Every request is logged with structured telemetry
- Failed requests are retried with exponential backoff

Failure Modes
- Network timeout → request is retried with exponential backoff
- Rate limiting → request is queued and retried after reset time
- Connector unavailable → request fails gracefully with logged error
- Invalid response → response is logged and request is marked as failed
- Security validation failure → request is blocked and security event logged

Debug Notes
- Use correlation_id to trace requests through the entire pipeline
- Monitor fetch_duration_ms metrics for performance issues
- Check rate_limit_exceeded alerts for connector throttling
- Review security_validation_failed alerts for potential attacks
- Use request_cache_hit_ratio metrics to optimize caching strategy

Design Tradeoffs
- Chose aggressive retry with exponential backoff for reliability
- Tradeoff: Higher latency but better success rate for flaky services
- Mitigation: Maximum retry limits and timeout caps prevent excessive delays
- Review trigger: If average fetch duration exceeds 10 seconds, reduce retry attempts
"""

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..models.entities import SearchResult, redact_sensitive_data
from ...connectors.base import ConnectorRegistry, SourceConnector, ConnectorStatus


class FetchType(Enum):
    """Types of fetch operations."""
    SEARCH = "search"
    VALIDATION = "validation"
    HEALTH_CHECK = "health_check"


class FetchStatus(Enum):
    """Status of fetch operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class FetchRequest:
    """Individual fetch request with metadata."""
    request_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = ""
    connector_name: str = ""
    query_string: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    fetch_type: FetchType = FetchType.SEARCH
    priority: int = 2  # 1=high, 2=medium, 3=low
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: int = 30
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: FetchStatus = FetchStatus.PENDING
    error_message: Optional[str] = None
    results: List[SearchResult] = field(default_factory=list)

    def __post_init__(self):
        """Validate fetch request data."""
        if not self.connector_name:
            raise ValueError("Connector name cannot be empty")
        if not self.query_string.strip():
            raise ValueError("Query string cannot be empty")
        if self.priority not in [1, 2, 3]:
            raise ValueError("Priority must be 1, 2, or 3")
        if self.max_retries < 0 or self.max_retries > 10:
            raise ValueError("Max retries must be between 0 and 10")

    def get_request_hash(self) -> str:
        """Generate hash for request deduplication."""
        content = f"{self.connector_name}:{self.query_string}:{json.dumps(self.parameters, sort_keys=True)}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def can_retry(self) -> bool:
        """Check if request can be retried."""
        return self.retry_count < self.max_retries and self.status in [FetchStatus.FAILED]

    def get_retry_delay_seconds(self) -> int:
        """Calculate exponential backoff delay."""
        return min(300, (2 ** self.retry_count))  # Cap at 5 minutes

    def mark_started(self):
        """Mark request as started."""
        self.status = FetchStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()

    def mark_completed(self, results: List[SearchResult]):
        """Mark request as completed with results."""
        self.status = FetchStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.results = results

    def mark_failed(self, error_message: str):
        """Mark request as failed."""
        self.status = FetchStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "connector_name": self.connector_name,
            "query_string": redact_sensitive_data(self.query_string),
            "parameters": self.parameters,
            "fetch_type": self.fetch_type.value,
            "priority": self.priority,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": self.status.value,
            "error_message": self.error_message,
            "results_count": len(self.results)
        }


@dataclass
class FetchMetrics:
    """Metrics for fetch operations."""
    total_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    retry_count: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_duration_ms: int = 0
    connector_metrics: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def get_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.completed_requests / self.total_requests) * 100

    def get_cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio percentage."""
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return 0.0
        return (self.cache_hits / total_cache_requests) * 100

    def get_average_duration_ms(self) -> float:
        """Calculate average duration in milliseconds."""
        if self.completed_requests == 0:
            return 0.0
        return self.total_duration_ms / self.completed_requests

    def update_connector_metrics(self, connector_name: str, status: str, duration_ms: int):
        """Update metrics for a specific connector."""
        if connector_name not in self.connector_metrics:
            self.connector_metrics[connector_name] = {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "duration_ms": 0
            }
        
        self.connector_metrics[connector_name]["total"] += 1
        if status == "completed":
            self.connector_metrics[connector_name]["completed"] += 1
            self.connector_metrics[connector_name]["duration_ms"] += duration_ms
        elif status == "failed":
            self.connector_metrics[connector_name]["failed"] += 1


class FetchManager:
    """
    Core fetch manager for executing OSINT search queries.

    Purpose
    - Execute search queries across multiple connectors
    - Manage rate limiting, retries, and caching
    - Provide comprehensive observability and error handling

    Invariants
    - All requests include correlation IDs for tracing
    - Rate limits are never exceeded for any connector
    - Sensitive data is never logged or cached in plain text
    - Every request attempt is logged with structured telemetry
    - Failed requests are retried with exponential backoff

    Failure Modes
    - Connector unavailable → request fails gracefully with detailed logging
    - Rate limiting exceeded → request is queued and retried after reset
    - Network timeout → request is retried with exponential backoff
    - Invalid response → response is logged and request is marked failed
    - Security validation failure → request is blocked and security event logged

    Debug Notes
    - Use correlation_id to trace requests through the entire system
    - Monitor fetch_duration_ms metrics for performance issues
    - Check rate_limit_exceeded alerts for throttling issues
    - Review security_validation_failed alerts for potential attacks
    - Use request_cache_hit_ratio metrics to optimize caching

    Design Tradeoffs
    - Chose comprehensive retry logic for maximum reliability
    Tradeoff: Higher latency but better success rate for unreliable services
    - Mitigation: Maximum retry limits and timeout caps prevent excessive delays
    - Review trigger: If average fetch duration exceeds 10 seconds, reduce retry attempts
    """

    def __init__(self, connector_registry: ConnectorRegistry, cache_ttl_minutes: int = 60):
        """Initialize fetch manager with connector registry and cache settings."""
        self.connector_registry = connector_registry
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # In-memory cache for deduplication
        self.cache: Dict[str, Tuple[datetime, List[SearchResult]]] = {}
        self.cache_ttl_minutes = cache_ttl_minutes
        
        # Request queue and processing
        self.request_queue: asyncio.Queue = asyncio.Queue()
        self.active_requests: Dict[str, FetchRequest] = {}
        self.processing = False
        
        # Metrics
        self.metrics = FetchMetrics()
        
        # Rate limiting tracking
        self.rate_limit_tracker: Dict[str, datetime] = {}
        
        # Security settings
        self.max_concurrent_requests = 50
        self.max_request_size_kb = 1024  # 1MB max request size

    async def start_processing(self):
        """Start the fetch processing loop."""
        if self.processing:
            return
        
        self.processing = True
        self.logger.info("starting fetch processing loop")
        
        # Start processing tasks
        for i in range(5):  # 5 concurrent processing tasks
            asyncio.create_task(self._process_requests_loop(f"processor-{i}"))

    async def stop_processing(self):
        """Stop the fetch processing loop."""
        self.processing = False
        self.logger.info("stopping fetch processing loop")

    async def fetch_queries(self, queries: List[Dict[str, Any]], 
                          correlation_id: Optional[str] = None) -> Dict[str, List[SearchResult]]:
        """
        Execute multiple search queries across connectors.

        Summary
        - Queue fetch requests for all queries
        - Wait for completion or timeout
        - Return results grouped by connector

        Preconditions
        - queries must be valid search query dictionaries
        - correlation_id must be provided for tracing
        - fetch processing must be started

        Postconditions
        - All queries are attempted or marked as failed
        - Results are returned grouped by connector name
        - Metrics are updated for all operations

        Error cases
        - Invalid query format → request is rejected with ValidationError
        - Connector unavailable → query fails with logged error
        - Rate limiting exceeded → query is queued and retried

        Idempotency: Not idempotent - creates new requests each call
        Side effects: Updates cache, metrics, and connector state
        """
        start_time = datetime.utcnow()
        
        if not correlation_id:
            correlation_id = str(uuid4())
        
        logger = self.logger.child({
            "correlation_id": correlation_id,
            "op": "fetch.fetch_queries",
            "query_count": len(queries)
        })
        
        logger.info("starting batch fetch operation")

        try:
            # Validate and create fetch requests
            fetch_requests = []
            for query_data in queries:
                try:
                    request = self._create_fetch_request(query_data, correlation_id)
                    fetch_requests.append(request)
                except Exception as e:
                    logger.error("failed to create fetch request", {
                        "query_data": query_data,
                        "error": str(e)
                    })
                    continue

            # Queue requests
            for request in fetch_requests:
                await self.request_queue.put(request)
                self.metrics.total_requests += 1

            logger.info("queued fetch requests", {
                "request_count": len(fetch_requests)
            })

            # Wait for completion
            results = await self._wait_for_completion(fetch_requests, correlation_id)

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info("batch fetch operation completed", {
                "total_requests": len(fetch_requests),
                "successful_requests": sum(1 for r in fetch_requests if r.status == FetchStatus.COMPLETED),
                "failed_requests": sum(1 for r in fetch_requests if r.status == FetchStatus.FAILED),
                "duration_ms": duration_ms
            })

            return results

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error("batch fetch operation failed", {
                "error": str(e),
                "duration_ms": duration_ms
            })
            raise

    def _create_fetch_request(self, query_data: Dict[str, Any], correlation_id: str) -> FetchRequest:
        """Create a fetch request from query data."""
        connector_name = query_data.get("connector_name")
        query_string = query_data.get("query_string", "")
        parameters = query_data.get("parameters", {})
        priority = query_data.get("priority", 2)
        max_retries = query_data.get("max_retries", 3)
        timeout_seconds = query_data.get("timeout_seconds", 30)

        if not connector_name:
            raise ValueError("connector_name is required")
        if not query_string.strip():
            raise ValueError("query_string cannot be empty")

        # Security validation
        self._validate_request_security(query_string, parameters)

        return FetchRequest(
            correlation_id=correlation_id,
            connector_name=connector_name,
            query_string=query_string,
            parameters=parameters,
            priority=priority,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds
        )

    def _validate_request_security(self, query_string: str, parameters: Dict[str, Any]):
        """Validate request for security issues."""
        # Check request size
        total_size = len(query_string.encode('utf-8')) + len(json.dumps(parameters).encode('utf-8'))
        if total_size > self.max_request_size_kb * 1024:
            raise ValueError(f"Request too large: {total_size} bytes")

        # Check for suspicious patterns
        suspicious_patterns = [
            '<script',
            'javascript:',
            'data:',
            'vbscript:',
            'DROP TABLE',
            'DELETE FROM',
            'INSERT INTO',
            'UPDATE SET',
            'UNION SELECT'
        ]

        combined_content = f"{query_string} {json.dumps(parameters)}".upper()
        for pattern in suspicious_patterns:
            if pattern in combined_content:
                raise ValueError(f"Suspicious pattern detected: {pattern}")

    async def _wait_for_completion(self, requests: List[FetchRequest], 
                                  correlation_id: str, timeout_seconds: int = 300) -> Dict[str, List[SearchResult]]:
        """Wait for all requests to complete or timeout."""
        results = {}
        start_time = datetime.utcnow()
        
        while requests:
            completed_requests = [r for r in requests if r.status in [FetchStatus.COMPLETED, FetchStatus.FAILED]]
            failed_requests = [r for r in requests if r.status == FetchStatus.FAILED]
            
            # Update results
            for request in completed_requests:
                if request.connector_name not in results:
                    results[request.connector_name] = []
                results[request.connector_name].extend(request.results)
                requests.remove(request)

            # Check timeout
            if (datetime.utcnow() - start_time).total_seconds() > timeout_seconds:
                logger = self.logger.child({"correlation_id": correlation_id})
                logger.warning("fetch operation timed out", {
                    "remaining_requests": len(requests),
                    "timeout_seconds": timeout_seconds
                })
                break

            # Check rate limits and wait
            await asyncio.sleep(0.1)

        return results

    async def _process_requests_loop(self, processor_id: str):
        """Main processing loop for fetch requests."""
        logger = self.logger.child({
            "processor_id": processor_id,
            "op": "fetch.process_requests_loop"
        })
        
        logger.info("starting request processor")

        while self.processing:
            try:
                # Get request from queue
                try:
                    request = await asyncio.wait_for(self.request_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Check concurrent request limit
                if len(self.active_requests) >= self.max_concurrent_requests:
                    await self.request_queue.put(request)  # Re-queue
                    await asyncio.sleep(0.1)
                    continue

                # Process request
                asyncio.create_task(self._process_single_request(request, processor_id))

            except Exception as e:
                logger.error("error in processing loop", {
                    "error": str(e),
                    "active_requests": len(self.active_requests)
                })
                await asyncio.sleep(1.0)

        logger.info("request processor stopped")

    async def _process_single_request(self, request: FetchRequest, processor_id: str):
        """Process a single fetch request."""
        logger = self.logger.child({
            "correlation_id": request.correlation_id,
            "request_id": request.request_id,
            "processor_id": processor_id,
            "op": "fetch.process_single_request"
        })

        # Add to active requests
        self.active_requests[request.request_id] = request

        try:
            # Check cache first
            cache_key = request.get_request_hash()
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                request.mark_completed(cached_result)
                self.metrics.cache_hits += 1
                logger.debug("request served from cache", {
                    "connector": request.connector_name,
                    "cache_hit": True
                })
                return

            self.metrics.cache_misses += 1

            # Get connector
            connector = self.connector_registry.get_connector(request.connector_name)
            if not connector:
                request.mark_failed(f"Connector {request.connector_name} not found")
                self.metrics.failed_requests += 1
                logger.error("connector not found", {
                    "connector_name": request.connector_name
                })
                return

            # Check connector status
            if connector.status == ConnectorStatus.INACTIVE:
                request.mark_failed(f"Connector {request.connector_name} is inactive")
                self.metrics.failed_requests += 1
                logger.warning("connector is inactive", {
                    "connector_name": request.connector_name
                })
                return

            # Check rate limits
            if not connector.rate_limit.can_make_request():
                # Queue for later
                await asyncio.sleep(1.0)
                await self.request_queue.put(request)
                logger.debug("request queued due to rate limit", {
                    "connector_name": request.connector_name
                })
                return

            # Execute request
            await self._execute_request(request, connector, logger)

        except Exception as e:
            request.mark_failed(str(e))
            self.metrics.failed_requests += 1
            logger.error("unexpected error processing request", {
                "error": str(e),
                "connector_name": request.connector_name
            })

        finally:
            # Remove from active requests
            self.active_requests.pop(request.request_id, None)

    async def _execute_request(self, request: FetchRequest, connector: SourceConnector, logger):
        """Execute the actual fetch request."""
        start_time = datetime.utcnow()
        request.mark_started()

        logger.debug("executing fetch request", {
            "connector_name": request.connector_name,
            "query_string": redact_sensitive_data(request.query_string),
            "timeout_seconds": request.timeout_seconds
        })

        try:
            # Perform search with timeout
            results = await asyncio.wait_for(
                connector.search(request.query_string, request.parameters),
                timeout=request.timeout_seconds
            )

            # Validate results
            valid_results = []
            for result in results:
                if connector.validate_search_result(result):
                    valid_results.append(result)
                else:
                    logger.warning("invalid search result filtered", {
                        "result_url": result.url,
                        "connector_name": request.connector_name
                    })

            # Cache results
            cache_key = request.get_request_hash()
            self._add_to_cache(cache_key, valid_results)

            # Update metrics
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.metrics.completed_requests += 1
            self.metrics.total_duration_ms += duration_ms
            self.metrics.update_connector_metrics(request.connector_name, "completed", duration_ms)

            request.mark_completed(valid_results)

            logger.info("fetch request completed", {
                "connector_name": request.connector_name,
                "results_count": len(valid_results),
                "duration_ms": duration_ms,
                "retry_count": request.retry_count
            })

        except asyncio.TimeoutError:
            error_msg = f"Request timeout after {request.timeout_seconds} seconds"
            request.mark_failed(error_msg)
            self.metrics.failed_requests += 1
            self.metrics.update_connector_metrics(request.connector_name, "failed", 0)

            logger.warning("fetch request timed out", {
                "connector_name": request.connector_name,
                "timeout_seconds": request.timeout_seconds
            })

            # Retry if possible
            if request.can_retry():
                await self._schedule_retry(request, logger)

        except Exception as e:
            error_msg = str(e)
            request.mark_failed(error_msg)
            self.metrics.failed_requests += 1
            self.metrics.update_connector_metrics(request.connector_name, "failed", 0)

            logger.error("fetch request failed", {
                "connector_name": request.connector_name,
                "error": error_msg,
                "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000
            })

            # Retry if possible
            if request.can_retry():
                await self._schedule_retry(request, logger)

    async def _schedule_retry(self, request: FetchRequest, logger):
        """Schedule a retry for a failed request."""
        request.retry_count += 1
        request.status = FetchStatus.RETRYING
        self.metrics.retry_count += 1

        retry_delay = request.get_retry_delay_seconds()
        
        logger.info("scheduling request retry", {
            "request_id": request.request_id,
            "retry_count": request.retry_count,
            "max_retries": request.max_retries,
            "retry_delay_seconds": retry_delay
        })

        # Schedule retry
        await asyncio.sleep(retry_delay)
        await self.request_queue.put(request)

    def _get_from_cache(self, cache_key: str) -> Optional[List[SearchResult]]:
        """Get results from cache if available and not expired."""
        if cache_key not in self.cache:
            return None

        cached_time, results = self.cache[cache_key]
        if datetime.utcnow() - cached_time > timedelta(minutes=self.cache_ttl_minutes):
            del self.cache[cache_key]
            return None

        return results

    def _add_to_cache(self, cache_key: str, results: List[SearchResult]):
        """Add results to cache."""
        self.cache[cache_key] = (datetime.utcnow(), results)

        # Clean up expired cache entries
        self._cleanup_cache()

    def _cleanup_cache(self):
        """Remove expired cache entries."""
        expired_keys = []
        current_time = datetime.utcnow()

        for cache_key, (cached_time, _) in self.cache.items():
            if current_time - cached_time > timedelta(minutes=self.cache_ttl_minutes):
                expired_keys.append(cache_key)

        for key in expired_keys:
            del self.cache[key]

    def get_metrics(self) -> Dict[str, Any]:
        """Get current fetch metrics."""
        return {
            "total_requests": self.metrics.total_requests,
            "completed_requests": self.metrics.completed_requests,
            "failed_requests": self.metrics.failed_requests,
            "retry_count": self.metrics.retry_count,
            "cache_hits": self.metrics.cache_hits,
            "cache_misses": self.metrics.cache_misses,
            "cache_hit_ratio": self.metrics.get_cache_hit_ratio(),
            "success_rate": self.metrics.get_success_rate(),
            "average_duration_ms": self.metrics.get_average_duration_ms(),
            "active_requests": len(self.active_requests),
            "queued_requests": self.request_queue.qsize(),
            "connector_metrics": self.metrics.connector_metrics
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self.cache),
            "cache_ttl_minutes": self.cache_ttl_minutes,
            "cache_hits": self.metrics.cache_hits,
            "cache_misses": self.metrics.cache_misses,
            "cache_hit_ratio": self.metrics.get_cache_hit_ratio()
        }

    async def health_check(self) -> Dict[str, bool]:
        """Perform health check on fetch manager."""
        health_status = {
            "processing_active": self.processing,
            "queue_not_full": self.request_queue.qsize() < 1000,
            "active_requests reasonable": len(self.active_requests) < self.max_concurrent_requests,
            "cache_operational": len(self.cache) < 10000  # Reasonable cache size
        }
        
        return health_status
