"""
Entity Graph Engine for OSINT Framework

Graph-based entity resolution and relationship tracking:
- Directed graph of entities and relationships
- Transitive property resolution
- Ego network analysis
- Community detection
- Path finding between entities
- Relationship strength metrics
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple, Any
from enum import Enum
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class RelationshipType(Enum):
    """Types of relationships between entities."""
    SAME_IDENTITY = "same_identity"  # Different platforms, same person
    KNOWS = "knows"  # Professional/social relationship
    WORKS_WITH = "works_with"  # Same company/project
    FAMILY = "family"  # Family relationship
    OWNS = "owns"  # Owns domain/company
    MANAGES = "manages"  # Manager relationship
    ASSOCIATED = "associated"  # Unclear relationship type
    FINANCIAL = "financial"  # Financial relationship
    RESIDENCE = "residence"  # Shared address
    COMMUNICATION = "communication"  # Email/message exchange


class EdgeType(Enum):
    """Types of edges in entity graph."""
    DIRECT = "direct"  # Direct observation
    INFERRED = "inferred"  # Inferred from other relationships
    TRANSITIVE = "transitive"  # Through third party


@dataclass
class EntityNode:
    """A node in the entity graph."""
    node_id: str
    entity_type: str  # PERSON, COMPANY, DOMAIN, etc.
    attributes: Dict[str, Any]
    confidence: float  # 0-1, confidence this entity is real
    created_at: datetime = field(default_factory=datetime.utcnow)
    sources: List[str] = field(default_factory=list)  # Sources that reported this
    tags: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict:
        return {
            'node_id': self.node_id,
            'entity_type': self.entity_type,
            'attributes': self.attributes,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat(),
            'sources': self.sources,
            'tags': list(self.tags)
        }


@dataclass
class EntityEdge:
    """An edge between two entities in the graph."""
    edge_id: str = field(default_factory=lambda: str(uuid4()))
    source_id: str = ""
    target_id: str = ""
    relationship_type: RelationshipType = RelationshipType.ASSOCIATED
    edge_type: EdgeType = EdgeType.DIRECT
    strength: float = 0.5  # 0-1, strength of relationship
    confidence: float = 0.5  # 0-1, confidence in this relationship
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    source_connector: str = ""  # Which connector found this

    def to_dict(self) -> Dict:
        return {
            'edge_id': self.edge_id,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'relationship_type': self.relationship_type.value,
            'edge_type': self.edge_type.value,
            'strength': self.strength,
            'confidence': self.confidence,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'source_connector': self.source_connector
        }


class EntityGraph:
    """Directed graph of entities and their relationships."""

    def __init__(self):
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        self.nodes: Dict[str, EntityNode] = {}
        self.edges: Dict[str, EntityEdge] = {}
        self.adjacency: Dict[str, List[str]] = {}  # node_id -> list of connected node_ids
        self._cache_dirty = False

    # ==================== Node Management ====================

    def add_node(
        self,
        node_id: str,
        entity_type: str,
        attributes: Dict[str, Any],
        confidence: float = 0.5,
        sources: Optional[List[str]] = None
    ) -> EntityNode:
        """Add or update a node in the graph."""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            # Update attributes and confidence
            node.attributes.update(attributes)
            node.confidence = max(node.confidence, confidence)
            if sources:
                node.sources.extend(sources)
            node.sources = list(set(node.sources))
        else:
            node = EntityNode(
                node_id=node_id,
                entity_type=entity_type,
                attributes=attributes,
                confidence=confidence,
                sources=sources or []
            )
            self.nodes[node_id] = node
            self.adjacency[node_id] = []

        self._cache_dirty = True
        return node

    def get_node(self, node_id: str) -> Optional[EntityNode]:
        """Retrieve a node by ID."""
        return self.nodes.get(node_id)

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and its edges."""
        if node_id not in self.nodes:
            return False

        # Remove all edges involving this node
        edges_to_remove = [
            eid for eid, edge in self.edges.items()
            if edge.source_id == node_id or edge.target_id == node_id
        ]
        for eid in edges_to_remove:
            self.remove_edge(eid)

        del self.nodes[node_id]
        if node_id in self.adjacency:
            del self.adjacency[node_id]

        self._cache_dirty = True
        return True

    def get_nodes_by_type(self, entity_type: str) -> List[EntityNode]:
        """Get all nodes of a specific type."""
        return [n for n in self.nodes.values() if n.entity_type == entity_type]

    def get_nodes_by_attribute(self, attr_key: str, attr_value: Any) -> List[EntityNode]:
        """Get all nodes with a specific attribute."""
        return [
            n for n in self.nodes.values()
            if n.attributes.get(attr_key) == attr_value
        ]

    # ==================== Edge Management ====================

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType = RelationshipType.ASSOCIATED,
        strength: float = 0.5,
        confidence: float = 0.5,
        metadata: Optional[Dict] = None,
        source_connector: str = ""
    ) -> Optional[EntityEdge]:
        """Add an edge between two nodes."""
        if source_id not in self.nodes or target_id not in self.nodes:
            self.logger.warning(
                "Cannot add edge, nodes not found",
                source_id=source_id,
                target_id=target_id
            )
            return None

        edge = EntityEdge(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            strength=strength,
            confidence=confidence,
            metadata=metadata or {},
            source_connector=source_connector
        )

        self.edges[edge.edge_id] = edge

        # Update adjacency
        if target_id not in self.adjacency[source_id]:
            self.adjacency[source_id].append(target_id)

        self._cache_dirty = True
        return edge

    def get_edge(self, edge_id: str) -> Optional[EntityEdge]:
        """Retrieve an edge by ID."""
        return self.edges.get(edge_id)

    def get_edges_from(self, source_id: str) -> List[EntityEdge]:
        """Get all outgoing edges from a node."""
        return [e for e in self.edges.values() if e.source_id == source_id]

    def get_edges_to(self, target_id: str) -> List[EntityEdge]:
        """Get all incoming edges to a node."""
        return [e for e in self.edges.values() if e.target_id == target_id]

    def get_edges_between(self, node_id1: str, node_id2: str) -> List[EntityEdge]:
        """Get all edges between two nodes (both directions)."""
        return [
            e for e in self.edges.values()
            if (e.source_id == node_id1 and e.target_id == node_id2) or
               (e.source_id == node_id2 and e.target_id == node_id1)
        ]

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge from the graph."""
        if edge_id not in self.edges:
            return False

        edge = self.edges[edge_id]
        if edge.target_id in self.adjacency[edge.source_id]:
            self.adjacency[edge.source_id].remove(edge.target_id)

        del self.edges[edge_id]
        self._cache_dirty = True
        return True

    # ==================== Graph Analysis ====================

    def get_ego_network(
        self,
        center_id: str,
        depth: int = 2,
        relationship_filter: Optional[Set[RelationshipType]] = None
    ) -> 'EntityGraph':
        """
        Extract ego network - center node plus neighbors up to specified depth.
        """
        ego = EntityGraph()
        visited = set()

        def traverse(node_id: str, current_depth: int):
            if current_depth < 0 or node_id in visited:
                return

            visited.add(node_id)
            node = self.nodes[node_id]
            ego.add_node(
                node_id,
                node.entity_type,
                node.attributes,
                node.confidence,
                node.sources
            )

            # Get outgoing edges
            for edge in self.get_edges_from(node_id):
                if relationship_filter and edge.relationship_type not in relationship_filter:
                    continue

                # Add target node
                target = self.nodes[edge.target_id]
                ego.add_node(
                    edge.target_id,
                    target.entity_type,
                    target.attributes,
                    target.confidence,
                    target.sources
                )

                # Add edge
                ego.add_edge(
                    edge.source_id,
                    edge.target_id,
                    edge.relationship_type,
                    edge.strength,
                    edge.confidence,
                    edge.metadata,
                    edge.source_connector
                )

                # Recurse
                traverse(edge.target_id, current_depth - 1)

        traverse(center_id, depth)
        return ego

    def find_shortest_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """Find shortest path between two nodes using BFS."""
        if source_id not in self.nodes or target_id not in self.nodes:
            return None

        visited = {source_id}
        queue = [(source_id, [source_id])]

        while queue:
            current, path = queue.pop(0)

            if current == target_id:
                return path

            for next_id in self.adjacency.get(current, []):
                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [next_id]))

        return None

    def get_path_confidence(self, path: List[str]) -> float:
        """Calculate confidence of a path as product of edge confidences."""
        if len(path) < 2:
            return 1.0

        confidence = 1.0
        for i in range(len(path) - 1):
            edges = self.get_edges_between(path[i], path[i + 1])
            if not edges:
                return 0.0
            # Use highest confidence edge
            max_confidence = max(e.confidence for e in edges)
            confidence *= max_confidence

        return confidence

    def community_detection(self) -> List[Set[str]]:
        """
        Simple community detection using connected components.
        Returns list of communities (sets of node IDs).
        """
        visited = set()
        communities = []

        def dfs(node_id: str, community: Set[str]):
            visited.add(node_id)
            community.add(node_id)

            # Visit neighbors (both directions)
            for edge in self.get_edges_from(node_id):
                if edge.target_id not in visited:
                    dfs(edge.target_id, community)

            for edge in self.get_edges_to(node_id):
                if edge.source_id not in visited:
                    dfs(edge.source_id, community)

        for node_id in self.nodes:
            if node_id not in visited:
                community = set()
                dfs(node_id, community)
                communities.append(community)

        return communities

    # ==================== Transitive Property ====================

    def compute_transitive_relationships(
        self,
        relationship_type: RelationshipType
    ) -> List[EntityEdge]:
        """
        Find transitive relationships.
        If A relates to B and B relates to C, infer A relates to C.
        """
        transitive_edges = []

        for middle_id in self.nodes:
            outgoing = self.get_edges_from(middle_id)
            incoming = self.get_edges_to(middle_id)

            for in_edge in incoming:
                for out_edge in outgoing:
                    # Check if both edges are of the requested type
                    if (in_edge.relationship_type == relationship_type and
                        out_edge.relationship_type == relationship_type):

                        # Create transitive edge
                        strength = in_edge.strength * out_edge.strength
                        confidence = in_edge.confidence * out_edge.confidence

                        transitive_edge = EntityEdge(
                            source_id=in_edge.source_id,
                            target_id=out_edge.target_id,
                            relationship_type=relationship_type,
                            edge_type=EdgeType.TRANSITIVE,
                            strength=strength,
                            confidence=confidence,
                            metadata={
                                'transitive_through': middle_id,
                                'original_edges': [in_edge.edge_id, out_edge.edge_id]
                            }
                        )

                        transitive_edges.append(transitive_edge)

        return transitive_edges

    # ==================== Centrality Measures ====================

    def compute_pagerank(self, iterations: int = 20, damping: float = 0.85) -> Dict[str, float]:
        """
        Compute PageRank scores for all nodes.
        Higher scores indicate more important/connected nodes.
        """
        if not self.nodes:
            return {}

        ranks = {nid: 1.0 / len(self.nodes) for nid in self.nodes}
        n = len(self.nodes)

        for _ in range(iterations):
            new_ranks = {}
            for node_id in self.nodes:
                # Probability of random jump
                pr = (1 - damping) / n

                # Add contributions from incoming edges
                incoming = self.get_edges_to(node_id)
                for edge in incoming:
                    source_edges = len(self.get_edges_from(edge.source_id))
                    if source_edges > 0:
                        # Weight by edge strength
                        weight = edge.strength / source_edges
                        pr += damping * ranks[edge.source_id] * weight

                new_ranks[node_id] = pr

            ranks = new_ranks

        return ranks

    def compute_degree_centrality(self) -> Dict[str, float]:
        """Compute in-degree and out-degree centrality."""
        centrality = {}

        for node_id in self.nodes:
            in_degree = len(self.get_edges_to(node_id))
            out_degree = len(self.get_edges_from(node_id))
            total_degree = in_degree + out_degree

            # Normalize by max possible (n-1)
            max_degree = (len(self.nodes) - 1) * 2
            if max_degree > 0:
                centrality[node_id] = total_degree / max_degree
            else:
                centrality[node_id] = 0

        return centrality

    def compute_betweenness_centrality(self) -> Dict[str, float]:
        """
        Compute betweenness centrality.
        Measures how often a node lies on shortest paths between other nodes.
        """
        centrality = {nid: 0.0 for nid in self.nodes}

        for source_id in self.nodes:
            for target_id in self.nodes:
                if source_id == target_id:
                    continue

                path = self.find_shortest_path(source_id, target_id)
                if path:
                    # Add credit to intermediate nodes
                    for node_id in path[1:-1]:
                        centrality[node_id] += 1

        # Normalize
        if len(self.nodes) > 2:
            norm = 2.0 / ((len(self.nodes) - 1) * (len(self.nodes) - 2))
            for node_id in centrality:
                centrality[node_id] *= norm

        return centrality

    # ==================== Export & Visualization ====================

    def to_dict(self) -> Dict:
        """Export graph to dictionary."""
        return {
            'nodes': [n.to_dict() for n in self.nodes.values()],
            'edges': [e.to_dict() for e in self.edges.values()],
            'stats': {
                'node_count': len(self.nodes),
                'edge_count': len(self.edges),
                'pagerank': self.compute_pagerank(),
                'centrality': self.compute_degree_centrality()
            }
        }

    def to_graphml(self) -> str:
        """Export graph to GraphML format (for visualization tools)."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
            '  <graph edgedefault="directed">',
        ]

        # Add nodes
        for node in self.nodes.values():
            lines.append(f'    <node id="{node.node_id}">')
            lines.append(f'      <data key="type">{node.entity_type}</data>')
            lines.append(f'      <data key="confidence">{node.confidence}</data>')
            lines.append('    </node>')

        # Add edges
        for edge in self.edges.values():
            lines.append(
                f'    <edge source="{edge.source_id}" target="{edge.target_id}">'
            )
            lines.append(f'      <data key="type">{edge.relationship_type.value}</data>')
            lines.append(f'      <data key="strength">{edge.strength}</data>')
            lines.append('    </edge>')

        lines.extend([
            '  </graph>',
            '</graphml>'
        ])

        return '\n'.join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        nodes = list(self.nodes.values())
        edges = list(self.edges.values())

        if not nodes:
            return {}

        return {
            'node_count': len(nodes),
            'edge_count': len(edges),
            'average_degree': len(edges) / len(nodes) if nodes else 0,
            'density': len(edges) / (len(nodes) * (len(nodes) - 1)) if len(nodes) > 1 else 0,
            'communities': len(self.community_detection()),
            'avg_node_confidence': sum(n.confidence for n in nodes) / len(nodes),
            'avg_edge_confidence': sum(e.confidence for e in edges) / len(edges) if edges else 0,
        }
