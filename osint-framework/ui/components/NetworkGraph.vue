<template>
  <div class="network-graph">
    <div class="graph-header">
      <h2>Network Graph</h2>
      <div class="graph-controls">
        <button @click="togglePhysics" :class="{ active: physicsEnabled }">
          {{ physicsEnabled ? 'Physics On' : 'Physics Off' }}
        </button>
        <button @click="exportGraph">Export as PNG</button>
        <button @click="resetView">Reset View</button>
        <label>
          Node Size:
          <select v-model.number="nodeSizeMultiplier">
            <option value="0.5">Small</option>
            <option value="1">Normal</option>
            <option value="1.5">Large</option>
          </select>
        </label>
      </div>
    </div>

    <div ref="graphContainer" class="graph-container"></div>

    <div v-if="selectedNode" class="node-details">
      <h3>{{ selectedNode.label }}</h3>
      <div class="details-content">
        <div class="detail-item">
          <span class="label">Entity Type:</span>
          <span class="value">{{ selectedNode.type }}</span>
        </div>
        <div class="detail-item">
          <span class="label">Centrality Score:</span>
          <span class="value">{{ (selectedNode.centrality * 100).toFixed(1) }}</span>
        </div>
        <div class="detail-item">
          <span class="label">Degree:</span>
          <span class="value">{{ selectedNode.degree }}</span>
        </div>
        <div v-if="selectedNode.community" class="detail-item">
          <span class="label">Community:</span>
          <span class="value">{{ selectedNode.community }}</span>
        </div>
        <div v-if="selectedNode.metadata" class="detail-item">
          <span class="label">Metadata:</span>
          <pre class="metadata">{{ JSON.stringify(selectedNode.metadata, null, 2) }}</pre>
        </div>
      </div>

      <div class="connected-nodes">
        <h4>Connected To:</h4>
        <div class="nodes-list">
          <div v-for="edge in getConnectedNodes()" :key="edge.id" class="connected-node">
            <span class="node-name">{{ edge.label }}</span>
            <span class="edge-label">{{ edge.relationship }}</span>
            <span class="edge-strength" :style="{ width: (edge.strength * 100) + '%' }"></span>
          </div>
        </div>
      </div>
    </div>

    <div class="graph-legend">
      <div class="legend-section">
        <h4>Node Types</h4>
        <div v-for="type in nodeTypes" :key="type" class="legend-item">
          <span class="legend-dot" :style="{ background: getNodeColor(type) }"></span>
          <span>{{ type }}</span>
        </div>
      </div>
      <div class="legend-section">
        <h4>Relationship Strength</h4>
        <div class="strength-bar">
          <span>Weak</span>
          <div class="bar">
            <div class="bar-fill" style="width: 25%"></div>
          </div>
          <span>Strong</span>
        </div>
      </div>
    </div>

    <div class="graph-stats">
      <div class="stat">
        <span class="label">Nodes:</span>
        <span class="value">{{ nodes.length }}</span>
      </div>
      <div class="stat">
        <span class="label">Edges:</span>
        <span class="value">{{ edges.length }}</span>
      </div>
      <div class="stat">
        <span class="label">Communities:</span>
        <span class="value">{{ communities.length }}</span>
      </div>
      <div class="stat">
        <span class="label">Avg. Degree:</span>
        <span class="value">{{ avgDegree.toFixed(1) }}</span>
      </div>
    </div>
  </div>
</template>

