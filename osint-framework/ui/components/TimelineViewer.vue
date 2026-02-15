<template>
  <div class="timeline-viewer">
    <div class="timeline-header">
      <h2>Timeline View</h2>
      <div class="timeline-controls">
        <div class="filter-section">
          <label>Filter by Event Type:</label>
          <select v-model="selectedEventType" @change="filterEvents">
            <option value="">All Events</option>
            <option value="employment">Employment</option>
            <option value="education">Education</option>
            <option value="social">Social Media</option>
            <option value="location">Location</option>
            <option value="breach">Data Breach</option>
            <option value="financial">Financial</option>
          </select>
        </div>
        <div class="zoom-controls">
          <button @click="zoomIn">+</button>
          <button @click="zoomOut">-</button>
          <span>{{ zoomLevel }}x</span>
        </div>
      </div>
    </div>

    <div class="timeline-container" :style="{ height: containerHeight }">
      <div class="timeline-axis">
        <div v-for="year in getYearMarkers()" :key="year" class="year-marker">
          {{ year }}
        </div>
      </div>

      <div class="timeline-events" :style="{ transform: `scale(1, ${zoomLevel})` }">
        <div
          v-for="event in filteredEvents"
          :key="event.event_id"
          :class="['timeline-event', event.event_type, { milestone: event.is_milestone }]"
          :style="{ left: getEventPosition(event) + '%' }"
          @click="selectEvent(event)"
          @mouseover="hoveredEvent = event"
          @mouseleave="hoveredEvent = null"
        >
          <div class="event-dot"></div>
          <div v-if="hoveredEvent && hoveredEvent.event_id === event.event_id" class="event-tooltip">
            <div class="tooltip-title">{{ event.event_type }}</div>
            <div class="tooltip-date">{{ formatDate(event.date) }}</div>
            <div class="tooltip-description">{{ event.description }}</div>
            <div class="tooltip-confidence">
              Confidence: {{ (event.confidence * 100).toFixed(0) }}%
            </div>
            <div v-if="event.source" class="tooltip-source">Source: {{ event.source }}</div>
          </div>
        </div>
      </div>

      <div v-if="selectedEvent" class="event-details">
        <h3>{{ selectedEvent.event_type }}</h3>
        <div class="details-content">
          <div class="detail-item">
            <span class="label">Date:</span>
            <span class="value">{{ formatDate(selectedEvent.date) }}</span>
          </div>
          <div class="detail-item">
            <span class="label">Description:</span>
            <span class="value">{{ selectedEvent.description }}</span>
          </div>
          <div class="detail-item">
            <span class="label">Location:</span>
            <span class="value">{{ selectedEvent.location || 'N/A' }}</span>
          </div>
          <div class="detail-item">
            <span class="label">Confidence:</span>
            <span class="value">{{ (selectedEvent.confidence * 100).toFixed(1) }}%</span>
          </div>
          <div v-if="selectedEvent.entities" class="detail-item">
            <span class="label">Related Entities:</span>
            <div class="entities-list">
              <span v-for="entity in selectedEvent.entities" :key="entity" class="entity-tag">
                {{ entity }}
              </span>
            </div>
          </div>
          <div v-if="selectedEvent.source" class="detail-item">
            <span class="label">Source:</span>
            <span class="value">{{ selectedEvent.source }}</span>
          </div>
          <div v-if="selectedEvent.metadata" class="detail-item">
            <span class="label">Additional Data:</span>
            <pre class="metadata">{{ JSON.stringify(selectedEvent.metadata, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>

    <div class="timeline-legend">
      <div class="legend-item employment">
        <span class="legend-dot"></span>
        <span>Employment</span>
      </div>
      <div class="legend-item education">
        <span class="legend-dot"></span>
        <span>Education</span>
      </div>
      <div class="legend-item social">
        <span class="legend-dot"></span>
        <span>Social Media</span>
      </div>
      <div class="legend-item location">
        <span class="legend-dot"></span>
        <span>Location</span>
      </div>
      <div class="legend-item breach">
        <span class="legend-dot"></span>
        <span>Data Breach</span>
      </div>
      <div class="legend-item financial">
        <span class="legend-dot"></span>
        <span>Financial</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TimelineViewer',
  props: {
    events: {
      type: Array,
      required: true,
      default: () => []
    }
  },
  data() {
    return {
      selectedEventType: '',
      zoomLevel: 1,
      containerHeight: '400px',
      selectedEvent: null,
      hoveredEvent: null
    };
  },
  computed: {
    filteredEvents() {
      if (!this.selectedEventType) {
        return this.events;
      }
      return this.events.filter(e => e.event_type === this.selectedEventType);
    }
  },
  methods: {
    filterEvents() {
      this.$emit('filter-changed', this.selectedEventType);
    },
    zoomIn() {
      if (this.zoomLevel < 3) {
        this.zoomLevel += 0.5;
        this.containerHeight = (400 * this.zoomLevel) + 'px';
      }
    },
    zoomOut() {
      if (this.zoomLevel > 0.5) {
        this.zoomLevel -= 0.5;
        this.containerHeight = (400 * this.zoomLevel) + 'px';
      }
    },
    getYearMarkers() {
      if (!this.events.length) return [];
      
      const dates = this.events.map(e => new Date(e.date));
      const minYear = Math.min(...dates.map(d => d.getFullYear()));
      const maxYear = Math.max(...dates.map(d => d.getFullYear()));
      
      const years = [];
      for (let year = minYear; year <= maxYear; year++) {
        years.push(year);
      }
      return years;
    },
    getEventPosition(event) {
      const dates = this.events.map(e => new Date(e.date));
      const minDate = new Date(Math.min(...dates));
      const maxDate = new Date(Math.max(...dates));
      const eventDate = new Date(event.date);
      
      const totalTime = maxDate - minDate;
      const eventTime = eventDate - minDate;
      
      return (eventTime / totalTime) * 100;
    },
    selectEvent(event) {
      this.selectedEvent = event;
      this.$emit('event-selected', event);
    },
    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    }
  }
};
</script>

<style scoped>
.timeline-viewer {
  padding: 20px;
  background: #f5f5f5;
  border-radius: 8px;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.timeline-controls {
  display: flex;
  gap: 20px;
  align-items: center;
}

.filter-section,
.zoom-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

select {
  padding: 8px 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 14px;
}

button {
  padding: 8px 12px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
}

button:hover {
  background: #0056b3;
}

.timeline-container {
  position: relative;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-bottom: 20px;
  overflow-y: auto;
}

.timeline-axis {
  display: flex;
  justify-content: space-around;
  padding: 10px;
  border-bottom: 1px solid #ddd;
  font-weight: bold;
}

.year-marker {
  flex: 1;
  text-align: center;
}

.timeline-events {
  position: relative;
  height: 100px;
  padding: 20px;
  transition: transform 0.3s ease;
}

.timeline-event {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  transition: all 0.3s ease;
}

.timeline-event:hover .event-dot {
  transform: scale(1.5);
}

.event-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #007bff;
  border: 2px solid white;
  box-shadow: 0 0 5px rgba(0, 0, 0, 0.2);
  transition: transform 0.3s ease;
}

.timeline-event.employment .event-dot {
  background: #28a745;
}

.timeline-event.education .event-dot {
  background: #ffc107;
}

.timeline-event.social .event-dot {
  background: #17a2b8;
}

.timeline-event.location .event-dot {
  background: #e83e8c;
}

.timeline-event.breach .event-dot {
  background: #dc3545;
}

.timeline-event.financial .event-dot {
  background: #6f42c1;
}

.timeline-event.milestone .event-dot {
  width: 16px;
  height: 16px;
  border-width: 3px;
}

.event-tooltip {
  position: absolute;
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 10px;
  min-width: 200px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
  z-index: 10;
  top: -120px;
  left: -100px;
}

.tooltip-title {
  font-weight: bold;
  margin-bottom: 5px;
}

.tooltip-date {
  font-size: 12px;
  color: #666;
  margin-bottom: 5px;
}

.tooltip-description {
  font-size: 13px;
  margin-bottom: 5px;
}

.tooltip-confidence {
  font-size: 11px;
  color: #999;
}

.tooltip-source {
  font-size: 11px;
  color: #999;
  margin-top: 5px;
}

.event-details {
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 15px;
  margin-bottom: 20px;
}

.event-details h3 {
  margin-top: 0;
  margin-bottom: 15px;
}

.details-content {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.detail-item {
  display: flex;
  flex-direction: column;
}

.detail-item .label {
  font-weight: bold;
  margin-bottom: 5px;
  color: #333;
}

.detail-item .value {
  color: #666;
}

.entities-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.entity-tag {
  background: #e9ecef;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
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

.timeline-legend {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 15px;
  padding: 15px;
  background: white;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.legend-item.employment .legend-dot {
  background: #28a745;
}

.legend-item.education .legend-dot {
  background: #ffc107;
}

.legend-item.social .legend-dot {
  background: #17a2b8;
}

.legend-item.location .legend-dot {
  background: #e83e8c;
}

.legend-item.breach .legend-dot {
  background: #dc3545;
}

.legend-item.financial .legend-dot {
  background: #6f42c1;
}
</style>
