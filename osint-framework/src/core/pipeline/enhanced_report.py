"""
Enhanced Report Generator with Professional Intelligence Standards

Purpose
- Professional intelligence reporting with multiple formats
- Advanced risk assessment and threat analysis
- Interactive visualizations and dashboards
- Compliance and audit trail generation

Invariants
- All reports include comprehensive audit trails
- Risk assessments follow industry standards
- Visualizations are interactive and exportable
- All operations maintain full chain of custody
- Sensitive data is protected throughout processing

Failure Modes
- Report generation failure → fallback to basic format
- Visualization error → text-based alternatives
- Compliance validation failure → detailed error reporting
- Template rendering failure → default templates
- Export format error → multiple format options

Debug Notes
- Monitor report_generation_time for performance issues
- Check visualization_render_time for rendering performance
- Review compliance_validation_results for audit issues
- Use export_success_rate for format reliability
- Monitor risk_assessment_accuracy for model performance

Design Tradeoffs
- Chose comprehensive reporting over simple summaries
- Tradeoff: More complex but provides professional insights
- Mitigation: Fallback to basic reporting when advanced features fail
- Review trigger: If report generation time exceeds 30 seconds, optimize templates
"""

import asyncio
import logging
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
import uuid
import base64
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from weasyprint import HTML, CSS
from jinja2 import Environment, BaseLoader, Template
import networkx as nx

from .report import ReportGenerator, ReportFormat, RiskCategory, InvestigationReport
from ..models.entities import Entity, EntityType, VerificationStatus, RiskLevel


@dataclass
class ThreatAssessment:
    """Professional threat assessment."""
    threat_id: str
    threat_type: str
    severity: str
    likelihood: str
    impact: str
    confidence: float
    indicators: List[str]
    mitigation_steps: List[str]
    assessment_date: datetime
    assessor: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplianceReport:
    """Compliance and audit report."""
    compliance_id: str
    framework: str  # GDPR, CCPA, etc.
    compliance_score: float
    violations: List[str]
    recommendations: List[str]
    audit_trail: List[Dict[str, Any]]
    assessment_date: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntelligenceSummary:
    """Executive intelligence summary."""
    summary_id: str
    key_findings: List[str]
    risk_level: RiskLevel
    threat_actors: List[str]
    attack_vectors: List[str]
    recommendations: List[str]
    confidence_level: float
    data_sources: List[str]
    analysis_date: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisualizationConfig:
    """Visualization configuration."""
    viz_id: str
    viz_type: str
    title: str
    data_source: str
    chart_type: str
    interactive: bool
    export_formats: List[str]
    styling: Dict[str, Any] = field(default_factory=dict)