<script>
// Mock D3.js integration - would use actual D3 in production
export default {
  name: 'NetworkGraph',
  props: {
    nodes: {
      type: Array,
      required: true,
      default: () => []
    },
    edges: {
      type: Array,
      required: true,
      default: () => []
    }
  },
  data() {
    return {
      selectedNode: null,
      physicsEnabled: true,
      nodeSizeMultiplier: 1,
      nodeTypes: ['Person', 'Company', 'Domain', 'Account', 'Location'],
      communities: []
    };
  },
  computed: {
    avgDegree() {
      if (!this.nodes.length) return 0;
      const totalDegree = this.nodes.reduce((sum, node) => {
        return sum + this.edges.filter(e => e.source === node.id || e.target === node.id).length;
      }, 0);
      return totalDegree / this.nodes.length;
    }
  },
  mounted() {
    this.initializeGraph();
  },
  methods: {
    initializeGraph() {
      // Initialize D3 force-directed graph
      this.$nextTick(() => {
        const container = this.$refs.graphContainer;
        if (!container || this.nodes.length === 0) return;
        
        // Use canvas-based rendering for performance
        const canvas = document.createElement('canvas');
        canvas.width = container.clientWidth;
        canvas.height = container.clientHeight;
        container.appendChild(canvas);
        
        const ctx = canvas.getContext('2d');
        
        // Simple force-directed layout using physics simulation
        const nodeRadius = 10;
        const repulsion = 1000;
        const attraction = 0.1;
        const iterations = 100;
        
        // Initialize node positions if not already set
        if (this.nodes.length > 0 && !this.nodes[0].x) {
          this.nodes.forEach((node, i) => {
            node.x = Math.random() * canvas.width;
            node.y = Math.random() * canvas.height;
            node.vx = 0;
            node.vy = 0;
          });
        }
        
        // Run physics simulation
        for (let iter = 0; iter < iterations; iter++) {
          // Apply repulsion forces
          for (let i = 0; i < this.nodes.length; i++) {
            for (let j = i + 1; j < this.nodes.length; j++) {
              const dx = this.nodes[j].x - this.nodes[i].x;
              const dy = this.nodes[j].y - this.nodes[i].y;
              const dist = Math.sqrt(dx * dx + dy * dy) || 1;
              const force = repulsion / (dist * dist);
              
              this.nodes[i].vx -= (force * dx) / dist;
              this.nodes[i].vy -= (force * dy) / dist;
              this.nodes[j].vx += (force * dx) / dist;
              this.nodes[j].vy += (force * dy) / dist;
            }
          }
          
          // Apply attraction forces for edges
          for (const edge of this.edges) {
            const source = this.nodes.find(n => n.id === edge.source);
            const target = this.nodes.find(n => n.id === edge.target);
            if (!source || !target) continue;
            
            const dx = target.x - source.x;
            const dy = target.y - source.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = attraction * dist;
            
            source.vx += (force * dx) / dist;
            source.vy += (force * dy) / dist;
            target.vx -= (force * dx) / dist;
            target.vy -= (force * dy) / dist;
          }
          
          // Update positions
          this.nodes.forEach(node => {
            node.x += node.vx;
            node.y += node.vy;
            node.vx *= 0.95;
            node.vy *= 0.95;
          });
        }
        
        // Draw the graph
        this.renderGraph(ctx, canvas);
      });
      
      // Calculate communities
      this.calculateCommunities();
    },
    
    renderGraph(ctx, canvas) {
      // Clear canvas
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      const nodeRadius = 10 * this.nodeSizeMultiplier;
      
      // Draw edges
      ctx.strokeStyle = '#ccc';
      ctx.lineWidth = 1;
      for (const edge of this.edges) {
        const source = this.nodes.find(n => n.id === edge.source);
        const target = this.nodes.find(n => n.id === edge.target);
        if (!source || !target) continue;
        
        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);
        ctx.stroke();
      }
      
      // Draw nodes
      for (const node of this.nodes) {
        const color = this.getNodeColor(node.type);
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI);
        ctx.fill();
        
        // Draw label
        ctx.fillStyle = '#000';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const label = node.label.length > 10 ? node.label.substring(0, 10) + '.' : node.label;
        ctx.fillText(label, node.x, node.y + nodeRadius + 15);
      }
      
      // Add click handler
      const canvas_ref = document.querySelector('.graph-container canvas');
      if (canvas_ref && !canvas_ref.clickHandlerAttached) {
        canvas_ref.addEventListener('click', (e) => {
          const rect = canvas_ref.getBoundingClientRect();
          const x = e.clientX - rect.left;
          const y = e.clientY - rect.top;
          
          for (const node of this.nodes) {
            const dist = Math.sqrt((node.x - x) ** 2 + (node.y - y) ** 2);
            if (dist < nodeRadius * 1.5) {
              this.selectNode(node);
              break;
            }
          }
        });
        canvas_ref.clickHandlerAttached = true;
      }
    },
    calculateCommunities() {
      // Simplified community detection (Louvain-like algorithm would be used in production)
      const communities = new Map();
      let communityId = 0;

      for (const node of this.nodes) {
        if (!communities.has(node.id)) {
          communities.set(node.id, communityId);
          this.expandCommunity(node.id, communityId, communities);
          communityId++;
        }
      }

      this.communities = Array.from(new Set(communities.values()));
    },
    expandCommunity(nodeId, communityId, communities) {
      // Simple breadth-first expansion for community detection
      const visited = new Set([nodeId]);
      const queue = [nodeId];

      while (queue.length > 0 && visited.size < 10) {
        const current = queue.shift();
        
        for (const edge of this.edges) {
          let neighbor = null;
          if (edge.source === current) neighbor = edge.target;
          else if (edge.target === current) neighbor = edge.source;

          if (neighbor && !visited.has(neighbor)) {
            visited.add(neighbor);
            communities.set(neighbor, communityId);
            queue.push(neighbor);
          }
        }
      }
    },
    togglePhysics() {
      this.physicsEnabled = !this.physicsEnabled;
      this.$emit('physics-toggled', this.physicsEnabled);
    },
    exportGraph() {
      // Export graph as PNG
      this.$emit('export-requested');
    },
    resetView() {
      this.selectedNode = null;
      this.$emit('view-reset');
    },
    selectNode(node) {
      this.selectedNode = node;
      this.$emit('node-selected', node);
    },
    getConnectedNodes() {
      if (!this.selectedNode) return [];
      
      return this.edges
        .filter(e => e.source === this.selectedNode.id || e.target === this.selectedNode.id)
        .map(e => {
          const targetId = e.source === this.selectedNode.id ? e.target : e.source;
          const targetNode = this.nodes.find(n => n.id === targetId);
          
          return {
            id: targetId,
            label: targetNode?.label || targetId,
            relationship: e.relationship || 'connected',
            strength: e.strength || 0.5
          };
        });
    },
    getNodeColor(type) {
      const colors = {
        Person: '#4285F4',
        Company: '#34A853',
        Domain: '#FBBC04',
        Account: '#EA4335',
        Location: '#9C27B0'
      };
      return colors[type] || '#999';
    }
  }
};
</script>

