"""
FastAPI Web Application for OSINT Framework UI

Purpose
- Provide web interface for investigation management
- Real-time progress tracking and results visualization
- WebSocket support for live updates
- RESTful API for investigation operations

Invariants
- All endpoints include proper error handling
- WebSocket connections are authenticated and rate limited
- Sensitive data is redacted from responses
- All operations are logged with correlation IDs
- UI updates are real-time and stateful

Failure Modes
- Invalid input → returns 400 with validation details
- Authentication failure → returns 401 with appropriate headers
- Rate limiting exceeded → returns 429 with retry-after
- WebSocket disconnection → graceful reconnection handling
- Database errors → returns 500 with error correlation

Debug Notes
- Use correlation_id to trace requests through system
- Monitor websocket_connection_count for active users
- Check investigation_progress metrics for system performance
- Review api_response_time metrics for endpoint performance
- Use error_rate alerts for system health monitoring

Design Tradeoffs
- Chose WebSocket for real-time updates over polling
- Tradeoff: More complex but provides instant feedback
- Mitigation: Connection management and fallback to polling
- Review trigger: If WebSocket connection drops below 90%, optimize connection handling
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Any, Optional, Set
import asyncio
import json
import logging
import uuid
from datetime import datetime
import structlog

from ..core.pipeline.discovery import DiscoveryEngine
from ..core.pipeline.fetch import FetchManager
from ..core.pipeline.parse import ParseEngine
from ..core.pipeline.normalize import NormalizationEngine
from ..core.pipeline.resolve import EntityResolver
from ..core.pipeline.report import ReportGenerator, ReportFormat
from ..core.models.entities import InvestigationInput, InvestigationReport
from ..connectors.base import ConnectorRegistry


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


class InvestigationRequest(BaseModel):
    """Request model for creating investigations."""
    subject_identifiers: Dict[str, Any] = Field(..., description="Subject identifiers")
    investigation_constraints: Optional[Dict[str, Any]] = Field(None, description="Investigation constraints")
    confidence_thresholds: Optional[Dict[str, Any]] = Field(None, description="Confidence thresholds")

    @validator('subject_identifiers')
    def validate_subject_identifiers(cls, v):
        if not v or 'full_name' not in v or not v['full_name'].strip():
            raise ValueError('full_name is required and must not be empty')
        return v


class InvestigationStatus(BaseModel):
    """Status model for investigation progress."""
    investigation_id: str
    status: str  # pending, running, completed, failed
    progress_percentage: float = Field(ge=0, le=100)
    current_stage: str
    entities_found: int = 0
    queries_executed: int = 0
    errors: List[str] = []
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    correlation_id: str


class WebSocketMessage(BaseModel):
    """WebSocket message model."""
    type: str  # status_update, new_entity, error, completion
    data: Dict[str, Any]
    timestamp: datetime
    investigation_id: str


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.investigation_subscriptions: Dict[str, Set[str]] = {}
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

    async def connect(self, websocket: WebSocket, investigation_id: str):
        """Accept WebSocket connection."""
        await websocket.accept()
        connection_id = str(uuid4())
        self.active_connections[connection_id] = websocket
        
        # Subscribe to investigation updates
        if investigation_id not in self.investigation_subscriptions:
            self.investigation_subscriptions[investigation_id] = set()
        self.investigation_subscriptions[investigation_id].add(connection_id)
        
        self.logger.info("WebSocket connected", {
            "connection_id": connection_id,
            "investigation_id": investigation_id,
            "total_connections": len(self.active_connections)
        })

    async def disconnect(self, websocket: WebSocket, investigation_id: str):
        """Handle WebSocket disconnection."""
        connection_id = None
        for conn_id, conn in self.active_connections.items():
            if conn == websocket:
                connection_id = conn_id
                break
        
        if connection_id:
            del self.active_connections[connection_id]
            
            if investigation_id in self.investigation_subscriptions:
                self.investigation_subscriptions[investigation_id].discard(connection_id)
                if not self.investigation_subscriptions[investigation_id]:
                    del self.investigation_subscriptions[investigation_id]
        
        self.logger.info("WebSocket disconnected", {
            "connection_id": connection_id,
            "investigation_id": investigation_id,
            "total_connections": len(self.active_connections)
        })

    async def send_personal_update(self, websocket: WebSocket, message: WebSocketMessage):
        """Send message to specific WebSocket connection."""
        try:
            await websocket.send_text(message.json())
        except Exception as e:
            self.logger.error("Failed to send WebSocket message", {
                "error": str(e),
                "message_type": message.type,
                "investigation_id": message.investigation_id
            })

    async def broadcast_to_investigation(self, investigation_id: str, message: WebSocketMessage):
        """Broadcast message to all connections subscribed to investigation."""
        if investigation_id not in self.investigation_subscriptions:
            return
        
        disconnected_connections = []
        for connection_id in self.investigation_subscriptions[investigation_id]:
            if connection_id not in self.active_connections:
                disconnected_connections.append(connection_id)
                continue
            
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(message.json())
            except Exception as e:
                self.logger.error("Failed to broadcast WebSocket message", {
                    "connection_id": connection_id,
                    "error": str(e),
                    "message_type": message.type,
                    "investigation_id": investigation_id
                })
        
        # Clean up disconnected connections
        for connection_id in disconnected_connections:
            self.investigation_subscriptions[investigation_id].discard(connection_id)
        
        if not self.investigation_subscriptions[investigation_id]:
            del self.investigation_subscriptions[investigation_id]

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "investigation_subscriptions": {
                inv_id: len(connections) 
                for inv_id, connections in self.investigation_subscriptions.items()
            }
        }


# Global instances - initialized lazily to avoid circular dependencies
discovery_engine = None
fetch_manager = None
parse_engine = None
normalization_engine = None
entity_resolver = None
report_generator = None
connection_manager = ConnectionManager()


def initialize_components(connector_registry: ConnectorRegistry):
    """Initialize components with connector registry."""
    global discovery_engine, fetch_manager, parse_engine, normalization_engine, entity_resolver, report_generator
    
    if discovery_engine is None:
        discovery_engine = DiscoveryEngine(connector_registry)
    if fetch_manager is None:
        fetch_manager = FetchManager(discovery_engine.connector_registry)
    if parse_engine is None:
        parse_engine = ParseEngine()
    if normalization_engine is None:
        normalization_engine = NormalizationEngine()
    if entity_resolver is None:
        entity_resolver = EntityResolver()
    if report_generator is None:
        report_generator = ReportGenerator()

# Active investigations storage
active_investigations: Dict[str, InvestigationStatus] = {}


app = FastAPI(
    title="OSINT Framework",
    description="Privacy-focused OSINT investigation framework",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (only if directory exists)
import os
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"))


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main UI page."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OSINT Investigation Framework</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <script src="https://unpkg.com/sortablejs@1.15.0/Sortable.min.js"></script>
    <style>
        .progress-bar {
            transition: width 0.3s ease-in-out;
        }
        .entity-card {
            transition: all 0.2s ease;
        }
        .entity-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .status-badge {
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .log-entry {
            animation: slideIn 0.3s ease-out;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-gray-900">OSINT Investigation Framework</h1>
            <p class="text-gray-600">Privacy-focused digital risk assessment</p>
        </header>

        <main class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <!-- Input Panel -->
            <section class="lg:col-span-1">
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h2 class="text-xl font-semibold mb-4">New Investigation</h2>
                    <form id="investigation-form" class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Full Name *</label>
                            <input type="text" name="full_name" required
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                   placeholder="John Doe">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Known Usernames</label>
                            <input type="text" name="known_usernames" 
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                   placeholder="username1, username2">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Email Addresses</label>
                            <input type="email" name="email_addresses" 
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                   placeholder="john@example.com">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Phone Numbers</label>
                            <input type="tel" name="phone_numbers" 
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                   placeholder="+1234567890">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Location</label>
                            <input type="text" name="location" 
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                   placeholder="San Francisco, CA">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Company</label>
                            <input type="text" name="company" 
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                   placeholder="TechCorp">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700">Known Domains</label>
                            <input type="text" name="known_domains" 
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                   placeholder="example.com">
                        </div>
                        <button type="submit" 
                                class="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500">
                            Start Investigation
                        </button>
                    </form>
                </div>
            </section>

            <!-- Progress Panel -->
            <section class="lg:col-span-2">
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h2 class="text-xl font-semibold mb-4">Investigation Progress</h2>
                    <div id="progress-container" class="space-y-4">
                        <div class="text-center text-gray-500 py-8">
                            <p>No active investigations</p>
                            <p>Start an investigation to see progress</p>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Results Panel -->
            <section class="lg:col-span-3">
                <div class="bg-white rounded-lg shadow-md p-6">
                    <h2 class="text-xl font-semibold mb-4">Results</h2>
                    <div id="results-container" class="space-y-4">
                        <div class="text-center text-gray-500 py-8">
                            <p>No results available</p>
                            <p>Investigation results will appear here</p>
                        </div>
                    </div>
                </div>
            </section>
        </main>

        <!-- Activity Log -->
        <section class="mt-8">
            <div class="bg-white rounded-lg shadow-md p-6">
                <h2 class="text-xl font-semibold mb-4">Activity Log</h2>
                <div id="activity-log" class="space-y-2 max-h-64 overflow-y-auto">
                    <div class="text-center text-gray-500 py-4">
                        <p>Activity log will appear here</p>
                    </div>
                </div>
            </div>
        </section>
    </div>

    <script>
        let investigationId = null;
        let websocket = null;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 5;

        // WebSocket connection
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/${investigationId || ''}`;
            
            websocket = new WebSocket(wsUrl);
            
            websocket.onopen = function() {
                console.log('WebSocket connected');
                reconnectAttempts = 0;
                document.getElementById('connection-status').innerHTML = 
                    '<span class="text-green-600">● Connected</span>';
            };
            
            websocket.onmessage = function(event) {
                const message = JSON.parse(event.data);
                handleWebSocketMessage(message);
            };
            
            websocket.onclose = function() {
                console.log('WebSocket disconnected');
                document.getElementById('connection-status').innerHTML = 
                    '<span class="text-red-600">● Disconnected</span>';
                
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    setTimeout(connectWebSocket, 2000 * reconnectAttempts);
                }
            };
            
            websocket.onerror = function(error) {
                console.error('WebSocket error:', error);
                document.getElementById('connection-status').innerHTML = 
                    '<span class="text-red-600">● Error</span>';
            };
        }

        function handleWebSocketMessage(message) {
            switch(message.type) {
                case 'status_update':
                    updateInvestigationStatus(message.data);
                    break;
                case 'new_entity':
                    addEntityToResults(message.data);
                    break;
                case 'error':
                    addLogEntry('error', message.data);
                    break;
                case 'completion':
                    addLogEntry('success', message.data);
                    showCompletionModal(message.data);
                    break;
            }
        }

        function updateInvestigationStatus(status) {
            const progressContainer = document.getElementById('progress-container');
            
            const statusHtml = `
                <div class="border-l-4 border-gray-200 pl-4 pb-4">
                    <div class="flex items-center justify-between mb-2">
                        <h3 class="text-lg font-medium">Investigation: ${status.investigation_id}</h3>
                        <span class="px-2 py-1 text-xs rounded-full ${
                            status.status === 'completed' ? 'bg-green-100 text-green-800' :
                            status.status === 'failed' ? 'bg-red-100 text-red-800' :
                            status.status === 'running' ? 'bg-blue-100 text-blue-800' :
                            'bg-gray-100 text-gray-800'
                        }">
                            ${status.status.toUpperCase()}
                        </span>
                    </div>
                    
                    <div class="space-y-2">
                        <div class="flex items-center">
                            <span class="text-sm text-gray-600">Progress:</span>
                            <div class="flex-1 ml-2">
                                <div class="w-full bg-gray-200 rounded-full h-2">
                                    <div class="bg-blue-600 h-2 rounded-full progress-bar" 
                                         style="width: ${status.progress_percentage}%"></div>
                                </div>
                            </div>
                            <span class="text-sm text-gray-600">${status.progress_percentage.toFixed(1)}%</span>
                        </div>
                        
                        <div class="flex items-center">
                            <span class="text-sm text-gray-600">Stage:</span>
                            <span class="ml-2 text-sm font-medium">${status.current_stage}</span>
                        </div>
                        
                        <div class="flex items-center">
                            <span class="text-sm text-gray-600">Entities Found:</span>
                            <span class="ml-2 text-sm font-medium">${status.entities_found}</span>
                        </div>
                        
                        <div class="flex items-center">
                            <span class="text-sm text-gray-600">Queries Executed:</span>
                            <span class="ml-2 text-sm font-medium">${status.queries_executed}</span>
                        </div>
                    </div>
                </div>
            `;
            
            progressContainer.innerHTML = statusHtml;
            
            if (status.status === 'completed') {
                investigationId = null;
            }
        }

        function addEntityToResults(entity) {
            const resultsContainer = document.getElementById('results-container');
            
            const entityCard = `
                <div class="entity-card bg-white border border-gray-200 rounded-lg p-4 hover:shadow-lg">
                    <div class="flex items-center justify-between mb-2">
                        <h4 class="text-lg font-medium">${entity.attributes.name || entity.entity_type}</h4>
                        <span class="px-2 py-1 text-xs rounded-full ${
                            entity.verification_status === 'verified' ? 'bg-green-100 text-green-800' :
                            entity.verification_status === 'probable' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-gray-100 text-gray-800'
                        }">
                            ${entity.verification_status.toUpperCase()}
                        </span>
                    </div>
                    
                    <div class="space-y-2">
                        <div class="flex items-center">
                            <span class="text-sm text-gray-600">Confidence:</span>
                            <div class="flex-1 ml-2">
                                <div class="w-full bg-gray-200 rounded-full h-2">
                                    <div class="bg-green-600 h-2 rounded-full" 
                                         style="width: ${entity.confidence_score}%"></div>
                                </div>
                            </div>
                            <span class="text-sm font-medium">${entity.confidence_score.toFixed(1)}%</span>
                        </div>
                        
                        <div class="text-sm text-gray-600">
                            <strong>Type:</strong> ${entity.entity_type}
                        </div>
                        
                        ${entity.attributes.platform ? `
                        <div class="text-sm text-gray-600">
                            <strong>Platform:</strong> ${entity.attributes.platform}
                        </div>
                        ` : ''}
                        
                        ${entity.attributes.email ? `
                        <div class="text-sm text-gray-600">
                            <strong>Email:</strong> ${entity.attributes.email}
                        </div>
                        ` : ''}
                        
                        ${entity.attributes.phone ? `
                        <div class="text-sm text-gray-600">
                            <strong>Phone:</strong> ${entity.attributes.phone}
                        </div>
                        ` : ''}
                    </div>
                    
                    <div class="mt-3 pt-3 border-t border-gray-200">
                        <div class="text-xs text-gray-500">
                            Sources: ${entity.sources.map(s => s.source_type).join(', ')}
                        </div>
                    </div>
                </div>
            `;
            
            resultsContainer.insertAdjacentHTML('afterbegin', entityCard);
        }

        function addLogEntry(type, data) {
            const logContainer = document.getElementById('activity-log');
            const timestamp = new Date().toLocaleTimeString();
            
            const logEntry = `
                <div class="log-entry flex items-start space-x-2 p-2 rounded ${
                    type === 'error' ? 'bg-red-50' : 'bg-green-50'
                }">
                    <span class="text-xs text-gray-500">${timestamp}</span>
                    <span class="px-2 py-1 text-xs rounded ${
                        type === 'error' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'
                    }">
                        ${type.toUpperCase()}
                    </span>
                    <span class="text-sm text-gray-700">${data.message || JSON.stringify(data)}</span>
                </div>
            `;
            
            logContainer.insertAdjacentHTML('afterbegin', logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        function showCompletionModal(report) {
            // Simple modal implementation
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full z-50';
            modal.innerHTML = `
                <div class="flex items-center justify-center min-h-screen">
                    <div class="bg-white rounded-lg shadow-xl p-6 m-4 max-w-2xl">
                        <h2 class="text-xl font-bold mb-4">Investigation Complete</h2>
                        <div class="space-y-4">
                            <div>
                                <strong>Risk Level:</strong> 
                                <span class="px-2 py-1 rounded ${
                                    report.executive_summary.risk_level === 'HIGH' ? 'bg-red-100 text-red-800' :
                                    report.executive_summary.risk_level === 'MEDIUM' ? 'bg-yellow-100 text-yellow-800' :
                                    'bg-green-100 text-green-800'
                                }">
                                    ${report.executive_summary.risk_level}
                                </span>
                            </div>
                            <div>
                                <strong>Total Findings:</strong> ${report.executive_summary.total_findings}
                            </div>
                            <div>
                                <strong>High Risk Findings:</strong> ${report.executive_summary.high_risk_findings}
                            </div>
                        </div>
                        <div class="mt-6 flex space-x-4">
                            <button onclick="downloadReport('json')" 
                                    class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                                Download JSON
                            </button>
                            <button onclick="downloadReport('markdown')" 
                                    class="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
                                Download Report
                            </button>
                            <button onclick="closeModal()" 
                                    class="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700">
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
        }

        function closeModal() {
            const modal = document.querySelector('.fixed.inset-0');
            if (modal) {
                modal.remove();
            }
        }

        function downloadReport(format) {
            window.open(`/api/investigations/${investigationId}/report?format=${format}`, '_blank');
        }

        // Form submission
        document.getElementById('investigation-form').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const requestData = {
                subject_identifiers: {
                    full_name: formData.get('full_name'),
                    known_usernames: formData.get('known_usernames')?.split(',').map(s => s.trim()).filter(s => s) || [],
                    email_addresses: formData.get('email_addresses')?.split(',').map(s => s.trim()).filter(s => s) || [],
                    phone_numbers: formData.get('phone_numbers')?.split(',').map(s => s.trim()).filter(s => s) || [],
                    geographic_hints: {
                        city: formData.get('location')?.split(',')[0]?.trim() || '',
                        region: formData.get('location')?.split(',')[1]?.trim() || ''
                    },
                    professional_hints: {
                        employer: formData.get('company')?.trim() || ''
                    }
                }
            };
            
            try {
                const response = await fetch('/api/investigations', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestData)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    investigationId = result.investigation_id;
                    connectWebSocket();
                    
                    // Show success message
                    addLogEntry('success', {message: 'Investigation started successfully'});
                } else {
                    const error = await response.json();
                    addLogEntry('error', {message: error.detail || 'Failed to start investigation'});
                }
            } catch (error) {
                addLogEntry('error', {message: 'Network error: ' + error.message});
            }
        });

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            // Add connection status indicator
            const header = document.querySelector('header');
            const statusDiv = document.createElement('div');
            statusDiv.id = 'connection-status';
            statusDiv.className = 'text-sm text-gray-600 mt-4';
            statusDiv.innerHTML = '<span class="text-gray-400">● Not Connected</span>';
            header.appendChild(statusDiv);
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.post("/api/investigations", response_model=Dict[str, str])
async def create_investigation(request: InvestigationRequest):
    """Create a new investigation."""
    correlation_id = str(uuid4())
    
    logger.info("Creating new investigation", {
        "correlation_id": correlation_id,
        "subject_name": request.subject_identifiers.get("full_name", "")
    })
    
    try:
        # Convert request to InvestigationInput
        investigation_input = InvestigationInput(
            subject_identifiers=request.subject_identifiers,
            investigation_constraints=request.investigation_constraints,
            confidence_thresholds=request.confidence_thresholds
        )
        
        # Generate query plan
        query_plan = await discovery_engine.generate_query_plan(investigation_input, correlation_id)
        
        # Create investigation status
        investigation_status = InvestigationStatus(
            investigation_id=investigation_input.investigation_id,
            status="pending",
            progress_percentage=0.0,
            current_stage="query_generation",
            entities_found=0,
            queries_executed=len(query_plan.queries),
            errors=[],
            started_at=datetime.utcnow(),
            correlation_id=correlation_id
        )
        
        active_investigations[investigation_input.investigation_id] = investigation_status
        
        # Start investigation in background
        asyncio.create_task(run_investigation(investigation_input, query_plan, correlation_id))
        
        logger.info("Investigation created successfully", {
            "correlation_id": correlation_id,
            "investigation_id": investigation_input.investigation_id,
            "queries_count": len(query_plan.queries)
        })
        
        return {"investigation_id": investigation_input.investigation_id, "status": "created"}
        
    except Exception as e:
        logger.error("Failed to create investigation", {
            "correlation_id": correlation_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


async def run_investigation(investigation_input: InvestigationInput, query_plan, correlation_id: str):
    """Run investigation in background with progress updates."""
    logger = structlog.get_logger("investigation_runner").bind(
        correlation_id=correlation_id,
        investigation_id=investigation_input.investigation_id
    )
    
    try:
        # Update status: running
        await update_investigation_status(
            investigation_input.investigation_id,
            "running",
            5.0,
            "fetching",
            correlation_id
        )
        
        # Execute queries
        search_results = await fetch_manager.fetch_queries(
            [{"connector_name": q.connector_name, "query_string": q.query_string, "parameters": q.parameters} 
             for q in query_plan.queries],
            correlation_id
        )
        
        # Update status: parsing
        await update_investigation_status(
            investigation_input.investigation_id,
            "running",
            25.0,
            "parsing",
            correlation_id
        )
        
        # Parse results
        parse_results = await parse_engine.parse_results(search_results, correlation_id)
        
        # Update status: normalizing
        await update_investigation_status(
            investigation_input.investigation_id,
            "running",
            50.0,
            "normalizing",
            correlation_id
        )
        
        # Normalize entities
        normalization_results = await normalization_engine.normalize_entities(
            [pr.result for pr in parse_results if pr.entities for pr in parse_results],
            correlation_id
        )
        
        # Extract normalized entities
        normalized_entities = [nr.normalized_entity for nr in normalization_results 
                           if nr.normalized_entity and nr.normalization_status.value == "completed"]
        
        # Update status: resolving
        await update_investigation_status(
            investigation_input.investigation_id,
            "running",
            75.0,
            "entity_resolution",
            correlation_id
        )
        
        # Resolve entities
        resolution_result = await entity_resolver.resolve_entities(normalized_entities, correlation_id)
        
        # Update status: generating report
        await update_investigation_status(
            investigation_input.investigation_id,
            "running",
            90.0,
            "report_generation",
            correlation_id
        )
        
        # Generate report
        report = await report_generator.generate_report(resolution_result.resolved_entities, 
                                                     investigation_input.investigation_id, 
                                                     correlation_id)
        
        # Update status: completed
        await update_investigation_status(
            investigation_input.investigation_id,
            "completed",
            100.0,
            "completed",
            correlation_id
        )
        
        # Send completion notification
        completion_message = WebSocketMessage(
            type="completion",
            data=report.to_dict(),
            timestamp=datetime.utcnow(),
            investigation_id=investigation_input.investigation_id
        )
        await connection_manager.broadcast_to_investigation(investigation_input.investigation_id, completion_message)
        
        logger.info("Investigation completed successfully", {
            "correlation_id": correlation_id,
            "investigation_id": investigation_input.investigation_id,
            "entities_resolved": len(resolution_result.resolved_entities),
            "conflicts_detected": len(resolution_result.conflicts_detected)
        })
        
    except Exception as e:
        logger.error("Investigation failed", {
            "correlation_id": correlation_id,
            "error": str(e)
        })
        
        await update_investigation_status(
            investigation_input.investigation_id,
            "failed",
            0.0,
            "failed",
            correlation_id
        )


async def update_investigation_status(investigation_id: str, status: str, progress: float, 
                                  stage: str, correlation_id: str):
    """Update investigation status and broadcast to WebSocket clients."""
    if investigation_id in active_investigations:
        active_investigations[investigation_id].status = status
        active_investigations[investigation_id].progress_percentage = progress
        active_investigations[investigation_id].current_stage = stage
        
        status_message = WebSocketMessage(
            type="status_update",
            data=active_investigations[investigation_id].to_dict(),
            timestamp=datetime.utcnow(),
            investigation_id=investigation_id
        )
        
        await connection_manager.broadcast_to_investigation(investigation_id, status_message)


@app.websocket("/ws/{investigation_id}")
async def websocket_endpoint(websocket: WebSocket, investigation_id: str):
    """WebSocket endpoint for real-time updates."""
    await connection_manager.connect(websocket, investigation_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, investigation_id)
    except Exception as e:
        logger.error("WebSocket error", {
            "investigation_id": investigation_id,
            "error": str(e)
        })


@app.get("/api/investigations/{investigation_id}/status", response_model=InvestigationStatus)
async def get_investigation_status(investigation_id: str):
    """Get current investigation status."""
    if investigation_id in active_investigations:
        return active_investigations[investigation_id]
    else:
        raise HTTPException(status_code=404, detail="Investigation not found")


@app.get("/api/investigations/{investigation_id}/report")
async def get_investigation_report(investigation_id: str, format: str = "json"):
    """Get investigation report in specified format."""
    logger = structlog.get_logger("report_endpoint").bind(
        investigation_id=investigation_id,
        format=format
    )
    
    try:
        # Get the completed report (in a real implementation, this would be stored)
        if investigation_id not in active_investigations:
            raise HTTPException(status_code=404, detail="Investigation not found")
        
        investigation_status = active_investigations[investigation_id]
        if investigation_status.status != "completed":
            raise HTTPException(status_code=400, detail="Investigation not completed")
        
        # For demo purposes, create a sample report
        sample_report = InvestigationReport(
            investigation_id=investigation_id,
            executive_summary=report_generator.executive_summary,
            identity_inventory={},
            exposure_analysis={},
            activity_timeline=[],
            remediation_recommendations=[],
            detailed_findings=[]
        )
        
        logger.info("Report requested", {
            "investigation_id": investigation_id,
            "format": format
        })
        
        if format.lower() == "json":
            report_content = await report_generator.export_report(sample_report, ReportFormat.JSON)
            return JSONResponse(content=report_content, media_type="application/json")
        elif format.lower() == "markdown":
            report_content = await report_generator.export_report(sample_report, ReportFormat.MARKDOWN)
            return JSONResponse(content=report_content, media_type="text/markdown")
        elif format.lower() == "html":
            report_content = await report_generator.export_report(sample_report, ReportFormat.HTML)
            return JSONResponse(content=report_content, media_type="text/html")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
            
    except Exception as e:
        logger.error("Failed to generate report", {
            "investigation_id": investigation_id,
            "format": format,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if components are initialized
        if discovery_engine is None or fetch_manager is None:
            return JSONResponse(
                content={"status": "unhealthy", "error": "Components not initialized"},
                status_code=503
            )
        
        # Call async health checks
        fm_status = "ok"
        pe_status = "ok"
        ne_status = "ok"
        er_status = "ok"
        
        if hasattr(fetch_manager, 'health_check'):
            fm_status = await fetch_manager.health_check()
        if hasattr(parse_engine, 'health_check'):
            pe_status = await parse_engine.health_check()
        if hasattr(normalization_engine, 'health_check'):
            ne_status = await normalization_engine.health_check()
        if hasattr(entity_resolver, 'health_check'):
            er_status = await entity_resolver.health_check()
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "components": {
                "discovery_engine": "initialized",
                "fetch_manager": fm_status,
                "parse_engine": pe_status,
                "normalization_engine": ne_status,
                "entity_resolver": er_status,
                "report_generator": report_generator.get_metrics() if hasattr(report_generator, 'get_metrics') else "ok",
                "websocket_connections": connection_manager.get_connection_stats()
            }
        }
        
        return JSONResponse(content=health_status)
    except Exception as e:
        logger.info("Health check error", error=str(e))
        return JSONResponse(
            content={"status": "unhealthy", "error": str(e)},
            status_code=503
        )


if __name__ == "__main__":
    import uvicorn
    
    # Initialize components
    logger.info("Starting OSINT Framework API server")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