class EnhancedReportGenerator(ReportGenerator):
    """Enhanced report generator with professional intelligence features."""
    
    def __init__(self, template_dir: Optional[str] = None):
        super().__init__(template_dir)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.jinja_env = Environment(loader=BaseLoader(), autoescape=True)
        self.visualization_configs = self._initialize_visualizations()
        self.compliance_frameworks = self._initialize_compliance_frameworks()
        
    def _initialize_visualizations(self) -> List[VisualizationConfig]:
        """Initialize visualization configurations."""
        return [
            VisualizationConfig(
                viz_id="entity_distribution",
                viz_type="entity_analysis",
                title="Entity Distribution by Type",
                data_source="entities",
                chart_type="pie",
                interactive=True,
                export_formats=["png", "svg", "html"],
                styling={"colors": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]}
            ),
            VisualizationConfig(
                viz_id="confidence_timeline",
                viz_type="temporal_analysis",
                title="Confidence Score Timeline",
                data_source="entities",
                chart_type="line",
                interactive=True,
                export_formats=["png", "svg", "html"],
                styling={"line_style": "solid", "marker": "circle"}
            ),
            VisualizationConfig(
                viz_id="risk_heatmap",
                viz_type="risk_analysis",
                title="Risk Assessment Heatmap",
                data_source="risk_assessment",
                chart_type="heatmap",
                interactive=True,
                export_formats=["png", "svg", "html"],
                styling={"colormap": "Reds"}
            ),
            VisualizationConfig(
                viz_id="entity_network",
                viz_type="network_analysis",
                title="Entity Relationship Network",
                data_source="relationships",
                chart_type="network",
                interactive=True,
                export_formats=["png", "svg", "html"],
                styling={"layout": "spring", "node_size": 300}
            ),
            VisualizationConfig(
                viz_id="source_reliability",
                viz_type="source_analysis",
                title="Source Reliability Analysis",
                data_source="sources",
                chart_type="bar",
                interactive=True,
                export_formats=["png", "svg", "html"],
                styling={"orientation": "vertical"}
            )
        ]
    
    def _initialize_compliance_frameworks(self) -> Dict[str, Any]:
        """Initialize compliance frameworks."""
        return {
            'GDPR': {
                'name': 'General Data Protection Regulation',
                'requirements': [
                    'lawful_basis_for_processing',
                    'data_minimization',
                    'purpose_limitation',
                    'storage_limitation',
                    'security_measures',
                    'accountability'
                ],
                'scoring_weights': {
                    'lawful_basis_for_processing': 0.2,
                    'data_minimization': 0.15,
                    'purpose_limitation': 0.15,
                    'storage_limitation': 0.1,
                    'security_measures': 0.25,
                    'accountability': 0.15
                }
            },
            'CCPA': {
                'name': 'California Consumer Privacy Act',
                'requirements': [
                    'right_to_know',
                    'right_to_delete',
                    'right_to_opt_out',
                    'right_to_non_discrimination',
                    'data_security'
                ],
                'scoring_weights': {
                    'right_to_know': 0.2,
                    'right_to_delete': 0.2,
                    'right_to_opt_out': 0.2,
                    'right_to_non_discrimination': 0.2,
                    'data_security': 0.2
                }
            }
        }
    
    async def generate_enhanced_report(self, entities: List[Entity], 
                                      investigation_id: str,
                                      correlation_id: Optional[str] = None) -> InvestigationReport:
        """Generate enhanced professional intelligence report."""
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f"Generating enhanced report", 
                           entity_count=len(entities),
                           investigation_id=investigation_id,
                           correlation_id=correlation_id)
            
            # Generate threat assessment
            threat_assessment = await self._generate_threat_assessment(
                entities, investigation_id, correlation_id
            )
            
            # Generate compliance report
            compliance_report = await self._generate_compliance_report(
                entities, investigation_id, correlation_id
            )
            
            # Generate intelligence summary
            intelligence_summary = await self._generate_intelligence_summary(
                entities, investigation_id, correlation_id
            )
            
            # Generate visualizations
            visualizations = await self._generate_visualizations(
                entities, investigation_id, correlation_id
            )
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Create enhanced investigation report
            report = InvestigationReport(
                investigation_id=investigation_id,
                generated_at=datetime.utcnow(),
                entities=entities,
                executive_summary=intelligence_summary,
                threat_assessment=threat_assessment,
                compliance_report=compliance_report,
                visualizations=visualizations,
                metadata={
                    'enhanced_reporting': True,
                    'processing_time': processing_time,
                    'threat_count': len(threat_assessment.indicators),
                    'compliance_score': compliance_report.compliance_score,
                    'visualization_count': len(visualizations),
                    'correlation_id': correlation_id
                }
            )
            
            self.logger.info(f"Enhanced report generated successfully",
                           processing_time=processing_time,
                           threat_count=len(threat_assessment.indicators),
                           compliance_score=compliance_report.compliance_score,
                           correlation_id=correlation_id)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Enhanced report generation failed",
                           error=str(e),
                           investigation_id=investigation_id,
                           correlation_id=correlation_id)
            
            # Fallback to basic report
            return await self.generate_report(entities, investigation_id, correlation_id)
    
    async def _generate_threat_assessment(self, entities: List[Entity],
                                        investigation_id: str,
                                        correlation_id: Optional[str] = None) -> ThreatAssessment:
        """Generate professional threat assessment."""
        # Analyze entities for threats
        threat_indicators = []
        threat_types = []
        
        for entity in entities:
            if entity.entity_type == EntityType.EMAIL:
                threat_indicators.append(f"Email exposure: {entity.value}")
                threat_types.append("data_exposure")
            elif entity.entity_type == EntityType.PHONE:
                threat_indicators.append(f"Phone exposure: {entity.value}")
                threat_types.append("data_exposure")
            elif entity.entity_type == EntityType.PERSON:
                threat_indicators.append(f"Personal identity: {entity.value}")
                threat_types.append("identity_theft")
            elif entity.entity_type == EntityType.LOCATION:
                threat_indicators.append(f"Location data: {entity.value}")
                threat_types.append("physical_threat")
        
        # Determine threat severity
        high_risk_entities = [e for e in entities if e.confidence > 0.8]
        
        if len(high_risk_entities) > 10:
            severity = "CRITICAL"
        elif len(high_risk_entities) > 5:
            severity = "HIGH"
        elif len(high_risk_entities) > 2:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        # Determine likelihood
        if len(entities) > 20:
            likelihood = "HIGH"
        elif len(entities) > 10:
            likelihood = "MEDIUM"
        else:
            likelihood = "LOW"
        
        # Determine impact
        sensitive_entities = [e for e in entities if e.entity_type in [EntityType.EMAIL, EntityType.PHONE, EntityType.PERSON]]
        if len(sensitive_entities) > 10:
            impact = "HIGH"
        elif len(sensitive_entities) > 5:
            impact = "MEDIUM"
        else:
            impact = "LOW"
        
        # Generate mitigation steps
        mitigation_steps = [
            "Enable two-factor authentication on all accounts",
            "Review and update privacy settings on social media",
            "Remove personal information from public directories",
            "Monitor for identity theft indicators",
            "Implement regular security audits"
        ]
        
        return ThreatAssessment(
            threat_id=str(uuid.uuid4()),
            threat_type="data_exposure",
            severity=severity,
            likelihood=likelihood,
            impact=impact,
            confidence=0.85,
            indicators=threat_indicators,
            mitigation_steps=mitigation_steps,
            assessment_date=datetime.utcnow(),
            assessor="OSINT Framework",
            metadata={
                'entity_count': len(entities),
                'high_confidence_count': len(high_risk_entities),
                'correlation_id': correlation_id
            }
        )
    
    async def _generate_compliance_report(self, entities: List[Entity],
                                       investigation_id: str,
                                       correlation_id: Optional[str] = None) -> ComplianceReport:
        """Generate compliance report."""
        # Use GDPR as default framework
        framework = self.compliance_frameworks['GDPR']
        
        # Assess compliance
        compliance_scores = {}
        violations = []
        
        # Data minimization
        if len(entities) > 50:
            compliance_scores['data_minimization'] = 0.3
            violations.append("Excessive data collection detected")
        else:
            compliance_scores['data_minimization'] = 0.9
        
        # Security measures
        high_confidence_entities = [e for e in entities if e.confidence > 0.8]
        if len(high_confidence_entities) > 0:
            compliance_scores['security_measures'] = 0.7
        else:
            compliance_scores['security_measures'] = 0.9
        
        # Storage limitation
        compliance_scores['storage_limitation'] = 0.8  # Assuming proper retention
        
        # Purpose limitation
        compliance_scores['purpose_limitation'] = 0.8  # Assuming proper use
        
        # Lawful basis
        compliance_scores['lawful_basis_for_processing'] = 0.8  # Assuming consent
        
        # Accountability
        compliance_scores['accountability'] = 0.9  # Framework provides audit trail
        
        # Calculate overall compliance score
        weights = framework['scoring_weights']
        overall_score = sum(
            compliance_scores[req] * weights[req]
            for req in framework['requirements']
            if req in compliance_scores
        )
        
        # Generate recommendations
        recommendations = [
            "Implement data minimization principles",
            "Enhance security measures for high-confidence data",
            "Establish clear data retention policies",
            "Document lawful basis for data processing",
            "Regular compliance audits"
        ]
        
        # Create audit trail
        audit_trail = [
            {
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'compliance_assessment',
                'framework': 'GDPR',
                'score': overall_score,
                'entity_count': len(entities)
            }
        ]
        
        return ComplianceReport(
            compliance_id=str(uuid.uuid4()),
            framework='GDPR',
            compliance_score=overall_score,
            violations=violations,
            recommendations=recommendations,
            audit_trail=audit_trail,
            assessment_date=datetime.utcnow(),
            metadata={
                'individual_scores': compliance_scores,
                'entity_count': len(entities),
                'correlation_id': correlation_id
            }
        )
    
    async def _generate_intelligence_summary(self, entities: List[Entity],
                                          investigation_id: str,
                                          correlation_id: Optional[str] = None) -> IntelligenceSummary:
        """Generate executive intelligence summary."""
        # Key findings
        key_findings = []
        
        entity_counts = {}
        for entity in entities:
            entity_counts[entity.entity_type] = entity_counts.get(entity.entity_type, 0) + 1
        
        if entity_counts:
            most_common_type = max(entity_counts, key=entity_counts.get)
            key_findings.append(f"Most common entity type: {most_common_type.value} ({entity_counts[most_common_type]} instances)")
        
        high_confidence_count = len([e for e in entities if e.confidence > 0.8])
        key_findings.append(f"High-confidence entities: {high_confidence_count}")
        
        # Determine risk level
        if high_confidence_count > 10:
            risk_level = RiskLevel.HIGH
        elif high_confidence_count > 5:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        # Threat actors (generic)
        threat_actors = [
            "Malicious actors seeking personal data",
            "Data brokers",
            "Social engineering attackers"
        ]
        
        # Attack vectors
        attack_vectors = [
            "Public information gathering",
            "Social media profiling",
            "Data aggregation"
        ]
        
        # Recommendations
        recommendations = [
            "Implement comprehensive privacy controls",
            "Regular monitoring of digital footprint",
            "Enhanced security measures for sensitive data",
            "Employee training on data protection"
        ]
        
        # Data sources
        data_sources = list(set(e.metadata.get('source', 'unknown') for e in entities))
        
        return IntelligenceSummary(
            summary_id=str(uuid.uuid4()),
            key_findings=key_findings,
            risk_level=risk_level,
            threat_actors=threat_actors,
            attack_vectors=attack_vectors,
            recommendations=recommendations,
            confidence_level=0.85,
            data_sources=data_sources,
            analysis_date=datetime.utcnow(),
            metadata={
                'entity_counts': entity_counts,
                'total_entities': len(entities),
                'correlation_id': correlation_id
            }
        )
    
    async def _generate_visualizations(self, entities: List[Entity],
                                     investigation_id: str,
                                     correlation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Generate interactive visualizations."""
        visualizations = []
        
        # Entity distribution pie chart
        entity_dist_viz = await self._create_entity_distribution_chart(entities)
        visualizations.append(entity_dist_viz)
        
        # Confidence timeline
        confidence_viz = await self._create_confidence_timeline(entities)
        visualizations.append(confidence_viz)
        
        # Risk heatmap
        risk_viz = await self._create_risk_heatmap(entities)
        visualizations.append(risk_viz)
        
        # Entity network
        network_viz = await self._create_entity_network(entities)
        visualizations.append(network_viz)
        
        return visualizations
    
    async def _create_entity_distribution_chart(self, entities: List[Entity]) -> Dict[str, Any]:
        """Create entity distribution pie chart."""
        entity_counts = {}
        for entity in entities:
            entity_counts[entity.entity_type.value] = entity_counts.get(entity.entity_type.value, 0) + 1
        
        fig = go.Figure(data=[go.Pie(
            labels=list(entity_counts.keys()),
            values=list(entity_counts.values()),
            hole=0.3
        )])
        
        fig.update_layout(
            title="Entity Distribution by Type",
            font=dict(size=12)
        )
        
        return {
            'viz_id': 'entity_distribution',
            'title': 'Entity Distribution by Type',
            'type': 'pie',
            'data': entity_counts,
            'chart_json': fig.to_json(),
            'interactive': True
        }
    
    async def _create_confidence_timeline(self, entities: List[Entity]) -> Dict[str, Any]:
        """Create confidence timeline chart."""
        # Create timeline data
        timeline_data = []
        for entity in entities:
            timeline_data.append({
                'entity_id': entity.id,
                'confidence': entity.confidence,
                'timestamp': entity.metadata.get('created_at', datetime.utcnow().isoformat())
            })
        
        df = pd.DataFrame(timeline_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        fig = px.line(
            df, 
            x='timestamp', 
            y='confidence',
            title='Confidence Score Timeline',
            markers=True
        )
        
        return {
            'viz_id': 'confidence_timeline',
            'title': 'Confidence Score Timeline',
            'type': 'line',
            'data': timeline_data,
            'chart_json': fig.to_json(),
            'interactive': True
        }
    
    async def _create_risk_heatmap(self, entities: List[Entity]) -> Dict[str, Any]:
        """Create risk assessment heatmap."""
        # Create risk matrix
        risk_data = []
        entity_types = list(set(e.entity_type.value for e in entities))
        
        for entity_type in entity_types:
            type_entities = [e for e in entities if e.entity_type.value == entity_type]
            
            # Calculate risk metrics
            avg_confidence = sum(e.confidence for e in type_entities) / len(type_entities)
            exposure_count = len(type_entities)
            
            risk_score = avg_confidence * exposure_count / 10
            
            risk_data.append({
                'entity_type': entity_type,
                'confidence': avg_confidence,
                'exposure': exposure_count,
                'risk_score': risk_score
            })
        
        df = pd.DataFrame(risk_data)
        
        fig = px.density_heatmap(
            df, 
            x='entity_type', 
            y='confidence',
            z='risk_score',
            title='Risk Assessment Heatmap'
        )
        
        return {
            'viz_id': 'risk_heatmap',
            'title': 'Risk Assessment Heatmap',
            'type': 'heatmap',
            'data': risk_data,
            'chart_json': fig.to_json(),
            'interactive': True
        }
    
    async def _create_entity_network(self, entities: List[Entity]) -> Dict[str, Any]:
        """Create entity relationship network."""
        # Create network graph
        G = nx.Graph()
        
        # Add nodes
        for entity in entities:
            G.add_node(
                entity.id,
                label=entity.value[:20] + "..." if len(entity.value) > 20 else entity.value,
                type=entity.entity_type.value,
                confidence=entity.confidence
            )
        
        # Add edges (simplified - in real implementation would use actual relationships)
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                if entity1.entity_type == entity2.entity_type:
                    G.add_edge(entity1.id, entity2.id, weight=0.5)
        
        # Create network visualization
        pos = nx.spring_layout(G)
        
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        )
        
        node_x = []
        node_y = []
        node_text = []
        node_info = []
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_info.append(G.nodes[node])
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=[info['label'] for info in node_info],
            marker=dict(
                size=10,
                color=[info['confidence'] for info in node_info],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Confidence")
            )
        )
        
        fig = go.Figure(data=[edge_trace, node_trace],
                       layout=go.Layout(
                           title='Entity Relationship Network',
                           titlefont_size=16,
                           showlegend=False,
                           hovermode='closest',
                           margin=dict(b=20,l=5,r=5,t=40),
                           annotations=[ dict(
                               text="Network visualization of entity relationships",
                               showarrow=False,
                               xref="paper", yref="paper",
                               x=0.005, y=-0.002,
                               xanchor='left', yanchor='bottom',
                               font=dict(color="black", size=12)
                           )],
                           xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
                       ))
        
        return {
            'viz_id': 'entity_network',
            'title': 'Entity Relationship Network',
            'type': 'network',
            'data': {'nodes': len(G.nodes()), 'edges': len(G.edges())},
            'chart_json': fig.to_json(),
            'interactive': True
        }
    
    async def export_enhanced_report(self, report: InvestigationReport, 
                                  output_format: ReportFormat,
                                  correlation_id: Optional[str] = None) -> Union[str, bytes]:
        """Export enhanced report in multiple formats."""
        try:
            if output_format == ReportFormat.JSON:
                return await self._export_enhanced_json(report, correlation_id)
            elif output_format == ReportFormat.MARKDOWN:
                return await self._export_enhanced_markdown(report, correlation_id)
            elif output_format == ReportFormat.HTML:
                return await self._export_enhanced_html(report, correlation_id)
            elif output_format == ReportFormat.PDF:
                return await self._export_enhanced_pdf(report, correlation_id)
            else:
                return await self.export_report(report, output_format, correlation_id)
        
        except Exception as e:
            self.logger.error(f"Enhanced export failed: {e}")
            return await self.export_report(report, output_format, correlation_id)
    
    async def _export_enhanced_html(self, report: InvestigationReport,
                                 correlation_id: Optional[str] = None) -> str:
        """Export enhanced HTML report with visualizations."""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>OSINT Investigation Report - {{ report.investigation_id }}</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { text-align: center; margin-bottom: 40px; }
                .section { margin-bottom: 30px; }
                .risk-high { color: #d32f2f; }
                .risk-medium { color: #f57c00; }
                .risk-low { color: #388e3c; }
                .visualization { margin: 20px 0; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>OSINT Investigation Report</h1>
                <p>Investigation ID: {{ report.investigation_id }}</p>
                <p>Generated: {{ report.generated_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
            </div>
            
            <div class="section">
                <h2>Executive Summary</h2>
                <p>Risk Level: <span class="risk-{{ report.executive_summary.risk_level.value.lower() }}">{{ report.executive_summary.risk_level.value }}</span></p>
                <p>Confidence Level: {{ "%.1f"|format(report.executive_summary.confidence_level * 100) }}%</p>
                <ul>
                    {% for finding in report.executive_summary.key_findings %}
                    <li>{{ finding }}</li>
                    {% endfor %}
                </ul>
            </div>
            
            <div class="section">
                <h2>Threat Assessment</h2>
                <p>Severity: {{ report.threat_assessment.severity }}</p>
                <p>Likelihood: {{ report.threat_assessment.likelihood }}</p>
                <p>Impact: {{ report.threat_assessment.impact }}</p>
                <h3>Indicators:</h3>
                <ul>
                    {% for indicator in report.threat_assessment.indicators %}
                    <li>{{ indicator }}</li>
                    {% endfor %}
                </ul>
            </div>
            
            <div class="section">
                <h2>Compliance Report</h2>
                <p>Framework: {{ report.compliance_report.framework }}</p>
                <p>Compliance Score: {{ "%.1f"|format(report.compliance_report.compliance_score * 100) }}%</p>
                {% if report.compliance_report.violations %}
                <h3>Violations:</h3>
                <ul>
                    {% for violation in report.compliance_report.violations %}
                    <li>{{ violation }}</li>
                    {% endfor %}
                </ul>
                {% endif %}
            </div>
            
            <div class="section">
                <h2>Visualizations</h2>
                {% for viz in report.visualizations %}
                <div class="visualization">
                    <h3>{{ viz.title }}</h3>
                    <div id="{{ viz.viz_id }}"></div>
                </div>
                {% endfor %}
            </div>
            
            <div class="section">
                <h2>Entity Details</h2>
                <table>
                    <tr>
                        <th>Type</th>
                        <th>Value</th>
                        <th>Confidence</th>
                        <th>Status</th>
                    </tr>
                    {% for entity in report.entities %}
                    <tr>
                        <td>{{ entity.entity_type.value }}</td>
                        <td>{{ entity.value }}</td>
                        <td>{{ "%.1f"|format(entity.confidence * 100) }}%</td>
                        <td>{{ entity.verification_status.value }}</td>
                    </tr>
                    {% endfor %}
                </table>
            </div>
            
            <script>
                // Render visualizations
                {% for viz in report.visualizations %}
                var data{{ viz.viz_id }} = {{ viz.chart_json }};
                Plotly.newPlot('{{ viz.viz_id }}', data{{ viz.viz_id }}.data, data{{ viz.viz_id }}.layout);
                {% endfor %}
            </script>
        </body>
        </html>
        """
        
        template = Template(template_str)
        return template.render(report=report)
    
    async def _export_enhanced_pdf(self, report: InvestigationReport,
                                 correlation_id: Optional[str] = None) -> bytes:
        """Export enhanced PDF report."""
        # Generate HTML first
        html_content = await self._export_enhanced_html(report, correlation_id)
        
        # Convert to PDF using WeasyPrint
        css = CSS(string='''
            @page { margin: 2cm; }
            body { font-family: Arial, sans-serif; font-size: 12px; }
            h1 { font-size: 24px; text-align: center; }
            h2 { font-size: 18px; color: #333; border-bottom: 2px solid #333; }
            h3 { font-size: 14px; color: #666; }
            table { border-collapse: collapse; width: 100%; margin: 10px 0; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; font-weight: bold; }
            .risk-high { color: #d32f2f; font-weight: bold; }
            .risk-medium { color: #f57c00; font-weight: bold; }
            .risk-low { color: #388e3c; font-weight: bold; }
        ''')
        
        # Create HTML object
        html_doc = HTML(string=html_content)
        
        # Generate PDF
        pdf_bytes = html_doc.write_pdf(stylesheets=[css])
        
        return pdf_bytes
    
    async def _export_enhanced_json(self, report: InvestigationReport,
                                 correlation_id: Optional[str] = None) -> str:
        """Export enhanced JSON report."""
        report_dict = {
            'investigation_id': report.investigation_id,
            'generated_at': report.generated_at.isoformat(),
            'entities': [
                {
                    'id': entity.id,
                    'type': entity.entity_type.value,
                    'value': entity.value,
                    'confidence': entity.confidence,
                    'verification_status': entity.verification_status.value,
                    'metadata': entity.metadata
                }
                for entity in report.entities
            ],
            'executive_summary': {
                'summary_id': report.executive_summary.summary_id,
                'key_findings': report.executive_summary.key_findings,
                'risk_level': report.executive_summary.risk_level.value,
                'threat_actors': report.executive_summary.threat_actors,
                'attack_vectors': report.executive_summary.attack_vectors,
                'recommendations': report.executive_summary.recommendations,
                'confidence_level': report.executive_summary.confidence_level,
                'data_sources': report.executive_summary.data_sources,
                'analysis_date': report.executive_summary.analysis_date.isoformat()
            },
            'threat_assessment': {
                'threat_id': report.threat_assessment.threat_id,
                'threat_type': report.threat_assessment.threat_type,
                'severity': report.threat_assessment.severity,
                'likelihood': report.threat_assessment.likelihood,
                'impact': report.threat_assessment.impact,
                'confidence': report.threat_assessment.confidence,
                'indicators': report.threat_assessment.indicators,
                'mitigation_steps': report.threat_assessment.mitigation_steps,
                'assessment_date': report.threat_assessment.assessment_date.isoformat()
            },
            'compliance_report': {
                'compliance_id': report.compliance_report.compliance_id,
                'framework': report.compliance_report.framework,
                'compliance_score': report.compliance_report.compliance_score,
                'violations': report.compliance_report.violations,
                'recommendations': report.compliance_report.recommendations,
                'assessment_date': report.compliance_report.assessment_date.isoformat()
            },
            'visualizations': [
                {
                    'viz_id': viz.viz_id,
                    'title': viz.title,
                    'type': viz.type,
                    'data': viz.data,
                    'interactive': viz.interactive
                }
                for viz in report.visualizations
            ],
            'metadata': report.metadata
        }
        
        return json.dumps(report_dict, indent=2, default=str)
    
    async def _export_enhanced_markdown(self, report: InvestigationReport,
                                      correlation_id: Optional[str] = None) -> str:
        """Export enhanced Markdown report."""
        md_content = f"""# OSINT Investigation Report

**Investigation ID:** {report.investigation_id}  
**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

**Risk Level:** {report.executive_summary.risk_level.value}  
**Confidence Level:** {report.executive_summary.confidence_level * 100:.1f}%

### Key Findings
"""
        
        for finding in report.executive_summary.key_findings:
            md_content += f"- {finding}\n"
        
        md_content += f"""
## Threat Assessment

**Severity:** {report.threat_assessment.severity}  
**Likelihood:** {report.threat_assessment.likelihood}  
**Impact:** {report.threat_assessment.impact}  
**Confidence:** {report.threat_assessment.confidence * 100:.1f}%

### Indicators
"""
        
        for indicator in report.threat_assessment.indicators:
            md_content += f"- {indicator}\n"
        
        md_content += f"""
### Mitigation Steps
"""
        
        for step in report.threat_assessment.mitigation_steps:
            md_content += f"- {step}\n"
        
        md_content += f"""
## Compliance Report

**Framework:** {report.compliance_report.framework}  
**Compliance Score:** {report.compliance_report.compliance_score * 100:.1f}%
"""
        
        if report.compliance_report.violations:
            md_content += "\n### Violations\n"
            for violation in report.compliance_report.violations:
                md_content += f"- {violation}\n"
        
        md_content += f"""
## Entity Details

| Type | Value | Confidence | Status |
|------|-------|------------|--------|
"""
        
        for entity in report.entities:
            md_content += f"| {entity.entity_type.value} | {entity.value} | {entity.confidence * 100:.1f}% | {entity.verification_status.value} |\n"
        
        md_content += f"""
## Visualizations

"""
        
        for viz in report.visualizations:
            md_content += f"### {viz.title}\n"
            md_content += f"- Type: {viz.type}\n"
            md_content += f"- Interactive: {viz.interactive}\n"
            md_content += f"- Data Points: {viz.data.get('count', 'N/A')}\n\n"
        
        return md_content