<style scoped>
.network-graph {
  padding: 20px;
  background: #f5f5f5;
  border-radius: 8px;
}

.graph-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.graph-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

.graph-controls button,
.graph-controls select {
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  cursor: pointer;
  background: white;
  font-size: 14px;
}

.graph-controls button:hover,
.graph-controls button.active {
  background: #007bff;
  color: white;
  border-color: #007bff;
}

.graph-container {
  width: 100%;
  height: 500px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
}

.graph-placeholder {
  color: #999;
  text-align: center;
  padding: 20px;
}

.node-details {
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 15px;
  margin-bottom: 20px;
}

.node-details h3 {
  margin-top: 0;
  margin-bottom: 15px;
}

.details-content {
  margin-bottom: 20px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.detail-item:last-child {
  border-bottom: none;
}

.detail-item .label {
  font-weight: bold;
  color: #333;
}

.detail-item .value {
  color: #666;
}

.metadata {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 4px;
  font-size: 11px;
  overflow-x: auto;
  max-height: 150px;
  overflow-y: auto;
}

.connected-nodes h4 {
  margin-top: 20px;
  margin-bottom: 10px;
}

.nodes-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.connected-node {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  background: #f5f5f5;
  border-radius: 4px;
}

.node-name {
  font-weight: bold;
  flex: 0 0 150px;
}

.edge-label {
  font-size: 12px;
  color: #999;
  flex: 0 0 100px;
}

.edge-strength {
  height: 4px;
  background: linear-gradient(to right, #ff6b6b, #ffd93d, #6bcf7f);
  border-radius: 2px;
  flex: 1;
}

.graph-legend {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 15px;
  margin-bottom: 20px;
}

.legend-section h4 {
  margin-top: 0;
  margin-bottom: 10px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.strength-bar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.strength-bar .bar {
  flex: 1;
  height: 20px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(to right, #ff6b6b, #ffd93d, #6bcf7f);
}

.graph-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 15px;
}

.stat {
  text-align: center;
}

.stat .label {
  display: block;
  font-size: 12px;
  color: #999;
  margin-bottom: 5px;
}

.stat .value {
  display: block;
  font-size: 20px;
  font-weight: bold;
  color: #007bff;
}
</style>
